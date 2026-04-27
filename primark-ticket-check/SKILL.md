---
name: primark-ticket-check
description: 比对 Primark 条码贴/价签 PDF 与原始 Ticket Request PDF，校验商品信息（SKU/ORIN/Kimball/条码/颜色/尺码/价格/币种/供应商号）是否一致，并对打印数量做“友情提醒”级别的差异提示（不作强校验）。当用户发来 Primark 的 Ticket Request 和工厂打样的条码贴/价签/Hangtag PDF 要求核对、检查、比对、查错时使用。也适用于 Primark PO 单据下条码贴的版面排查。**首选直接调 scripts/compare.py生成结构化 JSON 后渲染 Markdown 报告，避免跨模型差异。**
---

# Primark 条码贴比对 Skill

## 📁 输出路径约定（强制执行）

> ⚠️ **所有生成物必须落到固定路径，并在最终回复里向用户打印「绝对路径」。** 否则不同模型 cwd 不同，文件散落各处，用户找不到。

### 默认输出位置（脚本会自动创建目录）

| 类型 | 路径 |
|---|---|
| **采购单 .xls** | `~/.openclaw/workspace/agents/textile-trade/projects/Primark/<款号>/<日期>/<款号> 价格小圆贴&条码贴 采购单-YYYY.M.D.xls` |
| **条码贴比对结果 JSON** | `~/.openclaw/workspace/agents/textile-trade/projects/Primark/<款号>/比对结果-条码贴-YYYYMMDD-HHMM.json` |
| **洗标比对结果 JSON** | `~/.openclaw/workspace/agents/textile-trade/projects/Primark/<型号>/比对结果-洗标-YYYYMMDD-HHMM.json` |
| **Markdown 报告** | 同目录下，文件名前缀 `比对报告-` 或 `采购单生成报告-` |

### 在最终回复里的强制输出格式

```
✅ 完成

📍 文件路径
- 采购单: ~/.openclaw/workspace/agents/textile-trade/projects/Primark/991184191/20260427/...
- 报告: ~/.openclaw/workspace/agents/textile-trade/projects/Primark/991184191/20260427/...
```

**禁止**只说"已生成在 workspace 下"或"在 projects 目录里"——必须给出**完整可复制的路径**。

> 💡 **路径写法**：在文档/报告里展示路径时统一用 `~/` 形式（去用户名，便于跨机器复用）。
> 脚本内部解析与文件 IO 仍用绝对路径（`pathlib.Path.home()` 自动展开）。
> 报告元信息里的"绝对路径"字段，模型应将 `$HOME` 前缀替换为 `~` 后再输出。

---

## ⛔ 强制流程 (DO NOT SKIP)

> 🚨 **本 skill 任何一次调用，都必须严格按以下三步走，禁止跳过、禁止偷懒、禁止用 LLM 自己读文件代替。**

### Step 1 — 必须先调脚本

```bash
python3 <SKILL_DIR>/scripts/compare.py <Ticket_Request.PDF> <工厂打样.PDF> -o <项目目录>/比对结果-条码贴-<ORIN>-<YYYYMMDD-HHMM>.json
cat <项目目录>/比对结果-条码贴-<ORIN>-<YYYYMMDD-HHMM>.json
```

**禁止行为（违反一项即视为本次任务失败）：**
- ❌ 不调脚本，自己用 PyMuPDF / pdfplumber / pdftotext 读 PDF 后凭文本理解硬比对
- ❌ 不调脚本，凭训练数据猜 Primark Ticket Request 字段格式
- ❌ 调了脚本但忽略 JSON，自己另写一份比对结论
- ❌ 脚本报错就跳过——脚本报错必须先修脚本，不要绕过

**唯一允许 LLM 介入比对的场景**：脚本明确返回 `{"unsupported": true, "reason": "..."}`，且原因合理。

### Step 2 — 必须按 REPORT_TEMPLATE.md 渲染

报告 Markdown 必须严格遵循 `<SKILL_DIR>/REPORT_TEMPLATE.md` 定义的章节结构和最小字段数。

**模型职责仅限于**：
1. 触发 Step 1 脚本
2. 读取 JSON
3. 把 JSON 字段填入 REPORT_TEMPLATE.md 的占位符
4. 对 issues 给修改建议

