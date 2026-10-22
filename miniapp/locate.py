"""把浏览器给的坐标收成城市和地点。不假定人在天津小白楼。"""

from __future__ import annotations


def place_from_nominatim(data: dict) -> dict:
    address = data.get("address") or {}
    city = address.get("city") or address.get("town") or address.get("state") or ""
    keyword = (
        address.get("suburb")
        or address.get("neighbourhood")
        or address.get("road")
        or address.get("city_district")
        or ""
    )
    label = " · ".join(part for part in (city, keyword) if part)
    return {"city": city, "keyword": keyword, "label": label}
