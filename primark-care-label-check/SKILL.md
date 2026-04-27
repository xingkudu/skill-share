---
name: primark-care-label-check
description: 比对 Primark 洗标 PDF（工厂打样）与"洗标采购单 .xls"和"洗标-模版 .pdf"**。首选直接调 scripts/compare.py 结构化比对后渲染 Markdown 报告，避免跨模型差异。**原描述：比对 Primark 洗标 PDF与"洗标采购单 .xls"和"洗标-模版 .pdf"，校验内容字段（部门号/Style/SKU/Kimball/供应商号/产地/日期/年龄段/成分/水洗说明/制造国/Cover&Body 多语言/阿拉伯文/EXCLUSIVE OF DECORATION 等）与采购单是否完全一致，并校验欧洲单/美国单的版面结构、阿拉伯文 RTL、批次分页与张数标注是否符合模板规范。当用户发来 Primark 洗标 PDF（通常文件名形如 `YY.M.D-<款号>洗标.pdf`）+ 洗标采购单 .xls 要求核对、检查、比对、查错时使用。
---

# Primark 洗标比对 Skill

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

> 🚨 **本 skill 任何一次调用，都必须严格按以下三步走，禁止跳过、禁止偷懒、禁止用 LLM 自己读 .xls / PDF 代替脚本。**

### Step 1 — 必须先调脚本

```bash
python3 <SKILL_DIR>/scripts/compare.py <洗标采购单.xls> <洗标 PDF> -o <项目目录>/比对结果-洗标-<型号>-<YYYYMMDD-HHMM>.json
cat <项目目录>/比对结果-洗标-<型号>-<YYYYMMDD-HHMM>.json
```

**禁止行为（违反一项即视为本次任务失败）：**
- ❌ 不调脚本，自己用 xlrd / openpyxl 读 .xls 后猜字段位置——**采购单 cell 映射是定制的，R4 是部门号、R37 是日期、R36 是产地，读错一行全部错位**
- ❌ 不调脚本，自己用 PyMuPDF / pdfplumber 读 PDF 后凭多语言文本猜含义
- ❌ 调了脚本但忽略 JSON，自己另写一份比对结论
- ❌ 脚本报错就跳过——必须先修脚本，不要绕过

**唯一允许 LLM 介入比对的场景**：脚本明确返回 `{"unsupported": true, "reason": "..."}`，且原因合理。

### Step 2 — 必须按 REPORT_TEMPLATE.md 渲染

报告 Markdown 必须严格遵循 `<SKILL_DIR>/REPORT_TEMPLATE.md` 定义的章节结构和最小字段数。

**模型职责仅限于**：
1. 触发 Step 1 脚本
2. 读取 JSON
3. 把 JSON 字段填入 REPORT_TEMPLATE.md 的占位符
4. 对 issues 给修改建议（含根因分析 + 具体修改方案到 cell 坐标）
5. **看图补充检查**脚本不能验证的部分（阿拉伯文拼写 / RTL / 字号 / 批次分页 / 张数标注）

**不允许**：
- ❌ 自创章节顺序、自创字段名
- ❌ 省略商品身份表（12+ 行）、成分字段表（Body+Cover 各一组）、版面结构表（5+ 检查项）中的任何一个
- ❌ 成分字段不标 "14 种欧洲语言是否齐全" + "阿拉伯文 RTL 是否正确"
- ❌ issues 只列问题不给根因与修复方案
- ❌ 漏掉 "📝 给工厂的回复建议" 中英双语
- ❌ 漏掉 "📎 报告元信息" 中的模型标识、JSON 路径、绝对路径

### Step 3 — 必做自检

输出报告前，对照 `REPORT_TEMPLATE.md` 末尾的「最小字段数要求」和「禁止行为」逐条核对。额外检查：

- [ ] 部门号是 `XX-XX-XX` 格式（不可能是 `01-06-26` 这种日期！）
- [ ] 产地字段是 `CHINA` / `中国` / `Made in China` 三者之一，不是 `CA` 这种两位简写
- [ ] 季节 = SS/AW + 两位年份（如 AW26）
- [ ] 如果任一项看起来"奇怪"（比如部门号是日期、产地是两位代码）——**这是你读错 .xls 位置了，重调脚本，不要交付**

**任何一条不满足，回炉重写。**

### 脚本接口

