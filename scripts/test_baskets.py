#!/usr/bin/env python3
"""候选篮子：套餐盖住点名时，必须从一开始就参与比价。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baskets import BasketOffer, MenuItem, choose_basket, explain_choice, plan_baskets


BANSHI = "板烧鸡腿堡"
FRIES = "薯条"


def _menu() -> list[MenuItem]:
    return [
        MenuItem("1406", "板烧鸡腿堡", "single"),
        MenuItem("4810", "中薯条", "single"),
        MenuItem("4820", "大薯条", "single"),
        MenuItem("1440", "麦辣鸡腿汉堡", "single"),
        MenuItem(
            "9900005462",
            "板烧鸡腿堡三件套",
            "combo",
            ("板烧鸡腿堡", "中薯条", "可乐中杯"),
        ),
        MenuItem(
            "9900000890",
            "板烧鸡腿堡四件套",
            "combo",
            ("板烧鸡腿堡", "中薯条", "麦乐鸡4块", "可乐中杯"),
        ),
        MenuItem(
            "9900005466",
            "巨无霸三件套",
            "combo",
            ("巨无霸", "中薯条", "可乐中杯"),
        ),
        MenuItem("9900005456", "麦辣鸡腿汉堡三件套", "combo"),
    ]


class BasketPlanTests(unittest.TestCase):
    def test_combo_is_an_opening_option_before_prices(self) -> None:
        plan = plan_baskets([BANSHI, FRIES], _menu())
        names = [offer.name for offer in plan.to_price]
        self.assertIn("板烧鸡腿堡+中薯条", names)
        self.assertIn("板烧鸡腿堡三件套", names)
        self.assertIn("板烧鸡腿堡四件套", names)
        self.assertNotIn("巨无霸三件套", names)
        combo = next(offer for offer in plan.to_price if offer.name == "板烧鸡腿堡三件套")
        self.assertEqual(combo.extras, ("可乐中杯",))
        self.assertIn("巨无霸三件套", plan.rejected)
        self.assertNotIn("麦辣鸡腿汉堡三件套", plan.pending_inspection)

    def test_unopened_combo_matching_the_hero_item_cannot_be_dropped(self) -> None:
        items = [
            MenuItem("1406", "板烧鸡腿堡", "single"),
            MenuItem("4810", "中薯条", "single"),
            MenuItem("9900005462", "板烧鸡腿堡三件套", "combo"),
        ]
        plan = plan_baskets([BANSHI, FRIES], items)
        self.assertFalse(plan.ready)
        self.assertIn("板烧鸡腿堡三件套", plan.pending_inspection)
        self.assertNotIn("板烧鸡腿堡三件套", plan.rejected)

    def test_medium_fries_preferred_for_alacarte(self) -> None:
        plan = plan_baskets([BANSHI, FRIES], _menu())
        alacarte = next(offer for offer in plan.to_price if offer.kind == "alacarte")
        self.assertEqual(alacarte.components, ("板烧鸡腿堡", "中薯条"))
        self.assertEqual(alacarte.codes, ("1406", "4810"))

    def test_cheaper_combo_with_a_drink_wins(self) -> None:
        plan = plan_baskets([BANSHI, FRIES], _menu())
        priced = []
        for offer in plan.to_price:
            price = {"alacarte": 3700, "combo:9900005462": 3450, "combo:9900000890": 5700}[offer.basket_id]
            priced.append(
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
        choice = choose_basket(priced)
        self.assertEqual(choice.chosen.name, "板烧鸡腿堡三件套")
        self.assertEqual(choice.chosen.price_fen, 3450)
        self.assertIn("可乐中杯", choice.chosen.extras)
        text = explain_choice(choice)
        self.assertIn("¥34.50", text)
        self.assertIn("¥37.00", text)
        self.assertIn("可乐中杯", text)

    def test_same_price_keeps_the_combo(self) -> None:
        offers = [
            BasketOffer("alacarte", "alacarte", "板烧鸡腿堡+中薯条", ("板烧鸡腿堡", "中薯条"), (), ("1406", "4810"), 4940),
            BasketOffer(
                "combo:9900002996",
                "combo",
                "板烧鸡腿堡中套餐",
                ("板烧鸡腿堡", "中薯条", "可口可乐中杯"),
                ("可口可乐中杯",),
                ("9900002996",),
                4940,
            ),
        ]
        choice = choose_basket(offers)
        self.assertEqual(choice.chosen.kind, "combo")

    def test_more_expensive_combo_stays_visible_but_loses(self) -> None:
        offers = [
            BasketOffer("alacarte", "alacarte", "板烧鸡腿堡+中薯条", ("板烧鸡腿堡", "中薯条"), (), ("1406", "4810"), 3700),
            BasketOffer("combo:x", "combo", "板烧鸡腿堡四件套", ("板烧鸡腿堡", "中薯条", "可乐中杯"), ("可乐中杯",), ("x",), 5700),
        ]
        choice = choose_basket(offers)
        self.assertEqual(choice.chosen.kind, "alacarte")
        self.assertEqual(choice.alternatives[0].name, "板烧鸡腿堡四件套")


if __name__ == "__main__":
    unittest.main()
