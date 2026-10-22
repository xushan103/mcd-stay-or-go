"""把候选篮子和三路裁决接成小程序一次请求能跑完的结果。"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from baskets import BasketOffer, choose_basket, explain_choice, plan_baskets
from decide import ChannelQuote, decide, estimate_drive_minutes

from scenarios import SCENARIOS


def list_scenarios() -> list[dict]:
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "place": item["place"],
            "blurb": item["blurb"],
            "default_minutes_to_spot": item["default_minutes_to_spot"],
            "source": item["source"],
        }
        for item in SCENARIOS.values()
    ]


def _minutes_for(channel: dict, minutes_to_spot: float) -> float:
    if channel["channel"] == "delivery":
        return 0.0
    if channel["channel"] == "drivethru":
        return estimate_drive_minutes(channel["distance_m"])
    walk = channel["distance_m"] / 80.0
    return round(minutes_to_spot + walk + 5.0, 1)


def _priced_offers(channel: dict, requested: list[str]) -> list[BasketOffer]:
    plan = plan_baskets(requested, channel["items"])
    if not plan.ready:
        pending = "、".join(plan.pending_inspection)
        raise RuntimeError(f"{channel['label']}还有套餐没拆开：{pending}")
    offers: list[BasketOffer] = []
    for offer in plan.to_price:
        price = channel["prices"].get(offer.basket_id)
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
    if not offers:
        raise RuntimeError(f"{channel['label']}没有可核价的篮子")
    return offers


def run_verdict(
    scenario_id: str,
    *,
    minutes_to_spot: float = 0,
    wage: Optional[float] = None,
    driving: bool = False,
    max_minutes: Optional[float] = None,
) -> dict:
    if scenario_id not in SCENARIOS:
        raise KeyError(scenario_id)
    if minutes_to_spot < 0:
        raise ValueError("到站分钟不能为负")
    if wage is not None and wage < 0:
        raise ValueError("时薪不能为负")
    if max_minutes is not None and max_minutes < 0:
        raise ValueError("出门上限不能为负")

    scenario = SCENARIOS[scenario_id]
    rows: list[dict] = []
    quotes: list[ChannelQuote] = []

    for channel in scenario["channels"]:
        offers = _priced_offers(channel, scenario["requested"])
        choice = choose_basket(offers)
        chosen = choice.chosen
        minutes = _minutes_for(channel, minutes_to_spot)
        needs_car = bool(channel.get("needs_car"))
        in_decision = not needs_car or driving
        note = explain_choice(choice)
        if channel["channel"] == "delivery":
            note += f" 含配送 ¥{channel.get('delivery_fen', 0) / 100:.2f} + 打包 ¥{channel.get('packing_fen', 0) / 100:.2f}。"
        if needs_car and not driving:
            note += " 你没开车，这条只作对照，不进入裁决。"
        row = {
            "channel": channel["channel"],
            "label": channel["label"],
            "store_name": channel["store_name"],
            "store_code": channel["store_code"],
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
                    channel["channel"],
                    channel["label"],
                    chosen.price_fen or 0,
                    minutes,
                    channel["store_name"],
                    channel["store_code"],
                    note,
                    chosen.name,
                    channel.get("delivery_fen", 0),
                    channel.get("packing_fen", 0),
                )
            )

    verdict = decide(quotes, wage_yuan_per_hour=wage, max_active_minutes=max_minutes)
    for row in rows:
        row["recommended"] = row["in_decision"] and row["channel"] == verdict.recommended

    return {
        "scenario": {
            "id": scenario["id"],
            "title": scenario["title"],
            "place": scenario["place"],
            "source": scenario["source"],
            "captured_at": scenario["captured_at"],
        },
        "headline": verdict.recommended_label,
        "reason": verdict.reason,
        "critical_wage_yuan_per_hour": verdict.critical_wage_yuan_per_hour,
        "saving_yuan": verdict.saving_yuan,
        "extra_minutes": verdict.extra_minutes,
        "rows": rows,
        "verdict": asdict(verdict),
    }