**输出 JSON Schema**：`{verdict, header, checks[], structure, languages_found, issues[], warnings[]}`
- `verdict`：PASS / WARN / FAIL 三档
- `header.style_orin / department / supplier / season / colour / made_in` 从 .xls 权威提取，不依赖模型猜
- `languages_found` 是所有出现的语言代码集合（如 `[en, en-uk, en-us, fr, es, de, ...]`）
- 脚本不能替代人工的部分：阿拉伯文拼写、版面行序、批次分页、字号字体 LOGO 大小

**报告归档路径**：`projects/Primark/<款号>/比对报告-洗标-<型号>-<时间戳>.md`

---

## 适用场景

- 客户：**Primark**（爱尔兰快时尚集团）
- 业务链路：
  ```
  洗标采购单.xls (用户) ──► 印刷厂打样 ──► 洗标 PDF ──► 本 skill 反核
                                            ▲
                                            │ 版面参照
                                       洗标-模版.pdf
  ```
- 三个输入：
  1. **基准内容文件** = `<款号>单 洗标采购单-YYYY.M.D.xls`（用户/采购员发给印刷厂的"图稿要求"，**字段权威基准**）
  2. **待检文件** = `YY.M.D-<款号>洗标.pdf`（印刷厂排好版回传的洗标）
  3. **版面参照** = `templates/洗标-模版.pdf`（一份历史款洗标，**版面/结构权威基准**，仅看结构不看具体字段值）

> **关键判断口径**：内容字段以采购单 .xls 为准；版面布局/结构以模板 PDF 为准。如果采购单和洗标都对、但和模板版面差很大，要追问采购单是否还有别的图稿要求；如果采购单和模板都是同一种结构、洗标排错了，提示工厂修。

---

## 校验维度（按严重度分级）

### 🔴 强校验项（必须 100% 一致，错一个就阻断印刷）

#### 1. 商品身份字段（采购单 vs 洗标 PDF）

| 字段 | 采购单单元格 | 洗标 PDF 上 |
|---|---|---|
| **款号 / Style** | R5 (`STYLE`) | 9 位数字（如 991183635） |
| **部门号 / Department-Section-Subsection** | R4 (`部门号`) | 形如 `15-24-15` 或 `15-24-25`（数字格式：`XX-XX-XX`） |
| **供应商号 / Supplier ID** | R6 (`供应商代码`) | 5 位（如 80277） |
| **SKU**（每个尺码一个） | R9-R10 列 B | 9 位数字 |
| **Kimball Number**（每个尺码一个） | R9-R10 列 C | 7 位数字 |
| **颜色 Colour** | R2 + R9 列 D | 标签上一般不直接显示颜色文字（颜色由"色面"决定），但如果出现要核对 |
| **季节** | R3 (`季节`) | RN CODE 行末，如 `AW26`（春夏 SS / 秋冬 AW） |

> ⚠️ **特别注意部门号易错点**：模板上的部门号是 `15-24-15`（参照款 991183624），而采购单上的部门号是这个款自己的（如 `15-24-25` for 991183635）。**永远以采购单 .xls 为准**，不要被模板上的数字误导。

#### 2. 成分字段（Body / Cover 各一组多语言）

采购单 R14 用一大段多语言文本规定 `Body:` 和 `Cover:` 的成分，例如：

```
Body:
en：61% POLYESTER
21% VISCOSE
17% POLYAMIDE
1% ELASTANE
ca: ...
[14 种欧洲语言全列]

Cover:
en：61% POLYESTER
21% VISCOSE
18% POLYAMIDE
... [14 种欧洲语言全列]
```

**核对规则**：
- 洗标 PDF 上"成分块"必须包含 `Body:` + `Cover:` 两个分组（如果采购单分了组）
- 每种语言代码（`en/ca/cs/de/el/es/fr/hu/it/nl/pl/pt/ro/sk/sl`）都要出现，不能漏一种
- **数字百分比必须完全一致**（61%/21%/17%+1% 或 61%/21%/18%）
- **欧洲单 vs 美国单的差别**（采购单 R14 列 B = 欧洲；列 D = 美国）：
  - 欧洲单写 `en: ...`
  - 美国单写 `en-uk: ... en-us: ...`（多一个 en-us 分组，因为美国单需要美式英语标签）
- 阿拉伯文成分必须出现（RTL 排版，靠右对齐），数字用阿拉伯-印度数字（٦١, ٢١, ١٧, ١, ١٨）

