# 麦麦去留 · mcd-stay-or-go

> 同一顿麦当劳，到店自取 / 得来速 / 麦乐送三条路。  
> **先问你还要多久，再告诉你该不该出门。**

麦当劳程序员创意开发大赛参赛作品 · 基于官方 MCP · **非麦当劳官方产品**。

---

## 它解决什么

「点外送贵一点但不用动」和「下楼能省十几块」天天纠结。  
差价不只藏在餐品标价里，还藏在：

1. **配送费 + 打包费**
2. **三套互不通用的券池**
3. **外送 / 到店菜单编码与定价并不相同**

本 Skill 对三条履约通道分别走官方 `calculate-price`，再用你的 **到店 ETA / 出门上限 / 自评时薪** 做裁决——  
输出不是又一句「到店更便宜」，而是：

**「按你现在的时间，去还是留。」**

---

## 一句话样例（天津小白楼 · 实算快照）

想吃巨无霸套餐时：

| 通道 | 到手价 | 你要花的时间 |
|---|---:|---:|
| 到店自取 | **¥36.50** | ≈7 分钟（步行 101m） |
| 得来速 | ¥37.50 | ≈12 分钟（驾车约 3.8km） |
| 麦乐送 | ¥51.90 | 0 分钟（含配送 ¥6 + 打包 ¥1.9） |

到店比外送省约 **¥15.40**。若你时薪明显高于临界值，外送更划算；否则下楼。

> 完整 JSON 见 `fixtures/sample_quote.json`。价格会变，请以 MCP 实时核价为准。

---

## 和已有作品怎么区分

| | 常见「省钱助手」 | 三路比价 + 时薪类 | **麦麦去留（本项目）** |
|---|---|---|---|
| 第一问 | 预算 / 最省 | 三条路谁便宜 | **你还要多久能到店** |
| 输出 | 推荐套餐 | 临界时薪表 | **去 / 留 一句话裁决** |
| 默认动作 | 常引导凑单 | 比价 | **决策辅助，默认不下单** |

---

## 仓库结构

```text
SKILL.md                 # Agent Skill 主指令（Cursor / WorkBuddy 等）
MCP_INTEGRATION.md       # 使用的 MCP Tool 与调用链
CONTEST_DECLARATION.md   # 参赛声明（官方原文，勿改）
scripts/decide.py        # 临界时薪 / ETA 裁决引擎
scripts/test_decide.py   # 单元测试
fixtures/sample_quote.json
mcp-config.example.json
.env.example
docs/ISSUE_DRAFT.md      # 官方仓库报名 Issue 草稿
```

---

## 快速开始

### 1. 申请 MCP Token

打开 [麦当劳 MCP 开放平台](https://open.mcd.cn/mcp) → 登录 → 控制台激活 Token。

### 2. 配置 MCP Client

复制 `mcp-config.example.json`，把 `${MCD_MCP_TOKEN}` 换成环境变量或本地私密配置。  
**不要把真实 Token 写进仓库。**

### 3. 安装 Skill

- **Cursor**：把本仓库加入 Skill / 规则可读路径，或直接让 Agent 阅读 `SKILL.md`
- **WorkBuddy**：按官方文档配置 mcd-mcp 连接器后，导入本 Skill 对话流程

### 4. 本地试算（不需 Token）

```bash
python3 scripts/decide.py --fixture fixtures/sample_quote.json --wage 50
python3 -m unittest scripts/test_decide.py -v
```

---

## 目标用户

- 通勤 / 开会间隙纠结「下楼还是点外卖」的人
- 开车路过、想快速判断得来速是否值得绕路的人
- 不想再被「省钱话术」推着凑单，只想要一个说得清的结论的人

---

## 合规与声明

见 `CONTEST_DECLARATION.md`。项目输出仅供参考；餐品、价格、供应状态以麦当劳官方渠道实时结果为准。
