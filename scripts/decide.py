#!/usr/bin/env python3
"""麦麦去留 · 履约通道裁决引擎。

只做算术：临界时薪、综合成本、ETA 裁决。
价格必须来自官方 calculate-price（单位：分），本模块不重算优惠。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Iterable, Optional


FEN_PER_YUAN = 100


@dataclass(frozen=True)
class ChannelQuote:
    """一条履约通道的官方核价结果。"""

    channel: str  # pickup | drivethru | delivery
    label: str
    price_fen: int
    active_minutes: float  # 用户自己要花的主动时间（走路/开车/等电梯等）
    store_name: str = ""
    store_code: str = ""
    notes: str = ""
    product_name: str = ""
    delivery_fen: int = 0
    packing_fen: int = 0

    @property
    def price_yuan(self) -> float:
        return self.price_fen / FEN_PER_YUAN


@dataclass(frozen=True)
class Verdict:
    recommended: str
    recommended_label: str
    reason: str
    critical_wage_yuan_per_hour: Optional[float]
    compare_a: str
    compare_b: str
    saving_yuan: float
    extra_minutes: float
    ranked: list[dict]


def fen_to_yuan(fen: int) -> float:
    return round(fen / FEN_PER_YUAN, 2)


def critical_wage(
    cheaper_price_fen: int,
    cheaper_minutes: float,
    faster_price_fen: int,
    faster_minutes: float,
) -> Optional[float]:
    """省下的钱 ÷ 多花的时间 → 临界时薪（元/小时）。

    若更快通道并不更贵，或更便宜通道并不更慢，则返回 None。
    """
    save_fen = faster_price_fen - cheaper_price_fen
    extra_min = cheaper_minutes - faster_minutes
    if save_fen <= 0 or extra_min <= 0:
        return None
    return round((save_fen / FEN_PER_YUAN) * 60.0 / extra_min, 1)


def total_cost_yuan(price_fen: int, minutes: float, wage_yuan_per_hour: float) -> float:
    return round(price_fen / FEN_PER_YUAN + minutes / 60.0 * wage_yuan_per_hour, 2)


def rank_by_wage(quotes: Iterable[ChannelQuote], wage: float) -> list[ChannelQuote]:
    return sorted(quotes, key=lambda q: (total_cost_yuan(q.price_fen, q.active_minutes, wage), q.price_fen))


def decide(
    quotes: list[ChannelQuote],
    *,
    wage_yuan_per_hour: Optional[float] = None,
    max_active_minutes: Optional[float] = None,
) -> Verdict:
    if not quotes:
        raise ValueError("quotes 不能为空")

    eligible = list(quotes)
    if max_active_minutes is not None:
        filtered = [q for q in eligible if q.active_minutes <= max_active_minutes]
        if filtered:
            eligible = filtered

    # 默认：先比到手价，相同时比主动时间
    by_price = sorted(eligible, key=lambda q: (q.price_fen, q.active_minutes))
    cheapest = by_price[0]
    fastest = sorted(eligible, key=lambda q: (q.active_minutes, q.price_fen))[0]

    cw = critical_wage(
        cheapest.price_fen,
        cheapest.active_minutes,
        fastest.price_fen,
        fastest.active_minutes,
    )

    if wage_yuan_per_hour is not None and wage_yuan_per_hour > 0:
        ranked = rank_by_wage(eligible, wage_yuan_per_hour)
        best = ranked[0]
        reason = (
            f"按你给出的时薪约 ¥{wage_yuan_per_hour:g}/小时，"
            f"「{best.label}」综合成本最低（到手价 + 时间成本）。"
        )
        if cw is not None and cheapest.channel != fastest.channel:
            reason += (
                f" 临界时薪约 ¥{cw}/小时："
                f"时薪低于它更值得选「{cheapest.label}」，"
                f"高于它更值得选「{fastest.label}」。"
            )
    elif cw is not None and cheapest.channel != fastest.channel:
        ranked = by_price
        best = cheapest
        reason = (
            f"「{cheapest.label}」比「{fastest.label}」"
            f"省 ¥{fen_to_yuan(fastest.price_fen - cheapest.price_fen)}，"
            f"但要多花 {cheapest.active_minutes - fastest.active_minutes:.0f} 分钟；"
            f"临界时薪约 ¥{cw}/小时。"
        )
    else:
        ranked = by_price
        best = cheapest
        reason = f"「{best.label}」到手价最低，且主动时间不吃亏。"

    if max_active_minutes is not None:
        reason += f" 已应用「最多愿意花 {max_active_minutes:g} 分钟」约束。"

    saving = fen_to_yuan(fastest.price_fen - cheapest.price_fen)
    extra = max(0.0, cheapest.active_minutes - fastest.active_minutes)

    return Verdict(
        recommended=best.channel,
        recommended_label=best.label,
        reason=reason,
        critical_wage_yuan_per_hour=cw,
        compare_a=cheapest.channel,
        compare_b=fastest.channel,
        saving_yuan=saving,
        extra_minutes=extra,
        ranked=[
            {
                **asdict(q),
                "price_yuan": fen_to_yuan(q.price_fen),
                "total_cost_yuan": (
                    total_cost_yuan(q.price_fen, q.active_minutes, wage_yuan_per_hour)
                    if wage_yuan_per_hour
                    else None
                ),
            }
            for q in ranked
        ],
    )


def estimate_walk_minutes(distance_meters: float, wait_minutes: float = 5.0) -> float:
    """步行 ETA：按 80 m/min（约 4.8 km/h）+ 店内等待默认 5 分钟。"""
    if distance_meters < 0:
        raise ValueError("distance_meters 不能为负")
    return round(distance_meters / 80.0 + wait_minutes, 1)


def estimate_drive_minutes(distance_meters: float, wait_minutes: float = 4.0) -> float:
    """驾车 ETA：城市路况粗估 500 m/min（约 30 km/h）+ 车道等待默认 4 分钟。"""
    if distance_meters < 0:
        raise ValueError("distance_meters 不能为负")
    return round(distance_meters / 500.0 + wait_minutes, 1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="麦麦去留 · 本地裁决（输入官方核价分）")
    p.add_argument("--wage", type=float, default=None, help="自评时薪（元/小时）")
    p.add_argument("--max-minutes", type=float, default=None, help="最多愿意花的主动分钟")
    p.add_argument(
        "--fixture",
        default="fixtures/sample_quote.json",
        help="包含三路报价的 JSON fixture",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    with open(args.fixture, encoding="utf-8") as f:
        raw = json.load(f)
    quotes = [ChannelQuote(**item) for item in raw["quotes"]]
    verdict = decide(quotes, wage_yuan_per_hour=args.wage, max_active_minutes=args.max_minutes)
    print(json.dumps(asdict(verdict), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