**易错点**：
- 工厂可能把 `1% ELASTANE` 错写成 `1% ELASTAN`（注意词尾，en/sl 不同）
- 意大利文 `it:` 在 Cover 里是 18% POLIAMMIDE，在 Body 里也写 18% 是规范（Primark 习惯如此）— 不要按"应该 17%"去改
- 希腊语/阿拉伯文 OCR 容易乱，按文本流读出来是什么就是什么

#### 3. 水洗说明（多语言）

采购单 R32 列 B = 水洗说明的标准多语言文本：

```
en: 30 DEGREE WASH IN MACHINE. DO NOT BLEACH. DO NOT TUMBLE DRY. DO NOT IRON. DO NOT DRY CLEAN.
ca: ...
... [14 欧洲语言]
ar: يُغسل في الغسالة بدرجة حرارة ٣٠ ...
```

**核对规则**：
- 必须出现 `30 DEGREE WASH` / `30°` / `30C` 三种符号化表示中的至少版面图形（一般洗标会同时印 `30C • 30` 这种小图形 + 多语言文字）
- 五条禁令必须齐全：`NO BLEACH / NO TUMBLE DRY / NO IRON / NO DRY CLEAN`
- 阿拉伯文位置要在右侧
- 如果采购单写了 `30°C`，洗标上也必须是 30°C；如果写 `60°C`，那就是 60°C（不要把温度看错）

#### 4. 制造国（多语言 "Made in China"）

采购单 R35 列 B = 多语言"Made in China"（14 种欧语 + 阿拉伯文 `ar: صنع في الصين`）。
洗标 PDF 上必须出现完整列表，且最后一行印 `Made in China`。

#### 5. 产地、批次日期（每个批次一个日期）

采购单 R36-R38：
| 字段 | 内容 |
|---|---|
| 产地 | `TAIZHOU / CHINA` |
| 第一批日期 | `01-06-26`（即 2026 年 6 月 1 日，DD-MM-YY 欧式） |
| 第二批日期 | `01-07-26`（即 2026 年 7 月 1 日） |

**核对规则**：
- 洗标 PDF 每个"批次块"都要出现对应日期
- 第一批的标签上印 `01-06-26`，第二批的标签上印 `01-07-26`
- 不要把日期格式看反（DD-MM-YY，不是 MM-DD-YY）

#### 6. 公司地址 + RN CODE + NIF（固定信息块）

采购单虽然没明示，但模板和现有洗标上都印这一段：

```
Primark Limited, 22-24 Parnell Street, Dublin, D01 P7W2, Ireland.
Primark Stores Limited, 41 West Street, Reading, RG1 1TZ, UK.
US Importer: Primark US Corp., 101 Arch Street, Suite 300, Boston MA 02110, USA.
www.primark.com
NIF - B83875427  AW26
RN CODE:145478
```

**强校验**：
- `NIF - B83875427` ← 固定值（Primark 西班牙税号）
- `RN CODE:145478` ← 固定值（美国 RN 注册号，必须出现否则美国海关查）
- 季节代码（如 `AW26`）必须和采购单 R3 一致

#### 7. 童款年龄段 Logo

采购单 R40 + R41-R42 规定：
```
2-4 en: YEARS ca: ANYS cs: ROKY ... ar: ٤-٢ سنوات
5-9 en: YEARS ca: ANYS cs: ROKY ... ar: ٩-٥ سنوات
```

**核对规则**：
- 每个尺码块（2-4Y / 5-9Y）都要有完整多语言 + 阿拉伯文
- 阿拉伯文里的数字必须用阿拉伯-印度数字字符（٢, ٤, ٥, ٩），不能写成 `2-4` 拉丁数字
- 顺序：洗标 PDF 上 2-4Y 标签印 `2-4`，5-9Y 标签印 `5-9`

#### 8. EXCLUSIVE OF DECORATION（仅美国单）

- 采购单 R22 列 D 写明只有 **美国单** 加这块文字（`美国单成分加上左图红字内容`）
- 校验：欧洲单页**不应**出现 EXCLUSIVE OF DECORATION，美国单页**必须**出现完整多语言版本
- 这是美国 FTC 16 CFR Part 303 的强制要求

---

### 🟡 版面 / 结构校验（与模板对照）

参照 `templates/洗标-模版.pdf`（两页：第 1 页欧洲单，第 2 页美国单）。

#### 标签尺寸约定

