#!/usr/bin/env python3
"""小程序裁决：套餐从第一轮就参与，得来速默认不进地铁场景。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "miniapp"))

from engine import run_verdict  # noqa: E402
from locate import place_from_nominatim  # noqa: E402


class MiniAppTests(unittest.TestCase):
    def test_banshao_opens_with_the_cheaper_combo(self) -> None:
        result = run_verdict("banshao", minutes_to_spot=5)
        pickup = next(row for row in result["rows"] if row["channel"] == "pickup")
        delivery = next(row for row in result["rows"] if row["channel"] == "delivery")
        drive = next(row for row in result["rows"] if row["channel"] == "drivethru")
        self.assertEqual(result["headline"], "到店自取")
        self.assertEqual(pickup["product_name"], "板烧鸡腿堡三件套")
        self.assertEqual(pickup["price_yuan"], 34.5)
        self.assertIn("可乐中杯", pickup["note"])
        self.assertIn("37.00", pickup["note"])
        self.assertEqual(delivery["product_name"], "板烧鸡腿堡中套餐")
        self.assertFalse(drive["in_decision"])
        self.assertEqual(pickup["minutes"], 5)
        self.assertEqual(result["scenario"]["place"], "位置还没填")
        self.assertEqual(result["critical_wage_yuan_per_hour"], 178.8)

    def test_high_wage_stays_for_delivery(self) -> None:
        result = run_verdict("banshao", minutes_to_spot=5, wage=200)
        self.assertEqual(result["headline"], "麦乐送")

    def test_driving_lets_drivethru_into_the_decision(self) -> None:
        result = run_verdict("banshao", minutes_to_spot=5, driving=True)
        drive = next(row for row in result["rows"] if row["channel"] == "drivethru")
        self.assertTrue(drive["in_decision"])
        self.assertEqual(drive["product_name"], "板烧鸡腿堡三件套")

    def test_mala_coupon_is_its_own_snapshot(self) -> None:
        result = run_verdict("mala", minutes_to_spot=5)
        pickup = next(row for row in result["rows"] if row["channel"] == "pickup")
        self.assertEqual(pickup["price_yuan"], 25.4)
        self.assertEqual(result["headline"], "到店自取")

    def test_reverse_geocode_uses_city_and_suburb(self) -> None:
        found = place_from_nominatim(
            {"address": {"city": "上海市", "suburb": "徐家汇", "road": "衡山路"}}
        )
        self.assertEqual(found["label"], "上海市 · 徐家汇")

    def test_menu_lists_burger_snack_and_drink(self) -> None:
        from engine import menu_groups

        groups = {item["id"]: item for item in menu_groups()}
        self.assertEqual([item["label"] for item in menu_groups()], ["汉堡", "小食", "饮料"])
        burgers = [item["name"] for item in groups["burger"]["items"]]
        snacks = [item["name"] for item in groups["snack"]["items"]]
        drinks = [item["name"] for item in groups["drink"]["items"]]
        self.assertIn("板烧鸡腿堡", burgers)
        self.assertIn("巨无霸", burgers)
        self.assertIn("薯条", snacks)
        self.assertIn("可乐", drinks)

    def test_picked_juba_and_fries_prefers_combo(self) -> None:
        result = run_verdict(names=["巨无霸", "薯条"], minutes_to_spot=5)
        pickup = next(row for row in result["rows"] if row["channel"] == "pickup")
        self.assertEqual(pickup["product_name"], "巨无霸三件套")
        self.assertEqual(pickup["price_yuan"], 36.5)

    def test_fries_spicy_taro_and_cola_are_on_pickup(self) -> None:
        result = run_verdict(names=["薯条", "麦辣鸡腿汉堡", "香芋派", "可乐"], minutes_to_spot=8, place="上海市 · 徐家汇")
        pickup = next(row for row in result["rows"] if row["channel"] == "pickup")
        delivery = next(row for row in result["rows"] if row["channel"] == "delivery")
        self.assertTrue(pickup["in_decision"])
        self.assertEqual(pickup["price_yuan"], 54.0)
        self.assertEqual(pickup["minutes"], 8)
        self.assertTrue(delivery["in_decision"])
        self.assertEqual(result["scenario"]["place"], "上海市 · 徐家汇")
        self.assertNotIn("天津地铁", result["scenario"]["place"])

    def test_picked_chicken_uses_menu_price(self) -> None:
        result = run_verdict(names=["麦香鸡"], minutes_to_spot=5)
        pickup = next(row for row in result["rows"] if row["channel"] == "pickup")
        self.assertEqual(pickup["product_name"], "麦香鸡")
        self.assertEqual(pickup["price_yuan"], 17.0)

    def test_mix_from_different_channels_explains_the_gap(self) -> None:
        with self.assertRaises(ValueError) as caught:
            run_verdict(names=["心形薯饼8块", "双层脆鸡堡"], minutes_to_spot=5)
        message = str(caught.exception)
        self.assertIn("到店自取没有双层脆鸡堡", message)
        self.assertIn("麦乐送没有心形薯饼8块", message)
        self.assertNotIn("都对不上", message)

    def test_drive_only_item_asks_to_include_the_car(self) -> None:
        with self.assertRaises(ValueError) as caught:
            run_verdict(names=["怡泉+C"], minutes_to_spot=5)
        self.assertIn("我开着车", str(caught.exception))

    def test_short_limit_drops_the_walk(self) -> None:
        result = run_verdict("banshao", minutes_to_spot=5, max_minutes=3)
        self.assertEqual(result["headline"], "麦乐送")


if __name__ == "__main__":
    unittest.main()
