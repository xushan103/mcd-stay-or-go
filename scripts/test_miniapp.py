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
        self.assertEqual(result["critical_wage_yuan_per_hour"], 79.1)

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

    def test_short_limit_drops_the_walk(self) -> None:
        result = run_verdict("banshao", minutes_to_spot=5, max_minutes=5)
        self.assertEqual(result["headline"], "麦乐送")


if __name__ == "__main__":
    unittest.main()