| 标签类型 | 尺寸 | 用途 |
|---|---|---|
| **大签** | `19.7 x 2.5 cm` | 第 1 页 + 第 4 页（含成分、水洗、制造国、地址、Style/SKU/Kimball、年龄段） |
| **小签** | `9.85 x 2.5 cm` | 第 2 / 3 / 5 / 6 页（只含成分 + 水洗，是"附页"性质） |
| 备注 | `1cm / 1.5cm / 2cm / 3cm / 4cm` | 模板里出现的小尺寸标注是**留白/边距说明**，不是标签尺寸 |

> 模板第 1 页欧洲单标了 `9.85x2.5cm` 在底部—— 表示该款的小签是 9.85cm 长。这个尺寸要核对洗标 PDF 顶部"材质(无纺布) 19.7x2.5cm"和底部"9.85x2.5cm"两处标注是否同时出现。

#### 版面分块（每页布局）

每页通常是横向两栏布局（2-4Y 一栏 + 5-9Y 一栏），每栏从上到下依次：

1. **顶部区**：`材质(无纺布)` + 标签尺寸 + 标题（如 `26TF4AK009欧洲单`）
2. **批次/页/张数**：`第1批第1页 / 12503张` 这种格式（大签）；`第1批第N页 / xxxx张` 还有 `第5页 / 第6页` 等附页
3. **正文区（标签内容）**：
   - 多语言成分（`Body:` + `Cover:` 两段）
   - 多语言水洗说明（含 `30C • 30` 符号 + 五条禁令）
   - 多语言"WASH BEFORE FIRST USE"
   - 多语言"Made in China"
   - 阿拉伯文 RTL 区段（必须靠右对齐）
   - 公司地址 + 日期（`TAIZHOU / CHINA` + `01-06-26`）
   - `NIF - B83875427  AW26`
   - `RN CODE:145478`
   - 部门号 + 供应商号（`15-24-XX  80277`）
   - Style + SKU（`991183XXX  21214XXXX`）
   - Kimball（`7678601` / `7678602` 等 7 位数字）
4. **年龄段块**：`2-4 en: YEARS ...` 或 `5-9 en: YEARS ...`
5. **附页（小签）**：只放成分 + 水洗 + 制造国，不放 Style/SKU 等身份字段

#### 版面提示项（与模板差异时只提示，不阻断）

- 阿拉伯文是否右对齐（RTL）— 模板里所有 `ar:` 段落都靠右
- "第1批第N页 / xxxx张" 标注的字号、位置是否合理
- 是否每个语言代码都换行写（**采购单 R14 备注："每个国家的语言要分行列开，不能乌央乌央并在一起"**）
- 黑底白字 / 白底黑字（采购单 R12 = `白底黑字`，必须核对）

---

### 🔵 数量提示（友情提醒，不阻断）

采购单 R9-R11 是数量分布表：

| 尺码 | 第一批欧洲单 | 第一批美国单 | 第二批欧洲单 | 第二批美国单 |
|---|---|---|---|---|
| 2-4Y | n1 | n2 | n3 | n4 |
| 5-9Y | n5 | n6 | n7 | n8 |
| 合计 | Σ | Σ | Σ | Σ |

洗标 PDF 上每个标签底部的"xxxx张"应当：
- **大签的张数 ≈ 该批次 × 该市场 × 该尺码的数量**
- 小签（第 5 页 / 第 6 页等）数量可以更大（一件衣服可能用 3 张小签）—— 是多倍关系，不强校验
- **核心规则**：大签每尺码每批次数量必须 ≥ 采购单数量（多印属于备品，少印才是问题）

> 💡 不要严格"等于"。印刷厂会按版面排版补量，多印 1-5% 属正常。**只在"打印张数 < 采购单数量"时才提示风险**，否则不报。

---

## 比对流程

### Step 1. 文件定位

```bash
ls -la <workspace>/workspace/ | grep -E "(洗标|TF[0-9])"
```

确认三个文件都在：
- `<款号>单 洗标采购单-YYYY.M.D.xls`
- `YY.M.D-<款号>洗标.pdf`
- `templates/洗标-模版.pdf`（在 SKILL 目录里，不在 workspace）

### Step 2. 解析采购单（xlrd 读 .xls）

