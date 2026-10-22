"""官方 calculate-price 快照。小程序用这些到手价做裁决，不把菜单标价相加。"""

from __future__ import annotations

from baskets import MenuItem


def _single(code: str, name: str) -> MenuItem:
    return MenuItem(code, name, "single")


def _combo(code: str, name: str, components: tuple[str, ...]) -> MenuItem:
    return MenuItem(code, name, "combo", components)


XIAOBAILOU = "麦当劳天津小白楼地铁站朗香街餐厅"
ZHENGLIDAO = "天津真理道得来速餐厅"

SCENARIOS: dict[str, dict] = {
    "banshao": {
        "id": "banshao",
        "title": "板烧鸡腿堡 + 薯条",
        "place": "天津地铁 1 号线 · 小白楼",
        "blurb": "出 A 口就是店。套餐和单点一起比。",
        "requested": ["板烧鸡腿堡", "薯条"],
        "default_minutes_to_spot": 5,
        "captured_at": "2026-10-22 14:06",
        "source": "小白楼店官方核价快照，不是这一秒的实时价",
        "channels": [
            {
                "channel": "pickup",
                "label": "到店自取",
                "store_name": XIAOBAILOU,
                "store_code": "1980053",
                "distance_m": 101,
                "items": [
                    _single("1406", "板烧鸡腿堡"),
                    _single("4810", "中薯条"),
                    _combo("9900005462", "板烧鸡腿堡三件套", ("板烧鸡腿堡", "中薯条", "可乐中杯")),
                    _combo("9900000890", "板烧鸡腿堡四件套", ("板烧鸡腿堡", "中薯条", "麦乐鸡4块", "可乐中杯")),
                ],
                "prices": {"alacarte": 3700, "combo:9900005462": 3450, "combo:9900000890": 5700},
            },
            {
                "channel": "drivethru",
                "label": "得来速",
                "store_name": ZHENGLIDAO,
                "store_code": "1980115",
                "distance_m": 3841,
                "needs_car": True,
                "items": [
                    _single("1406", "板烧鸡腿堡"),
                    _single("4810", "中薯条"),
                    _combo("9900005462", "板烧鸡腿堡三件套", ("板烧鸡腿堡", "中薯条", "可乐中杯")),
                ],
                "prices": {"alacarte": 3800, "combo:9900005462": 3450},
            },
            {
                "channel": "delivery",
                "label": "麦乐送",
                "store_name": XIAOBAILOU,
                "store_code": "1980053",
                "distance_m": 0,
                "items": [
                    _single("901406", "板烧鸡腿堡"),
                    _single("501205", "中薯条"),
                    _combo("9900002996", "板烧鸡腿堡中套餐", ("板烧鸡腿堡", "中薯条", "可口可乐中杯")),
                ],
                "prices": {"alacarte": 4940, "combo:9900002996": 4940},
                "delivery_fen": 600,
                "packing_fen": 190,
            },
        ],
    },
    "mala": {
        "id": "mala",
        "title": "麦辣券 + 薯条",
        "place": "天津地铁 1 号线 · 小白楼",
        "blurb": "11.9 元麦辣券用在麦辣上，薯条仍是原价。",
        "requested": ["麦辣鸡腿汉堡", "薯条"],
        "default_minutes_to_spot": 5,
        "captured_at": "2026-10-22 14:07",
        "source": "同一张麦辣券的官方核价快照，不是这一秒的实时价",
        "channels": [
            {
                "channel": "pickup",
                "label": "到店自取",
                "store_name": XIAOBAILOU,
                "store_code": "1980053",
                "distance_m": 101,
                "items": [_single("1440", "麦辣鸡腿汉堡"), _single("4810", "中薯条")],
                "prices": {"alacarte": 2540},
            },
            {
                "channel": "drivethru",
                "label": "得来速",
                "store_name": ZHENGLIDAO,
                "store_code": "1980115",
                "distance_m": 3841,
                "needs_car": True,
                "items": [_single("1440", "麦辣鸡腿汉堡"), _single("4810", "中薯条")],
                "prices": {"alacarte": 2640},
            },
            {
                "channel": "delivery",
                "label": "麦乐送",
                "store_name": XIAOBAILOU,
                "store_code": "1980053",
                "distance_m": 0,
                "items": [_single("1440", "麦辣鸡腿汉堡"), _single("501205", "中薯条")],
                "prices": {"alacarte": 3530},
                "delivery_fen": 600,
                "packing_fen": 190,
            },
        ],
    },
    "juba": {
        "id": "juba",
        "title": "巨无霸三件套",
        "place": "天津 · 小白楼",
        "blurb": "三条路各用官方套餐价，外送菜单编码不同。",
        "requested": ["巨无霸"],
        "default_minutes_to_spot": 0,
        "captured_at": "2026-10-22 11:08",
        "source": "fixtures/sample_quote.json 官方核价快照，不是这一秒的实时价",
        "channels": [
            {
                "channel": "pickup",
                "label": "到店自取",
                "store_name": XIAOBAILOU,
                "store_code": "1980053",
                "distance_m": 101,
                "items": [_combo("9900005466", "巨无霸三件套", ("巨无霸", "中薯条", "可乐中杯"))],
                "prices": {"combo:9900005466": 3650},
            },
            {
                "channel": "drivethru",
                "label": "得来速",
                "store_name": ZHENGLIDAO,
                "store_code": "1980115",
                "distance_m": 3841,
                "needs_car": True,
                "items": [_combo("9900005466", "巨无霸三件套", ("巨无霸", "中薯条", "可乐中杯"))],
                "prices": {"combo:9900005466": 3750},
            },
            {
                "channel": "delivery",
                "label": "麦乐送",
                "store_name": XIAOBAILOU,
                "store_code": "1980053",
                "distance_m": 0,
                "items": [_combo("9900003001", "巨无霸中套餐", ("巨无霸", "中薯条", "可乐中杯"))],
                "prices": {"combo:9900003001": 5190},
                "delivery_fen": 600,
                "packing_fen": 190,
            },
        ],
    },
}