**不允许**：
- ❌ 自创章节顺序、自创字段名
- ❌ 省略基本信息表、价格币种表、EAN13 校验表、数量分组表中的任何一个
- ❌ 漏掉 "📝 给工厂的回复建议" 中英双语
- ❌ 漏掉 "📎 报告元信息" 中的模型标识、JSON 路径、绝对路径

### Step 3 — 必做自检

输出报告前，对照 `REPORT_TEMPLATE.md` 末尾的「最小字段数要求」和「禁止行为」逐条核对。**任何一条不满足，回炉重写。**

### 脚本接口

**输出 JSON Schema**：`{verdict, checks[], quantities, issues[], warnings[]}`
- `verdict`：PASS / WARN / FAIL 三档
- 已自动处理：条码空格切断（PDF 中 `5 397362 209987` 常见）、Kimball-7 集合、SKU/EAN-13 集合系统化比对

**报告归档路径**：`projects/Primark/<PO>/比对报告-条码贴-<ORIN>-<时间戳>.md`

---

## 适用场景

- 客户:**Primark**(爱尔兰快时尚集团)
- 输入:
  - **基准文件** = `Ticket_Request_<PO号>_<n>.PDF`(Primark 系统导出的票据请求,权威基准)
  - **待检文件** = 工厂/制版方做的条码贴/价签 PDF(通常文件名形如 `YY.M.D-<款号>条码贴.pdf`)
- 目的:在批量印刷前发现错误,避免返工。

## 校验维度(按严重度分级)

### 🔴 强校验项(必须 100% 一致,错一个就阻断印刷)

| 字段 | Ticket Request 字段名 | 说明 |
|---|---|---|
| **Style ORIN(款号)** | `Style ORIN` | 9 位数字,唯一识别一款商品 |
| **SKU** | `SKU` | 9 位数字,每个尺码一个 SKU |
| **EAN13 条码** | `Barcode` | 13 位,最后一位是校验位,必须能读出 |
| **Kimball 号** | `Kimball Number` | 7 位,每个尺码一个 |
| **供应商号** | `Supplier ID` | 5 位(如 80277) |
| **颜色** | `Colour Description` | 大小写不敏感,但拼写必须一致 |
| **尺码** | `Size Description` | 如 0-6M HAT 0-6M/44 |
| **Department-Section-Subsection** | `Department/Section/Subsection` | 形如 `15-21-15` |
| **价格数值** | `Price <CCY>` | 每个 region 的价格金额 |
| **价格币种** | 列名中的货币代码 | EUR/GBP/USD/AED/BHD/KWD/QAR/CZK/PLN/RON 等 |
| **Tag Type** | `Tag Type` | 如 Small Self-Adhesive Label |

### 🟡 友情提醒项(数量差异 - 不阻断,只提示)

> ⚠️ **数量不作为强校验**:考虑到印刷损耗、备品、版面排版限制,工厂打的条码贴数量比 Ticket Request 少属于正常现象。**只在报告里提示出来即可,不要把它列为"严重问题"或"必须修改"。**

> 💡 **关键经验**:Ticket 数量 = **PO 数量 × 1.02(含 2% 损耗)**。所以如果工厂打回来的条码贴数量 ≈ `Ticket ÷ 1.02`(即真实 PO 数),那是**完全正确**的,不是少印!只有当数字明显低于 PO 数(比例 <0.97)或明显高于 Ticket 数(>1.05)时才值得追问。

判断口径:
- 如果有 PO 文件 → 比对 PO 数量为基准
- 没有 PO → 用 `round(Ticket / 1.02)` 估算 PO 数,再比对

报告时只列:总数差异、各价格分组 × 各尺码 的数量,并标注"已扣 2% 损耗后基本一致 ✓"或"差异异常,建议核对"。

### 🔵 信息项

- 交货时间(Date)、Delivery Number、Destination PO - 仅供参考,条码贴上一般不体现。

---

## 比对流程

### Step 1. 先看文件存在 & 拿基础信息

```bash
ls -la <workspace>/
```

### Step 2. 提取 Ticket Request 文本(PyPDF 即可,文本流是干净的)

```python
import pypdf
r = pypdf.PdfReader("Ticket_Request_<PO>_0.PDF")
for p in r.pages:
    print(p.extract_text())
```