```python
import xlrd
b = xlrd.open_workbook("<采购单>.xls")
s = b.sheet_by_index(0)

req = {
    "title":      s.cell_value(0,0),
    "color":      s.cell_value(2,1),
    "season":     s.cell_value(3,1),
    "dept":       s.cell_value(4,1),    # 强校验！
    "style":      s.cell_value(5,1),    # 强校验！
    "supplier":   s.cell_value(6,1),    # 强校验！
    "sizes": [   # R9-R10
        {"size": s.cell_value(9,0),  "sku": s.cell_value(9,1),  "kimball": s.cell_value(9,2),
         "color": s.cell_value(9,3), "qty_eu_b1": s.cell_value(9,4), "qty_us_b1": s.cell_value(9,5),
         "qty_eu_b2": s.cell_value(9,6), "qty_us_b2": s.cell_value(9,7)},
        {"size": s.cell_value(10,0), "sku": s.cell_value(10,1), "kimball": s.cell_value(10,2),
         "color": s.cell_value(10,3), "qty_eu_b1": s.cell_value(10,4), "qty_us_b1": s.cell_value(10,5),
         "qty_eu_b2": s.cell_value(10,6), "qty_us_b2": s.cell_value(10,7)},
    ],
    "material":   s.cell_value(12,0),    # 材质(无纺布) 白底黑字
    "comp_eu":    s.cell_value(14,1),    # 欧洲成分大段
    "comp_us":    s.cell_value(14,3),    # 美国成分大段
    "exclusive":  s.cell_value(22,3),    # EXCLUSIVE OF DECORATION 多语言
    "wash":       s.cell_value(32,1),    # 水洗多语言
    "first_wash": s.cell_value(34,1),    # WASH BEFORE FIRST USE
    "made_in":    s.cell_value(35,1),    # 制造国多语言
    "origin":     s.cell_value(36,1),    # TAIZHOU / CHINA
    "date_b1":    s.cell_value(37,1),    # 01-06-26
    "date_b2":    s.cell_value(38,1),    # 01-07-26
    "age_label":  s.cell_value(40,1),
}
```

### Step 3. 解析洗标 PDF（PyMuPDF 拿带坐标的 words）

```python
import fitz
doc = fitz.open("<洗标>.pdf")
for pi in range(doc.page_count):
    p = doc[pi]
    raw_text = p.get_text()                # 用于关键字搜索
    words = p.get_text("words")             # 用于版面分析
    # words 里的 (x, y, x2, y2, text, block, line, word_idx)
```

**判断每页是欧洲单还是美国单**：
- 顶部出现 `<款号>欧洲单` → 欧洲页
- 顶部出现 `<款号>美国单` → 美国页
- 美国页特征：成分块前缀是 `en-uk:` `en-us:` 而不是 `en:`，且必有 `EXCLUSIVE OF DECORATION` 段

### Step 4. 字段抽取（按页）

每页提取以下数据，逐项与采购单比对：

```python
def extract_label_fields(page_text):
    fields = {}
    # 部门号 - 供应商号 一行（形如 "15-24-15               80277"）
    m = re.search(r'(\d{2}-\d{2}-\d{2})\s+(\d{5})', page_text)
    if m: fields["dept"], fields["supplier"] = m.group(1), m.group(2)
    # Style + SKU 一行（"991183635    212144012"）
    m = re.search(r'(99\d{7})\s+(2\d{8})', page_text)
    if m: fields["style"], fields["sku"] = m.group(1), m.group(2)
    # Kimball 7 位数（"7678601"）
    m = re.search(r'\b(7\d{6})\b', page_text)
    if m: fields["kimball"] = m.group(1)
    # NIF / RN / Season
    fields["nif"] = "NIF - B83875427" if "B83875427" in page_text else None
    fields["rn"]  = "RN CODE:145478"  if "145478"   in page_text else None
    m = re.search(r'\b(SS|AW)(\d{2})\b', page_text)
    if m: fields["season"] = m.group(0)
    # 日期
    dates = re.findall(r'\b(\d{2}-\d{2}-\d{2})\b', page_text)
    fields["dates"] = list(set(dates))
    # 数量标注
    qtys = re.findall(r'(\d{2,5})张', page_text)
    fields["qtys"] = qtys
    return fields
```

### Step 5. 版面对照模板

只做**结构性**对比，不要求字段值一致（模板的款号是历史款）：

