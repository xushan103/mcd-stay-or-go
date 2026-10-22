#!/usr/bin/env python3
"""decide.py 单元测试（不依赖 MCP 网络）。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decide import (
    ChannelQuote,
    critical_wage,
    decide,
    estimate_drive_minutes,
    estimate_walk_minutes,
    fen_to_yuan,
)


ROOT = Path(__file__).resolve().parents[1]


class DecideTests(unittest.TestCase):
    def test_fen_to_yuan(self) -> None:
        self.assertEqual(fen_to_yuan(3650), 36.5)
        self.assertEqual(fen_to_yuan(5190), 51.9)

    def test_critical_wage_matches_sample(self) -> None:
        # 外送 51.9 vs 到店 36.5，多花 12 分钟 → 15.4 * 60 / 12 = 77
        cw = critical_wage(3650, 12, 5190, 0)
        self.assertEqual(cw, 77.0)

    def test_decide_prefers_pickup_when_wage_low(self) -> None:
        quotes = [
            ChannelQuote("pickup", "到店自取", 3650, 12, notes="步行"),
            ChannelQuote("drivethru", "得来速", 3750, 12, notes="开车"),
            ChannelQuote("delivery", "麦乐送", 5190, 0, notes="等外卖"),
        ]
        v = decide(quotes, wage_yuan_per_hour=30)
        self.assertEqual(v.recommended, "pickup")

    def test_decide_prefers_delivery_when_wage_high(self) -> None:
        quotes = [
            ChannelQuote("pickup", "到店自取", 3650, 25),
            ChannelQuote("delivery", "麦乐送", 5190, 0),
        ]
        v = decide(quotes, wage_yuan_per_hour=80)
        self.assertEqual(v.recommended, "delivery")

    def test_max_minutes_filters_long_walk(self) -> None:
        quotes = [
            ChannelQuote("pickup", "到店自取", 3650, 40),
            ChannelQuote("delivery", "麦乐送", 5190, 0),
        ]
        v = decide(quotes, max_active_minutes=15)
        self.assertEqual(v.recommended, "delivery")

    def test_eta_helpers(self) -> None:
        # 101m 步行约 1.3 + 5 等待
        self.assertAlmostEqual(estimate_walk_minutes(101), 6.3, places=1)
        self.assertAlmostEqual(estimate_drive_minutes(3841), 11.7, places=1)

    def test_fixture_loads(self) -> None:
        path = ROOT / "fixtures" / "sample_quote.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        quotes = [ChannelQuote(**q) for q in raw["quotes"]]
        v = decide(quotes, wage_yuan_per_hour=50)
        self.assertIn(v.recommended, {"pickup", "drivethru", "delivery"})
        self.assertTrue(v.reason)


if __name__ == "__main__":
    unittest.main()