**Ticket Request 的标准结构**:
- Header:PO 号、Style ORIN、Name、Kimball、Supplier ID、Total Units QTY、Tag Type
- 多个 Delivery 块(Delivery Number / Date / Destination PO / Units QTY)
- 多个 **Region 表**(每个 region 一张表):ROI / GCC / ROO / NE1-MGB / NE2-BOR / IB / UK / US1-PA / US2-FL 等
  - 每个 region 表里有 3 行(每个尺码一行),列:SKU / ORIN / Barcode / Kimball / Colour / Unit QTY of Tickets / Size 系列 / Price 系列

### Step 3. 提取条码贴文本(用 PyMuPDF 拿带坐标的 words,因为条码贴是图形排版,普通文本提取会乱序)

```python
import fitz
doc = fitz.open("<待检条码贴>.pdf")
page = doc[0]
words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word)
words.sort(key=lambda w: (round(w[1]/5)*5, w[0]))
```

按 y 分行、按 x 分列(通常 3 列布局),重建版面后逐个标签提取字段。

> 💡 **注意**:条码贴的 EAN13 数字是逐个字符放的(每个数字一个 word),需要按 y 一致 + x 相邻拼接成完整 13 位串。

### Step 4. 把条码贴按"价格款"分组(关键!)

> Primark 条码贴是**按价格款合并印刷**的,不是按 region 一一对应。要把 Ticket Request 的 region 按相同价格组合并:

| 条码贴上的价格款 | 对应 Ticket Request Region | 说明 |
|---|---|---|
| `£4.00` | UK | 英国 GBP |
| `€6.00` | ROI + ROO + IB | 爱尔兰 + 欧陆其他 + 伊比利亚(同 EUR 价) |
| `$9.00` | US1-PA + US2-FL | 美国 USD |
| `€7.00 / 26.00 PLN / 155,00 Kč / 30,00 LEI` | NE1-MGB + NE2-BOR | 中东欧多币种 |
| `AED29 / BHD3.000 / KWD2.400 / QAR29` | GCC | 海湾合作国家 |

> ⚠️ Primark region 划分会根据 PO 不同有变化(比如有的 PO 没有 GCC,有的会多 Brazil/Australia),**以实际 Ticket Request 里出现的 region 表为准**,不要写死映射。判断"哪些 region 该合并"的依据是**它们的价格组合完全相同**。

### Step 5. 逐项核对,输出报告(屏幕展示 + 落盘归档)

按下面"输出格式"产出。**报告必须同时落到磁盘**(见 Step 6),不能只在聊天里输出就完事。

### Step 6. 报告落盘(强制要求!)

**这是流程最后一步,永远不能跳过。** 即使全部通过,也必须存一份归档报告。

#### 落盘规则

1. **目录**:`<workspace>/projects/Primark/<PO号>/`(不存在则 `mkdir -p` 创建)
2. **文件名**:`比对报告-条码贴-<款号>-YYYYMMDD-HHMM.md`
   - 同一天多次校验不会覆盖(带时分)
   - 例:`比对报告-条码贴-991185354-20260424-2336.md`
3. **内容**:与聊天里输出的报告**完全一致**(含强校验表、数量提示、给工厂的回复建议)
4. **末尾必须附**:
   - 基准/待检文件的绝对路径
   - 校验时间(含时区)
   - 由哪个 skill 生成(`primark-ticket-check`)
   - 自动结论行:`Verdict: PASS / FAIL`

#### 标准代码片段

```python
import os, datetime, pathlib

# Workspace 根目录解析(按优先级):
#   1. 环境变量 OPENCLAW_WORKSPACE_DIR
#   2. 当前工作目录 cwd
ws = pathlib.Path(os.environ.get("OPENCLAW_WORKSPACE_DIR") or os.getcwd()).resolve()

po = "1255718"          # 从 Ticket Request 读取
style = "991185354"     # 从 Ticket Request 读取
verdict = "PASS"        # or "FAIL"
now = datetime.datetime.now().astimezone()

out_dir = ws / "projects" / "Primark" / po
out_dir.mkdir(parents=True, exist_ok=True)
fname = f"比对报告-条码贴-{style}-{now:%Y%m%d-%H%M}.md"
out_path = out_dir / fname

footer = f"""\n\n---\n\n## 📎 报告元信息(自动生成)\n\n- **基准文件**: `{ticket_path}`\n- **待检文件**: `{label_path}`\n- **校验时间**: {now:%Y-%m-%d %H:%M %Z}\n- **生成 skill**: primark-ticket-check\n- **Verdict**: {verdict}\n"""

out_path.write_text(report_md + footer, encoding="utf-8")
print(f"✅ 报告已归档: {out_path}")
```