| 检查项 | 期望 |
|---|---|
| 顶部是否有 `材质(无纺布)` + `19.7x2.5cm` | ✓ |
| 标题是否含 `<款号>欧洲单` 或 `<款号>美国单` | ✓ |
| 大签底部是否有 `9.85x2.5cm` 标注 | ✓（说明同时还要做小签） |
| 是否每页都有 "第N批第M页 + xxxx张" 标注 | ✓ |
| 阿拉伯文段是否在 word 坐标的右侧（x > 页宽 × 0.55） | ✓ |
| 美国单页是否含 `EXCLUSIVE OF DECORATION` | ✓ |
| 欧洲单页是否**不**含 `EXCLUSIVE OF DECORATION` | ✓ |
| 美国单成分是否使用 `en-uk:` `en-us:` 双前缀 | ✓ |
| 欧洲单成分是否只用 `en:` 前缀 | ✓ |

### Step 6. 输出报告（屏幕展示 + 落盘归档）

按下面"输出格式"产出。**报告必须同时落到磁盘**（见 Step 7），不能只在聊天里输出就完事。

### Step 7. 报告落盘（强制要求！）

**这是流程最后一步，永远不能跳过。** 即使全部通过，也必须存一份归档报告。

#### 落盘规则

1. **目录**：`<workspace>/projects/Primark/<Style>/`（不存在则 `mkdir -p` 创建；`<Style>` = 9 位 ORIN 号）
2. **文件名**：`比对报告-洗标-<款型号如 26TF4AK006>-YYYYMMDD-HHMM.md`
   - 同一天多次校验不会覆盖（带时分）
   - 例：`比对报告-洗标-26TF4AK006-20260425-0840.md`
3. **内容**：与聊天里输出的报告**完全一致**（含商品身份表 / 成分表 / 版面表 / 数量表 / 总评 / 给工厂的回复建议）
4. **末尾必须附**：
   - 采购单 / 洗标 PDF 的绝对路径
   - 模板 PDF 路径（`templates/洗标-模版.pdf`）
   - 校验时间（含时区）
   - 由哪个 skill 生成（`primark-care-label-check`）
   - 自动结论行：`Verdict: PASS / FAIL`

#### 标准代码片段

```python
import os, datetime, pathlib

# Workspace 根目录解析（按优先级）：
#   1. 环境变量 OPENCLAW_WORKSPACE_DIR
#   2. 当前工作目录 cwd
ws = pathlib.Path(os.environ.get("OPENCLAW_WORKSPACE_DIR") or os.getcwd()).resolve()

style = req["style"]            # 从采购单 R5 读取
model  = "26TF4AK006"           # 从文件名读取
verdict = "PASS" if not issues else "FAIL"
now = datetime.datetime.now().astimezone()

out_dir = ws / "projects" / "Primark" / style
out_dir.mkdir(parents=True, exist_ok=True)
fname = f"比对报告-洗标-{model}-{now:%Y%m%d-%H%M}.md"
out_path = out_dir / fname

footer = f"""\n\n---\n\n## 📎 报告元信息（自动生成）\n\n- **采购单**: `{xls_path}`\n- **洗标 PDF**: `{pdf_path}`\n- **版面参照**: `skills/primark-care-label-check/templates/洗标-模版.pdf`\n- **校验时间**: {now:%Y-%m-%d %H:%M %Z}\n- **生成 skill**: primark-care-label-check\n- **Verdict**: {verdict}\n"""

out_path.write_text(report_md + footer, encoding="utf-8")
print(f"✅ 报告已归档: {out_path}")
```

#### 在聊天结尾必须告诉用户

报告生成后，**末尾要明确告诉用户报告路径**，并附一句"已存档，可直接拷贝/转发给工厂确认"。例如：

> 📁 **报告已存**: `projects/Primark/991184191/比对报告-洗标-26TF4AK006-20260425-0840.md`
> （可直接转发给工厂作为确认依据）

---

## 输出格式（必须严格遵守）

