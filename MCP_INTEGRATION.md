# MCP 集成说明 · 麦麦去留

## 使用的 MCP Server

- **名称**：麦当劳中国 MCP（mcd-mcp）
- **接入**：`https://mcp.mcd.cn`（Streamable HTTP）
- **鉴权**：`Authorization: Bearer ${MCD_MCP_TOKEN}`
- **参考**：[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)

## 实际调用的 Tools

| Tool | 在本项目中的作用 |
|---|---|
| `now-time-info` | 确认当前时段，避免推荐已过期餐段 |
| `query-nearby-stores` | 拉取到店自取 / 得来速门店与距离 |
| `delivery-query-addresses` | 列出用户外送地址 |
| `delivery-query-stores` | 按地址查可配送门店与 `beCode` |
| `query-meals` | 各通道分别取实时菜单，匹配同类商品 |
| `query-store-coupons` | 各通道可用券（可选） |
| `available-coupons` / `auto-bind-coupons` | 领券后再核价（需用户确认） |
| `calculate-price` | **核心**：官方到手价（含配送/打包/优惠） |
| `create-order` | 仅用户明确下单时使用 |

本地 `scripts/decide.py` **不调用** MCP，只消费核价结果做临界时薪与 ETA 裁决。

## 调用流程

```text
用户：想吃巨无霸，我大概 10 分钟能走到店，时薪随便按 50 算
        │
        ▼
now-time-info
        │
        ├─ query-nearby-stores(beType=1) ──► 自取门店 + distance
        ├─ query-nearby-stores(beType=5) ──► 得来速门店 + beCode
        └─ delivery-query-addresses → delivery-query-stores(beType=2)
        │
        ▼
query-meals × 3（各通道菜单，匹配「巨无霸*套餐」同类）
        │
        ▼
calculate-price × 3（得到 price 分；外送含 delivery/packing）
        │
        ▼
scripts/decide.py（临界时薪 + 综合成本排序）
        │
        ▼
输出「去 / 留」裁决表；询问是否下单
```

## 业务价值

1. **把「到店还是外送」从感觉题变成可核对的算术题。**  
   差价往往藏在配送费、打包费、通道价差和互不通用的券池里，肉眼容易算错。
2. **第一输入是时间，不是优惠话术。**  
   适合开会间隙、通勤路上、带娃出门前等真实纠结场景。
3. **核价交给官方，裁决交给可测代码。**  
   Agent 不口算满减；`decide.py` 有单元测试，结论可复现。

## 实测快照（2026-10-22，天津小白楼）

数据见 `fixtures/sample_quote.json`：

| 通道 | 到手价 | 主动时间 |
|---|---:|---:|
| 到店自取 · 巨无霸三件套 | ¥36.50 | ≈7 分钟 |
| 得来速 · 巨无霸三件套 | ¥37.50 | ≈12 分钟 |
| 麦乐送 · 巨无霸中套餐 | ¥51.90（含配送 ¥6 + 打包 ¥1.9） | 0 分钟 |

到店相对外送约省 ¥15.40；若主动时间差 7 分钟，临界时薪约 ¥132/小时。  
（实时结果以再次调用 MCP 为准。）