#### 在聊天结尾必须告诉用户

报告生成后,**末尾要明确告诉用户报告路径**,并附一句"已存档,可直接拷贝/转发给工厂确认"。例如:

> 📁 **报告已存**: `projects/Primark/1255718/比对报告-条码贴-991185354-20260424-2336.md`
> (可直接转发给工厂作为确认依据)

---

## 输出格式(必须严格遵守)

```markdown
# 📋 Primark 条码贴 vs Ticket Request 比对报告

**PO 号**: <从基准文件读取>
**Style ORIN**: <款号>
**基准文件**: <Ticket_Request_xxx.PDF>
**待检文件**: <条码贴文件名>

## ✅ 商品基本信息核对

<表格:字段 / Ticket Request / 条码贴 / 状态>

## ✅/❌ 强校验项

如果全部通过:
> **强校验项全部通过,可以批量印刷。**

如果有错:
> 🔴 **以下字段不一致,必须修正后才能印刷:**
> <逐项列出>

## ⚠️ 数量提示(仅供参考,不阻断)

<表格:分组 / 应印 / 实印 / 差额>

> 💡 数量差异属正常现象(印刷损耗 / 版面限制 / 备品),如差异比例较大(>5%)建议和制版方确认是否漏取 destination;否则可直接放行。

## 📝 给工厂的回复建议(中英对照)

[只在有强校验项错误时才生成。如果只是数量提示,写一句简短的"数量已注意,可印刷"即可。]
```

---

## 关键规则

1. **数量永远不要写成"❌严重问题"**。只用 ⚠️ 或 💡,措辞用"提示""仅供参考""可放行"。
2. **强校验项错一个,回复建议必须包含"请勿开始批量印刷"**。
3. **EAN13 条码不能只比文本,要校验末位**(mod 10)。如果文本对了但校验位算不出,说明可能是 OCR 错误。
4. **价格币种和符号要分清**:`€` ≠ `EUR`(同义但表现不同),`Kč` 是捷克克朗 CZK,`LEI` 是罗马尼亚列伊 RON,`PLN` 波兰兹罗提,`AED/BHD/KWD/QAR` 中东四货币。报告中保持原文符号即可。
5. **如果条码贴有多页**,先 `fitz.open().page_count` 看一下,每页都要处理。
6. **Tag Type 要核对**:Small Self-Adhesive Label / Large Self-Adhesive / Hangtag 等不同类型的版面差很远,工厂用错类型是常见错误。

## 常见 Primark Region 速查表

| 代号 | 全称 | 主要市场 | 默认币种 |
|---|---|---|---|
| ROI | Republic of Ireland | 爱尔兰 | EUR |
| ROO | Rest of Europe (Open) | 法/比/荷/卢/奥/葡 等 | EUR |
| IB | Iberia | 西班牙 | EUR |
| UK | United Kingdom | 英国 | GBP |
| NE1-MGB | New Europe 1 - Mainland Group B | 捷克/斯洛伐克/匈牙利 | CZK + EUR + PLN + RON |
| NE2-BOR | New Europe 2 - Border | 波兰/罗马尼亚 等 | 同 NE1 |
| US1-PA | US Region 1 - Pennsylvania DC | 美国东 | USD |
| US2-FL | US Region 2 - Florida DC | 美国南 | USD |
| GCC | Gulf Cooperation Council | 阿联酋/巴林/科威特/卡塔尔 | AED/BHD/KWD/QAR |

---

## EAN13 校验位算法(备用)

```python
def ean13_check(code12: str) -> int:
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(code12))
    return (10 - s % 10) % 10

# 示例
assert ean13_check("539736706307") == 2  # 5397367063072 ✓
```

## 工作目录约定

- 待比对文件默认在 `<workspace>/workspace/` 下
- 中间产物(PNG 渲染、临时 JSON)放 `<workspace>/workspace/_check/`
- **比对报告必须落盘** → `<workspace>/projects/Primark/<PO号>/比对报告-条码贴-<款号>-YYYYMMDD-HHMM.md`(见 Step 6 强制规则)