```markdown
# 📋 Primark 洗标 vs 采购单比对报告

**款号 / Style**: <从采购单读取>
**部门号**: <从采购单读取>
**供应商**: 80277
**季节**: AW26
**采购单文件**: <文件名>
**洗标 PDF**: <文件名>
**版面参照**: templates/洗标-模版.pdf

---

## ✅ 商品身份字段核对

| 字段 | 采购单 | 洗标 PDF | 状态 |
|---|---|---|---|
| Style | ... | ... | ✅ / 🔴 |
| 部门号 | ... | ... | ✅ / 🔴 |
| 供应商号 | ... | ... | ✅ / 🔴 |
| SKU (2-4Y) | ... | ... | ✅ / 🔴 |
| SKU (5-9Y) | ... | ... | ✅ / 🔴 |
| Kimball (2-4Y) | ... | ... | ✅ / 🔴 |
| Kimball (5-9Y) | ... | ... | ✅ / 🔴 |
| 季节 | AW26 | AW26 | ✅ |
| NIF | B83875427 | B83875427 | ✅ |
| RN CODE | 145478 | 145478 | ✅ |
| 产地 | TAIZHOU / CHINA | TAIZHOU / CHINA | ✅ |
| 第一批日期 | 01-06-26 | 01-06-26 | ✅ |
| 第二批日期 | 01-07-26 | 01-07-26 | ✅ |

## ✅ 成分字段核对（Body / Cover）

### 欧洲单
- Body: 61% POLYESTER / 21% VISCOSE / 17% POLYAMIDE / 1% ELASTANE — ✅ / 🔴
- Cover: 61% POLYESTER / 21% VISCOSE / 18% POLYAMIDE — ✅ / 🔴
- 14 种欧洲语言：✅ 全部出现 / 🔴 缺 xxx
- 阿拉伯文：✅ 出现 + 数字使用阿拉伯-印度数字 / 🔴 缺失或乱码

### 美国单
- 同上，且必须有 `en-uk:` `en-us:` 双前缀
- 必须含 `EXCLUSIVE OF DECORATION` 多语言段

## ✅ 水洗 / 制造国 / 年龄段
- 水洗温度：30°C ✅
- 五条禁令：NO BLEACH / NO TUMBLE DRY / NO IRON / NO DRY CLEAN ✅
- WASH BEFORE FIRST USE 多语言 ✅
- Made in China 多语言 ✅
- 2-4Y / 5-9Y 年龄段多语言 + 阿拉伯文数字 ✅

## ⚠️/✅ 版面结构核对（vs 模板）

| 检查项 | 状态 | 说明 |
|---|---|---|
| 顶部材质 + 标签尺寸 | ✅ | 19.7x2.5cm |
| 大签 + 小签同时出现 | ✅ | 底部 9.85x2.5cm |
| 阿拉伯文 RTL 靠右 | ✅ / ⚠️ | |
| 美国单含 EXCLUSIVE OF DECORATION | ✅ / 🔴 | |
| 欧洲单不含 EXCLUSIVE | ✅ / 🔴 | |

## ⚠️ 数量提示（仅供参考，不阻断）

| 批次 / 市场 / 尺码 | 采购单数量 | 洗标 PDF 标注 | 差额 | 状态 |
|---|---:|---:|---:|---|
| 第一批 欧洲 2-4Y | 12,503 | 12,503 | 0 | ✅ |
| 第一批 欧洲 5-9Y | 12,147 | 12,147 | 0 | ✅ |
| 第一批 美国 2-4Y | 950 | 950 | 0 | ✅ |
| ... | | | | |

> 💡 数量仅作友情提醒。多印为正常备品，少印才需追问。

---

## 💬 总评

如果全部通过：
> **强校验项全部通过，可以批量印刷。** 🟢

如果有错：
> 🔴 **以下字段不一致，必须修正后才能印刷：**
> - <逐项列出>

## 📝 给工厂的回复建议

[只在有强校验项错误时才生成中英对照]
```

---

## 关键规则

1. **采购单 .xls 是字段权威**，模板 PDF 只参考结构；模板上的 Style/SKU/Dept 不可作为校验基准。
2. **数量永远不要写成"❌严重问题"**。只用 ⚠️ / 💡，少印才追问。
3. **欧洲单 ≠ 美国单**：
   - 欧洲单：成分用 `en:`；不含 EXCLUSIVE OF DECORATION
   - 美国单：成分用 `en-uk:` + `en-us:`；必含 EXCLUSIVE OF DECORATION（FTC 强制）
4. **阿拉伯文是否 RTL** 用 word 坐标判断（x > 页宽 × 0.55 算靠右）。
5. **日期是 DD-MM-YY 欧式**，不是 MM-DD-YY 美式。`01-06-26` = 2026 年 6 月 1 日。
6. **批次日期分配**：第一批用 `date_b1`，第二批用 `date_b2`。如果某批次的标签印错了日期 → 强校验错误。
7. **如果采购单和洗标 PDF 一致、但和模板差距大** → 不要立刻报错，温和提示"版面与模板差异较大，是否本款有特殊要求"。
8. **`NIF` `RN CODE` 是固定字符串**，工厂任何变动都是错误。

---

## 常见错误样本（看到要敏感）

