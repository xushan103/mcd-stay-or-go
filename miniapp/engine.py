"""点选餐品后，单点和能盖住点名的套餐一起比，再裁决去留。"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from baskets import BasketOffer, MenuItem, choose_basket, explain_choice, plan_baskets
from decide import ChannelQuote, decide, estimate_drive_minutes

from menu_catalog import (
    CAPTURED_AT,
    CARTS,
    COMBOS,
    COUPON_CARTS,
    COUPON_LINES,
    GROUPS,
    PLACE,
    SOURCE,
    STORES,
    products,
)


def menu_groups() -> list[dict]:
    grouped = {key: [] for key, _label in GROUPS}
    for product in products():
        pickup = product["channels"].get("pickup")
        shown = pickup or next(iter(product["channels"].values()))
        grouped[product["group"]].append(
            {
                "name": product["name"],
                "price_yuan": round(shown["price_fen"] / 100, 2),
                "price_note": "" if pickup else "外送",
            }
        )
    return [{"id": key, "label": label, "items": grouped[key]} for key, label in GROUPS]


def _unmatched_reason(selected: list[dict], driving: bool) -> str:
    """三条路都进不了裁决时，说明每一条缺了什么。"""
    bits = ["同一条路要同时有你点的全部单品，现在凑不齐。"]
    for channel_id, store in STORES.items():
        missing = [item["name"] for item in selected if channel_id not in item["channels"]]
        if missing:
            bits.append(f"{store['label']}没有{'、'.join(missing)}")
        elif store.get("needs_car") and not driving:
            bits.append(f"{store['label']}有，但你没开车，勾上「我开着车」才会拿来比")
    return "。".join(bits) + "。"


def _minutes_for(channel_id: str, store: dict, minutes_to_spot: float) -> float:
    if channel_id == "delivery":
        return 0.0
    if channel_id == "drivethru":
        return estimate_drive_minutes(store["distance_m"])
    return round(minutes_to_spot + store["distance_m"] / 80.0 + 5.0, 1)


def _selection(names: list[str]) -> list[dict]:
    wanted = []
    seen = set()
    catalog = {item["name"]: item for item in products()}
    missing = []
    for name in names:
        cleaned = name.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        if cleaned not in catalog:
            missing.append(cleaned)
            continue
        wanted.append(catalog[cleaned])
    if missing:
        raise ValueError("菜单里没有「" + "、".join(missing) + "」。从汉堡、小食、饮料里点。")
    if not wanted:
        raise ValueError("先点选汉堡、小食或饮料。")
    return wanted


def _channel_basket(channel_id: str, selected: list[dict], use_coupon: bool) -> tuple[list[BasketOffer], set[str]]:
    items: list[MenuItem] = []
    lines: dict[str, int] = {}
    requested: list[str] = []
    for product in selected:
        offer = product["channels"].get(channel_id)
        if offer is None:
            return [], set()
        items.append(MenuItem(offer["code"], product["name"], "single"))
        price = offer["price_fen"]
        if use_coupon and product["name"] == "麦辣鸡腿汉堡":
            price = COUPON_LINES[channel_id][offer["code"]]
        lines[offer["code"]] = price
        requested.append(product["name"])

    combo_prices: dict[str, int] = {}
    for combo in COMBOS:
        slot = combo["channels"].get(channel_id)
        if slot is None:
            continue
        items.append(MenuItem(slot["code"], combo["name"], "combo", tuple(combo["components"])))
        combo_prices[slot["code"]] = slot["price_fen"]

    plan = plan_baskets(requested, items)
    offers: list[BasketOffer] = []
    summed: set[str] = set()
    carts = dict(CARTS[channel_id])
    if use_coupon:
        carts.update(COUPON_CARTS[channel_id])
    for offer in plan.to_price:
        if offer.kind == "combo":
            price = combo_prices.get(offer.codes[0])
            official = True
        else:
            codes = frozenset(offer.codes)
            if codes in carts:
                price = carts[codes]
                official = True
            elif all(code in lines for code in offer.codes):
                price = sum(lines[code] for code in offer.codes)
                if channel_id == "delivery":
                    price += STORES["delivery"]["delivery_fen"] + STORES["delivery"]["packing_fen"]
                official = False
            else:
                price = None
                official = False
        if price is None:
            continue
        offers.append(
            BasketOffer(
                offer.basket_id,
                offer.kind,
                offer.name,
                offer.components,
                offer.extras,
                offer.codes,
                price,
            )
        )
        if not official:
            summed.add(offer.basket_id)
    return offers, summed


def run_verdict(
    scenario_id: str = "banshao",
    *,
    names: Optional[list[str]] = None,
    food: Optional[str] = None,
    use_coupon: bool = False,
    minutes_to_spot: float = 0,
    wage: Optional[float] = None,
    driving: bool = False,
    max_minutes: Optional[float] = None,
) -> dict:
    if minutes_to_spot < 0:
        raise ValueError("到站分钟不能为负")
    if wage is not None and wage < 0:
        raise ValueError("时薪不能为负")
    if max_minutes is not None and max_minutes < 0:
        raise ValueError("出门上限不能为负")

    if names is None:
        if food:
            names = [part.strip() for part in food.replace("＋", "+").split("+")]
        elif scenario_id == "mala":
            names = ["麦辣鸡腿汉堡", "薯条"]
            use_coupon = True
        elif scenario_id == "juba":
            names = ["巨无霸", "薯条"]
        else:
            names = ["板烧鸡腿堡", "薯条"]

    selected = _selection(names)
    title = " + ".join(item["name"] for item in selected)
    rows: list[dict] = []
    quotes: list[ChannelQuote] = []

    for channel_id, store in STORES.items():
        offers, summed = _channel_basket(channel_id, selected, use_coupon)
        minutes = _minutes_for(channel_id, store, minutes_to_spot)
        if not offers:
            rows.append(
                {
                    "channel": channel_id,
                    "label": store["label"],
                    "store_name": store["store_name"],
                    "store_code": store["store_code"],
                    "product_name": "未核价",
                    "price_fen": 0,
                    "price_yuan": None,
                    "minutes": minutes,
                    "note": "这条路的菜单没有你点的全部单品。",
                    "in_decision": False,
                    "recommended": False,
                }
            )
            continue
        choice = choose_basket(offers)
        chosen = choice.chosen
        needs_car = bool(store.get("needs_car"))
        in_decision = not needs_car or driving
        note = explain_choice(choice)
        if use_coupon and any(item["name"] == "麦辣鸡腿汉堡" for item in selected):
            note += " 麦辣按 11.9 元券的核价。"
        if channel_id == "delivery":
            note += " 含配送 ¥6.00 + 打包 ¥1.90。"
        if chosen.basket_id in summed:
            note += " 这组没有单独的整单核价，单品用的是菜单标价。"
        if needs_car and not driving:
            note += " 你没开车，这条只作对照，不进入裁决。"
        row = {
            "channel": channel_id,
            "label": store["label"],
            "store_name": store["store_name"],
            "store_code": store["store_code"],
            "product_name": chosen.name,
            "price_fen": chosen.price_fen,
            "price_yuan": round((chosen.price_fen or 0) / 100, 2),
            "minutes": minutes,
            "note": note,
            "in_decision": in_decision,
            "recommended": False,
        }
        rows.append(row)
        if in_decision:
            quotes.append(
                ChannelQuote(
                    channel_id,
                    store["label"],
                    chosen.price_fen or 0,
                    minutes,
                    store["store_name"],
                    store["store_code"],
                    note,
                    chosen.name,
                    store.get("delivery_fen", 0),
                    store.get("packing_fen", 0),
                )
            )

    if not quotes:
        raise ValueError(_unmatched_reason(selected, driving))

    verdict = decide(quotes, wage_yuan_per_hour=wage, max_active_minutes=max_minutes)
    for row in rows:
        row["recommended"] = row["in_decision"] and row["channel"] == verdict.recommended

    return {
        "scenario": {
            "id": "picked",
            "title": title,
            "place": PLACE,
            "source": SOURCE,
            "captured_at": CAPTURED_AT,
        },
        "headline": verdict.recommended_label,
        "reason": verdict.reason,
        "critical_wage_yuan_per_hour": verdict.critical_wage_yuan_per_hour,
        "saving_yuan": verdict.saving_yuan,
        "extra_minutes": verdict.extra_minutes,
        "rows": rows,
        "verdict": asdict(verdict),
    }
