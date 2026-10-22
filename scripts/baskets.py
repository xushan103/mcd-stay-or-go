#!/usr/bin/env python3
"""点名商品的候选篮子。

用户点的是要吃到的东西，不是「只能按单点 SKU 下单」。
套餐只要盖住全部点名，就从一开始进入候选；多出来的可乐、小食留在篮子里。
未看过子项的同名套餐标成待查，不能在核价前丢掉。
本模块不把菜单标价相加当到手价，到手价只接受官方 calculate-price 的结果。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def component_satisfies(component: str, requested: str) -> bool:
    """组件是否盖住一个点名。薯条可以落在中薯条上，板烧不能落在麦辣上。"""
    comp = _norm(component)
    req = _norm(requested)
    if len(req) < 2 or not comp:
        return False
    return req in comp or comp in req


def covers(components: Sequence[str], requested: Sequence[str]) -> bool:
    if not requested:
        raise ValueError("requested 不能为空")
    return all(any(component_satisfies(comp, req) for comp in components) for req in requested)


def extra_components(components: Sequence[str], requested: Sequence[str]) -> tuple[str, ...]:
    return tuple(comp for comp in components if not any(component_satisfies(comp, req) for req in requested))


@dataclass(frozen=True)
class MenuItem:
    """菜单上的一个单品或套餐。components 为空表示套餐子项还没拆开。"""

    code: str
    name: str
    kind: str  # single | combo
    components: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in {"single", "combo"}:
            raise ValueError(f"未知 kind: {self.kind}")


@dataclass(frozen=True)
class BasketOffer:
    basket_id: str
    kind: str
    name: str
    components: tuple[str, ...]
    extras: tuple[str, ...]
    codes: tuple[str, ...]
    price_fen: Optional[int] = None


@dataclass(frozen=True)
class BasketPlan:
    """to_price 已经知道子项，可以 calculate-price。

    pending_inspection 是名称能对上点名、但还没拆子项的套餐，必须先查详情。
    """

    to_price: tuple[BasketOffer, ...]
    pending_inspection: tuple[str, ...]
    rejected: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.pending_inspection


def _single_rank(item: MenuItem) -> tuple[int, int, str]:
    # 薯条默认中份；其余取名称更短的单品。
    medium = 0 if "中" in item.name else 1
    return (medium, len(item.name), item.code)


def _match_single(requested: str, singles: Sequence[MenuItem]) -> Optional[MenuItem]:
    hits = [item for item in singles if component_satisfies(item.name, requested)]
    if not hits:
        return None
    return sorted(hits, key=_single_rank)[0]


def _alacarte(requested: Sequence[str], singles: Sequence[MenuItem]) -> Optional[BasketOffer]:
    chosen: list[MenuItem] = []
    for req in requested:
        hit = _match_single(req, singles)
        if hit is None:
            return None
        chosen.append(hit)
    names = tuple(item.name for item in chosen)
    return BasketOffer(
        basket_id="alacarte",
        kind="alacarte",
        name="+".join(names),
        components=names,
        extras=(),
        codes=tuple(item.code for item in chosen),
    )


def _combo_offer(item: MenuItem, requested: Sequence[str]) -> BasketOffer:
    components = item.components or (item.name,)
    return BasketOffer(
        basket_id=f"combo:{item.code}",
        kind="combo",
        name=item.name,
        components=components,
        extras=extra_components(components, requested),
        codes=(item.code,),
    )


def plan_baskets(requested: Sequence[str], items: Sequence[MenuItem]) -> BasketPlan:
    """列出一开始就要考虑的篮子。盖住点名的套餐和单点并列，不看价格。"""
    if not requested:
        raise ValueError("requested 不能为空")

    singles = [item for item in items if item.kind == "single"]
    combos = [item for item in items if item.kind == "combo"]

    to_price: list[BasketOffer] = []
    pending: list[str] = []
    rejected: list[str] = []

    alacarte = _alacarte(requested, singles)
    if alacarte is not None:
        to_price.append(alacarte)

    for combo in combos:
        name_hits = any(component_satisfies(combo.name, req) for req in requested)
        if not combo.components:
            if name_hits:
                pending.append(combo.name)
            else:
                rejected.append(combo.name)
            continue
        if covers(combo.components, requested):
            to_price.append(_combo_offer(combo, requested))
        else:
            rejected.append(combo.name)

    return BasketPlan(
        to_price=tuple(to_price),
        pending_inspection=tuple(pending),
        rejected=tuple(rejected),
    )


@dataclass(frozen=True)
class BasketChoice:
    chosen: BasketOffer
    alternatives: tuple[BasketOffer, ...]


def choose_basket(offers: Sequence[BasketOffer]) -> BasketChoice:
    """同一通道里，用官方到手价更低的篮子。同价留下子项更多的套餐。"""
    priced = [offer for offer in offers if offer.price_fen is not None]
    if not priced:
        raise ValueError("没有已核价的篮子")
    ranked = sorted(priced, key=lambda offer: (offer.price_fen, 0 if offer.kind == "combo" else 1, -len(offer.components), offer.name))
    chosen = ranked[0]
    return BasketChoice(chosen=chosen, alternatives=tuple(item for item in ranked if item is not chosen))


def explain_choice(choice: BasketChoice) -> str:
    chosen = choice.chosen
    price = _yuan(chosen.price_fen or 0)
    extra = f"，多了{'、'.join(chosen.extras)}" if chosen.extras else ""
    text = f"采用「{chosen.name}」¥{price}{extra}"
    notes: list[str] = []
    for alt in choice.alternatives:
        if alt.price_fen is None or chosen.price_fen is None:
            continue
        alt_price = _yuan(alt.price_fen)
        delta = alt.price_fen - chosen.price_fen
        if delta > 0:
            notes.append(f"「{alt.name}」¥{alt_price}，贵 ¥{_yuan(delta)}")
        elif delta == 0:
            notes.append(f"「{alt.name}」同价 ¥{alt_price}，子项更少")
        else:
            notes.append(f"「{alt.name}」¥{alt_price}")
    if notes:
        text += "。" + "；".join(notes)
    return text + "。"


def _yuan(fen: int) -> str:
    return f"{fen / 100:.2f}"