| 错误形式 | 原因 | 处理 |
|---|---|---|
| 部门号印成模板上的 `15-24-15`（实际应为采购单上的） | 套用模板没改 | 🔴 强校验阻断 |
| 第二批的洗标日期还印成 `01-06-26` | 复制粘贴错误 | 🔴 强校验阻断 |
| 美国单缺 `EXCLUSIVE OF DECORATION` | 制版漏掉 | 🔴 强校验阻断 |
| 欧洲单成分用了 `en-uk: en-us:` | 美国单模板套到欧洲单 | 🔴 强校验阻断 |
| 阿拉伯文左对齐 | 排版未做 RTL | ⚠️ 提示修改 |
| 各国语言挤成一段不分行 | 排版偷懒 | ⚠️ 引用采购单 R14 备注"每个国家的语言要分行列开" |
| 阿拉伯数字写成拉丁数字（`2-4` 而非 `٢-٤`） | 字体不全 | 🔴 强校验阻断 |

---

## 工作目录约定

- 待比对文件默认在 `<workspace>/workspace/` 下
- 模板 PDF 在 SKILL 自己的 `templates/洗标-模版.pdf`
- 中间产物（PNG 渲染）放 `<workspace>/workspace/_check/`
- **比对报告必须落盘** → `<workspace>/projects/Primark/<Style>/比对报告-洗标-<款型号>-YYYYMMDD-HHMM.md`（见 Step 7 强制规则）

---

## 执行参考代码骨架

```python
import fitz, xlrd, re, sys

def parse_purchase_xls(path):
    s = xlrd.open_workbook(path).sheet_by_index(0)
    return {
        "season":   s.cell_value(3,1),
        "dept":     s.cell_value(4,1),
        "style":    str(int(s.cell_value(5,1))) if isinstance(s.cell_value(5,1), float) else s.cell_value(5,1),
        "supplier": str(int(s.cell_value(6,1))) if isinstance(s.cell_value(6,1), float) else s.cell_value(6,1),
        "sizes": [
            {"size": s.cell_value(r,0),
             "sku": str(int(s.cell_value(r,1))),
             "kimball": str(int(s.cell_value(r,2))),
             "qty_eu_b1": int(s.cell_value(r,4)) if s.cell_value(r,4)!='' else 0,
             "qty_us_b1": int(s.cell_value(r,5)) if s.cell_value(r,5)!='' else 0,
             "qty_eu_b2": int(s.cell_value(r,6)) if s.cell_value(r,6)!='' else 0,
             "qty_us_b2": int(s.cell_value(r,7)) if s.cell_value(r,7)!='' else 0}
            for r in (9, 10)
        ],
        "comp_eu":    s.cell_value(14,1),
        "comp_us":    s.cell_value(14,3),
        "wash":       s.cell_value(32,1),
        "made_in":    s.cell_value(35,1),
        "origin":     s.cell_value(36,1),
        "date_b1":    s.cell_value(37,1),
        "date_b2":    s.cell_value(38,1),
    }

def parse_label_pdf(path):
    doc = fitz.open(path)
    pages = []
    for pi in range(doc.page_count):
        p = doc[pi]
        text = p.get_text()
        # 判断单页类型
        is_eu = "欧洲单" in text
        is_us = "美国单" in text
        # 字段
        depts    = re.findall(r'(\d{2}-\d{2}-\d{2})\s+\d{5}', text)
        styles   = re.findall(r'(99\d{7})', text)
        skus     = re.findall(r'\b(2121\d{5})\b', text)
        kimballs = re.findall(r'\b(7\d{6})\b', text)
        dates    = re.findall(r'\b(\d{2}-\d{2}-\d{2})\b', text)
        qtys     = [(int(m.group(1)), m.start()) for m in re.finditer(r'(\d{2,5})张', text)]
        nif_ok   = "B83875427" in text
        rn_ok    = "145478" in text
        season   = re.search(r'\b((?:SS|AW)\d{2})\b', text)
        excl_ok  = "EXCLUSIVE OF DECORATION" in text
        pages.append({
            "page": pi+1, "is_eu": is_eu, "is_us": is_us,
            "depts": list(set(depts)), "styles": list(set(styles)),
            "skus": list(set(skus)), "kimballs": list(set(kimballs)),
            "dates": list(set(dates)), "qtys": qtys,
            "nif_ok": nif_ok, "rn_ok": rn_ok,
            "season": season.group(1) if season else None,
            "exclusive_ok": excl_ok,
        })
    return pages
```

按以上骨架解析，对照表格化输出报告。
