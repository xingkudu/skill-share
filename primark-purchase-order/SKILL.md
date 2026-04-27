---
name: primark-purchase-order
description: 根据 Primark 客户的 Ticket Request PDF 和 Purchase Order (PO) PDF，生成给国内印刷工厂的“价格小圆贴 & 条码贴纸采购单”Excel。Ticket 提供款号/SKU/条码/颜色/尺码/价格/币种等订单细节，PO 提供权威的商品数量。当用户要求做 Primark 条码贴/小圆贴/价格贴/价格标签/Hangtag 采购单、给印刷厂下单、整理 Primark 标签订单时使用。也适用于反推已存在的采购单数字来源、核对 Ticket 与 PO 的对应关系。**必须参照 reference/采购单-模版.xls 生成，使用 xlwt 库输出 .xls (不是 .xlsx)。**
---

# Primark 条码贴 & 价格小圆贴 采购单生成 Skill

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

## 核心规则(牢记!)

> 🎯 **Ticket 数量 = PO 数量 × 1.02(含 2% 损耗)**
>
> - **PO 数量** = 客户实际下单数 → **权威基准**
> - **Ticket 数量** = PO × 1.02 后向上取整 → 含损耗,不准
> - **采购单给工厂的数量必须以 PO 为准**(即 Ticket ÷ 1.02 ≈ PO)
>
> 实测验证(PO 1254344):每个 region Ticket / PO 比值都是 **1.0188 ~ 1.0200**。

> 📌 **如果用户只给 Ticket 没给 PO**:可以临时按 `round(Ticket / 1.02)` 反推,但必须在采购单上标注"PO 数量为反推估算",并提示用户尽快补 PO 文件以确认。

---

## 输入文件清单

| 文件 | 是否必须 | 用途 |
|---|---|---|
| **Ticket_Request_<PO号>_<n>.PDF** | ✅ 必须 | 取款号/SKU/条码/颜色/尺码/价格/币种/Tag Type/部门号 |
| **<PO 编号>.PDF**(文件名形如 `Global-...-<PO>-<n>.PDF` 或 `SUPPLIER COPY`) | ✅ 必须 | 取每个 destination 的实际订单数(权威) |
| 历史采购单参考样板 `.xls` | ⬜ 可选 | 其他实际订单(仅供对比,不要拿这个当模板) |

---

## 🚀 首选方案：直接调用脚本（避免模型差异）

> ⚠️ **不同模型（Opus / GPT / Qwen / 其他）中文 / 响应习惯不同，为保证输出一致，凡是能调脚本就不要手写代码。**

```bash
python3 <SKILL_DIR>/scripts/generate.py <Ticket.PDF> <PO.PDF> -o <输出目录>
```

**脚本会自动保证**：
- 表头 12 列固定顺序（国家/颜色/英文颜色/序列号/部门号/SKU/STYLE/条码号/Supplier ID/尺寸/价格/数量）
- 区域中文名统一（ROI=爱尔兰、UK=英国单、GCC=中东单 ···）
- 价格带币种符号（£ / € / $ / AED）
- 输出 .xls（xlwt，不是 .xlsx）
- 文件名格式统一
- 输出后自动调用 `xlrd` 反读校验（表头/标题/SKU/Ticket·PO比例）不过会报错

**如果脚本运行报错**，再读 SKILL.md 后面的步骤指导手工实现，但输出须与脚本一致。

---

## 📌 采购单模版(只供人读参考)

> ⚠️ **手工实现时必须参照此模版,保证表头、列顺序、说明文字、备注与历史采购单一致。**

**模版文件**:`reference/采购单-模版.xls`(原型:26RS4AK007 价格小圆贴&条码贴 采购单-2026.4.23.xls,已被用户认可为标准格式)

> 🔒 **模版已脱敏**:所有款号/SKU/EAN-13/Kimball/供应商号/部门号/颜色/价格/数量等真实字段均替换为 `<占位符>`(例如 `<Style ORIN>`、`<SKU-1>`、`<EAN13-1>`、`<GCC 价组:KWD/AED/QAR/BHD>`),数量一律为 0。样品参考图(条码贴/价格小圆贴/BABY小圆贴)不再嵌入模版内,以独立 PNG 形式保留在同目录(`reference/*.png`),由 `generate.py` 按需插入新生成的采购单。含真实数据的原版备份为 `采购单-模版.xls.bak-realdata-20260427`(私有,勿外发)。

### 模版结构速查

| 区域 | 行号 | 内容 |
|---|---|---|
| 标题 | R0 | `<款号> 价格小圆贴&条码贴纸采购单` + 右上角日期 |
| 问候 | R1 | `你好!请做"PRIMARK"价格贴纸,贴纸款式同图稿,请注意品质和颜色要准确。` |
| 说明 | R2 | `请先做电脑稿确认` |
| 区块 1 | R3-R4 | `1.价格贴纸:` + 说明 |
| 表头 | R5 | 国家 \| 颜色 \| 英文颜色 \| 序列号 \| 部门号 \| SKU \| STYLE \| 条码号 \| Supplier ID \| 尺寸 \| 价格 \| 数量 |
| 明细 | R6开始 | 按 region 分组 SKU 行 |
| 合计 | 明细末行 | K=`合计` L=总数量 |
| 区块 2 | +N | `2.价格小圆贴(白色不干胶底,黑色字体):请安排价格小圆贴,尺寸 1.5cm*1.5cm,同样品` + 价格汇总表 |
| 区块 3 | +N | `3.BABY小圆贴(白底黑字:尺寸 1.5cm*1.5cm,同样品)` + BABY 总数 |
| 备注 | 末尾 | 裁切要求 / 发票说明 / 包装提醒 |

### 模版使用准则

1. **不要重新设计表头顺序** - 12 列始终是:国家 / 颜色 / 英文颜色 / 序列号 / 部门号 / SKU / STYLE / 条码号 / Supplier ID / 尺寸 / 价格 / 数量
2. **问候语、说明、备注文字原样复制** - 不要自己改措辞,工厂习惯这种语气
3. **区域名称中文化** - ROI=爱尔兰、UK=英国单、GCC=中东单、ROO=欧洲单、NE1/NE2=德国/捷克、IB=西班牙、US1/US2=美国单
4. **中东/德捷贴纸要备注尺寸** - R0 列需接换行后加 `贴纸尺寸 3*4cm`
5. **价格带币种符号** - £ / € / $ / AED 不能省;多币种区域(中东、德捷)要列出所有币种的价格【参考模版 R7/R16 的多行价格】
6. **采用 .xls (BIFF) 格式** - 使用 Python `xlwt` 库,不要用 openpyxl(那个只能写 .xlsx,工厂电脑可能打不开)
7. **文件名格式**:`<款号或型号> 价格小圆贴&条码贴 采购单-YYYY.M.D.xls`

### 生成前检查清单

- [ ] 打开 `reference/采购单-模版.xls` 看一眼,确认表头和列顺序
- [ ] 生成后用 `xlrd` 读取生成的文件验证前 25 行结构
- [ ] 检查价格是否带币种符号
- [ ] 检查所有 region 都有中文名称
- [ ] 检查合计行、价格汇总、BABY 区块是否齐全

---

## PO 文件结构(要点)

### Header(第 1 页)
- `Purchase Order: <号>` - PO 号
- Supplier / Factory 信息
- `Total Units (Inc. TBC): <数>` - 总件数
- `Currency: USD`、`Incoterms: Free on Board`、`Total Supplier Cost Value: $...`

### DELIVERY/DESTINATION SUMMARY(第 1 页)
按交货批次分块,每块一个 `HANDOVER DATE` + `DELIVERY 编号`,下面列:

| DEST | DEST NUMBER | TBC UNITS | TOTAL UNITS (INCL TBC) | PACKS |
|---|---|---|---|---|
| GCC | U13684105 | 0 | 425 | 17 |
| IB  | S13684102 | 0 | 2,550 | 102 |
| ... |

> ✅ **取数就用这个表里的 `TOTAL UNITS (INCL TBC)`**,按 region 合并所有 Delivery 批次。

### DELIVERIES(第 4-5 页)
更详细的 destination → pack 拆分,含 Supplier Cost。如果只做条码贴采购单可以不看,要确认成本时再用。

### ITEMS(最后一页)
列出 Style ORIN / SKU ORIN / EAN-13 / Colour / Size / Kimball-7 / Compliance Id 等。**EAN-13 与 Ticket 里的必须一致**。

---

## Ticket 文件结构(参见 SKILL: primark-ticket-check)

按 region 分表,每个 region 表里每个尺码一行:SKU / ORIN / Barcode / Kimball / Colour / **Unit QTY of Tickets(含 2% 损耗)** / Size 系列 / Price 系列。

---

## Region → 价格款 合并规则(来自 primark-ticket-check)

> Primark 条码贴是**按价格款式合并印刷**的,多个 region 共用同一款贴纸:

| 价格款 | 合并的 Region | 中文区域名 | 说明 |
|---|---|---|---|
| **£4 / £5** | UK | 英国单 | GBP |
| **€6 / €7** | ROI + ROO + IB | 爱尔兰/西班牙/荷兰 | EUR 单价 |
| **€7 + 26 PLN + 155 Kč + 30 LEI** | NE1-MGB + NE2-BOR | 德国/捷克 | 4 币种 |
| **$9 / $10** | US1-PA + US2-FL | 美国单 | USD |
| **AED + BHD + KWD + QAR** | GCC | 中东单 | 4 币种 |

> ⚠️ 实际合并依据是"价格组合是否完全一致",不是写死的映射。要逐 PO 看 Ticket 里 region 表的 Price 列。

---

## 采购单标准结构

`<款号> 价格小圆贴&条码贴 采购单-YYYY.M.D.xls`

### Sheet1(核心)

#### 标题区
```
R0: <款号> 价格小圆贴&条码贴纸采购单
R1: (右上角) YYYY.M.D
R2: 你好!请做"PRIMARK"价格贴纸, 贴纸款式同图稿,请注意品质和颜色要准确。
R3: 请先做电脑稿确认
```

#### 1. 价格贴纸(条码贴)表
```
R4: 1.价格贴纸:
R5: 注意,不同国家的价格贴纸不同, 具体国家和条码以及价格如下表
R6: 表头 → 国家 | 颜色 | 英文颜色 | 序列号(Kimball) | 部门号 | SKU | STYLE | 条码号 | Supplier ID | 尺寸 | 价格 | 数量
```

每个"国家分组"占 3 行(每个尺码一行),第一行写国家名+贴纸尺寸,后两行国家列空白:
- **数量列 = 该分组每个 region 的 PO 数 ÷ 1 (直接合并相加,不做损耗加成)**
- **价格列 = 多币种用换行串起来**(如 `€7.00\n26.00 PLN\n155.00 Kč\n30.00LEI`),合并单元格只写第一行

最后一行:`合计 | <所有数量之和>`

#### 2. 价格小圆贴
```
R31: 2.价格小圆贴(白色不干胶底,黑色字体):请安排价格小圆贴,尺寸1.5cm*1.5cm,同样品
R32: 内容 | 数量
R33: <每种价格内容> | <对应数量(=该价格款的所有尺码合计)>
...
合计 | <总数>
```

> 📌 价格小圆贴 = 把上面条码贴的"价格款"汇总,每款一行,数字 = 该款所有尺码之和。

#### 3. BABY 小圆贴(仅婴幼儿款)
```
R40: 3.BABY小圆贴(白底黑字:尺寸1.5cm*1.5cm,同样品)
R41: 内容 | 数量
R42: BABY | <总数>(与采购单总合计相同)
```

> 仅当 Ticket 里 Subsection 含 `Baby` / `0-6M` / `6-12M` / `12-24M` 等婴儿尺码时才做。

#### 注意事项区(固定模板)
```
R47: 注:大货里小圆贴的裁切一定要适当,要便于工厂拿下来贴在吊钩上又不会损坏小圆贴,送大货时请放些余量
R48: 发票:由我司付货款!请开增值税发票!
R49: 注意包装时一定要颜色分开包装, 切记.
R50: 若赶不上要求交期,请务必通知工厂或者我司,谢谢配合!
R51: 并且要在外箱包装上注明是: <款号>单 价格小圆贴&条码贴纸
R52: 寄送地址:
```

---

## 完整工作流

### Step 1. 读 PO,按 region 汇总数量
```python
import pypdf
po = pypdf.PdfReader("<PO>.PDF")
# 从第 1 页 DELIVERY/DESTINATION SUMMARY 提取每行 (Region, DEST_NUM, TOTAL_UNITS)
# 多个 HANDOVER 批次同 region 累加
po_qty = {'UK': 13050, 'ROI': 2400, 'ROO': 5300, ...}
```

### Step 2. 读 Ticket,按 region 提取商品信息
```python
ticket = pypdf.PdfReader("Ticket_Request_<PO>_0.PDF")
# 提取 Header: Style ORIN / Kimball / Supplier ID / Department-Section-Subsection / Tag Type
# 提取每个 region 表: SKU/ORIN/Barcode/Kimball-7/Colour/Size/Price
```

### Step 3. 按"价格款"合并 region

依据 Ticket 里每个 region 的 Price 列,把价格组合一致的 region 归为同一个"价格款"。同时检查 Region 与价格款的对应是否符合常见映射(不符要警告)。

### Step 4. 推算每个价格款 × 每个尺码的数量
- 数量 = `sum(po_qty[r] for r in 该价格款下的所有 region)` 按尺码分别相加
- ⚠️ 如果 PO 没给到 SKU 级数量(PO 通常是 region 总数 + Pack 拆分),要参考 Ticket 里同 region 的 SKU 比例分配 ÷ 1.02 反推
  - 例如:UK 总 PO = 13,050,Ticket UK 0-6M=5124、6-12M=6085、12-24M=4804(合计 16013,含损耗)
  - 比例分配:0-6M = 13050 × 5124/16013 ≈ 4176 - 但**实操更简单的做法是直接 round(ticket_size / 1.02)**,与按比例几乎一致

### Step 5. 生成 Excel(用 xlwt 写 .xls 或 openpyxl 写 .xlsx)

> 客户/工厂习惯用 `.xls`,建议保留 .xls 格式。`xlwt` 库可写老格式。

```python
import xlwt
wb = xlwt.Workbook()
ws = wb.add_sheet('Sheet1')
# 设置合并、字体、边框、自动换行
# 标题、表头、数据、汇总、注意事项 按上面"标准结构"写入
# ⚠️ 不要直接 wb.save(<裸文件名>)!路径必须遵守 Step 7 的归档规则。
```

### Step 6. 自检(关键!)

输出前必须做以下校验,列在采购单底下或单独报告中:

1. ✅ **总数闭环**:条码贴合计 == 小圆贴价格合计 == BABY 小圆贴数量
2. ✅ **每个价格款** 在条码贴表里的 sum(数量) == 小圆贴表里该价格款的数量
3. ✅ **EAN13 校验位** 全部正确(用 mod10 算法)
4. ✅ **每个 SKU 在所有价格款里出现的次数** = 价格款个数
5. ⚠️ **数量 ≈ Ticket÷1.02**:如果差异 >5%,警告"是否 Ticket 损耗率与往常不同?"

### Step 7. 文件落盘(强制要求!)

**这是流程最后一步,永远不能跳过。** 生成的 .xls 采购单**必须**落到正式项目目录,不可仅放 `workspace/` 根下;同时在聊天里明确告诉用户路径。

#### 落盘规则

1. **目录**:`<workspace>/projects/Primark/<Style>/`(不存在则 `mkdir -p` 创建;`<Style>` = 9 位 ORIN 号,从 Ticket Request 读取)
2. **文件名**:`<款号> 价格小圆贴&条码贴 采购单-YYYY.M.D.xls`
   - 例:`26RS4AK001 价格小圆贴&条码贴 采购单-2026.4.25.xls`
   - **保持带中文 + `&` 符号**(工厂习惯的命名风格,不要改成 ASCII)
   - 同一天多版追加`-v2`/`-v3` 后缀,不要覆盖
3. **同时输出一份定接报告**发在同一目录:`采购单生成报告-<款号>-YYYYMMDD-HHMM.md`,内容 = Step 6 的自检结果 + 数量明细表 + 采购单路径 + Verdict

#### 标准代码片段

```python
import os, datetime, pathlib

# Workspace 根目录解析(按优先级):
#   1. 环境变量 OPENCLAW_WORKSPACE_DIR(OpenClaw 注入的当前 agent 工作区)
#   2. 当前工作目录 cwd(agent 默认就在自己 workspace 下)
ws_root = pathlib.Path(os.environ.get("OPENCLAW_WORKSPACE_DIR") or os.getcwd()).resolve()

style  = "991185354"           # 从 Ticket Request 读取
model  = "26RS4AK001"          # 款型号
now    = datetime.datetime.now().astimezone()
date_s = f"{now.year}.{now.month}.{now.day}"   # 2026.4.25 (工厂习惯的点分隔)

out_dir = ws_root / "projects" / "Primark" / style
out_dir.mkdir(parents=True, exist_ok=True)

# 主产物:.xls 采购单
xls_name = f"{model} 价格小圆贴&条码贴 采购单-{date_s}.xls"
xls_path = out_dir / xls_name
# 同名冲突不覆盖,追加后缀
seq = 2
while xls_path.exists():
    xls_path = out_dir / f"{model} 价格小圆贴&条码贴 采购单-{date_s}-v{seq}.xls"
    seq += 1
wb.save(str(xls_path))

# 伴生产物:生成报告 .md
report_path = out_dir / f"采购单生成报告-{model}-{now:%Y%m%d-%H%M}.md"
report_md   = build_self_check_report(...)  # Step 6 的自检表转 md
footer = f"""\n\n---\n\n## 📎 报告元信息(自动生成)\n\n- **输入 Ticket Request**: `{ticket_path}`\n- **输入 PO**: `{po_path}`\n- **产出采购单**: `{xls_path}`\n- **生成时间**: {now:%Y-%m-%d %H:%M %Z}\n- **生成 skill**: primark-purchase-order\n- **Verdict**: {verdict}   (PASS = 自检全过 / WARN = 有数量提示 / FAIL = 总数不闭环)\n"""
report_path.write_text(report_md + footer, encoding="utf-8")

print(f"✅ 采购单已生成: {xls_path}")
print(f"✅ 报告已归档: {report_path}")
```

#### 在聊天结尾必须告诉用户

生成后,**末尾要明确告诉用户两个路径**,并附一句"采购单可直接发给印刷厂"。例如:

> 📁 **采购单已生成**:
> - `projects/Primark/991185354/26RS4AK001 价格小圆贴&条码贴 采购单-2026.4.25.xls` ← 发给印刷厂
> - `projects/Primark/991185354/采购单生成报告-26RS4AK001-20260425-0900.md` ← 自检报告存档

---

## 嵌入参考样图

采购单需要在每个表后附上贴纸样式参考图(工厂看图才知道该怎么排版)。**图片已备在本 skill 的 `reference/` 目录下,直接用**,不要再去历史采购单里抽:

| 图片文件 | 插入位置 | 是否必需 |
|---|---|---|
| `reference/条码贴.png` | 第 1 节(价格贴纸/条码贴)合计行之后 | ✅ 总是插 |
| `reference/价格小圆贴1.png` | 第 2 节(价格小圆贴)合计行之后 | ✅ 总是插 |
| `reference/价格小圆贴2.png` | 接在价格小圆贴1后面 | ✅ 总是插 |
| `reference/baby小圆贴.png` | 第 3 节(BABY 小圆贴)后 | ⚠️ **仅当该单包含婴儿款时**(0-6M / 6-12M / 12-24M) |

是否插 baby 图由 `HAS_BABY` 变量控制:看 Ticket 里的 Subsection 名称或尺码是否含月龄表示(0-6M/6-12M/12-24M)。纯童装款(5-9Y/10+Y 等)不插。

### 🚨 xlwt 插图三大坑(必看!)

xlwt 只能插 **24bit BMP**,且对 BMP 格式极挑剔:

1. ❌ **sips 直接转出的 BMP 不能用** - sips 写出的是"top-down"方向(height 字段为负数),xlwt 会报 `largest image height supported is 65k`。**这个报错信息是幽魂报错,与尺寸无关。**
2. ✅ **用 PIL 写 BMP**:`Image.open(...).convert('RGB').save('x.bmp')` 默认 bottom-up + 24bit,完美适配 xlwt。
3. ⚠️ **PIL 直接读某些 PNG 会报"unrecognized data stream"** - 解法:用 sips 先转为 JPEG 作为中转格式,再用 PIL 读 JPEG 保存为 BMP。

```python
# 标准转换链路(PNG → JPEG 中转 → BMP)
import subprocess
from PIL import Image
subprocess.run(['sips','-Z','300','-s','format','jpeg', src_png, '--out', 'mid.jpg'],
              check=True, capture_output=True)
Image.open('mid.jpg').convert('RGB').save('out.bmp')  # 产出可被 xlwt 读取
```

逻辑封装:
```python
def prep_bmp(name, ref_dir, bmp_dir):
    src_png = f'{ref_dir}/{name}.png'
    mid_jpg = f'{bmp_dir}/ref_{name}.jpg'
    out_bmp = f'{bmp_dir}/ref_{name}.bmp'
    if not os.path.exists(out_bmp):
        subprocess.run(['sips','-Z','300','-s','format','jpeg', src_png,'--out',mid_jpg],
                      check=True, capture_output=True)
        Image.open(mid_jpg).convert('RGB').save(out_bmp)
    return out_bmp
```

4. **插图代码**:`ws.insert_bitmap('out.bmp', row, col)`,插入位置为单元格左上角,不受合并单元格影响。每张图留 8~10 行高度。

### 如果需要更高质量的图 / 超多图

考虑输出为 **.xlsx**(用 openpyxl + `Image()` 插 PNG),质量远优于 xlwt BMP,但要先确认工厂能打开 .xlsx(现代 Office 都可以,老 WPS 有时不行)。

## 常见坑

### 1. 价格符号及币种(双重险坑!)

#### a) 货币符号不能丢
- ⚠ **重要:采购单上价格必须带货币符号**,不能写裸数字。
- Ticket 里 Price 列是裸数字(币种在列头,如 `Price EUR` 下面写 `7`),但采购单上要写成 `€7.00`,而不是 `7`。
- 同理:`$10.00` 不是 `10`;`$4.00` 不是 `4`。

#### b) 货币符号表
- **$ / £** = 英镑(UK),不是 ¥
- **€** = 欧元
- **$** = 美元
- **Kč** = 捷克克朗(注意是 K + 小写带钩 č)
- **LEI / RON** = 罗马尼亚列伊
- **PLN** = 波兰兹罗提
- **AED/BHD/KWD/QAR** = 中东四币

#### c) 🚨 GCC 四币种列顺必须仔细看清楚
Ticket 里 GCC 表头是固定顺序:**Price AED │ Price BHD │ Price KWD │ Price QAR**

数据行如 `34 3.500 2.800 34` 要严格按顺序对号入座:
- AED 34 · BHD 3.500 · **KWD 2.800** · QAR 34

不要护别的单的价格(如 26RS4AK007 是 KWD 2.400),**每单都要当场从 Ticket 重新读**。

#### d) 不同价位供参考(不要死记)
| 价位 | UK | EUR | USD | NE EUR | NE PLN | NE Kc | NE LEI | KWD | AED/QAR | BHD |
|---|---|---|---|---|---|---|---|---|---|---|
| 低(妈2元毛帽女童)| £4 | €6 | $9 | €7 | 26 | 155 | 30 | 2.400 | 29 | 3.000 |
| 高(妈2元 IP联名男童)| £5 | €7 | $10 | €8 | 30 | 180 | 34 | 2.800 | 34 | 3.500 |

### 2. 价格小数点格式
- 中欧/捷克习惯用**逗号**:`155,00 Kč`、`26,00 PLN`、`30,00 LEI`
- 英美习惯用**点**:`£4.00`、`$9.00`
- BHD/KWD 通常 3 位小数:`3.000` `2.400`

### 3. 数量取整方向
反推 PO 数:`round(ticket / 1.02)`(四舍五入),**不要用 ceil 或 floor**,否则会和真 PO 差 ±1。

### 3.5 尺码顺序(小→大)与尺码简写

每个价格款内部的 SKU 行要按尺码**从小到大**排列。

**尺码名称要用简写形式**,不要照搬 Ticket 里的全名:

| Ticket 里的全名 | 采购单上用的简写 |
|---|---|
| `0-6Mths` | `0-6M` |
| `6-12Mths` | `6-12M` |
| `12-24Mths` | `12-24M` |
| `2-4 YEARS` / `2-4Y Hat` | `2-4Y` |
| `5-9YHat` | `5-9Y` |
| `7-10Y HAT` | `7-10Y` |
| `10+YRS` | `10+Y` |

原则:去掉 `Hat` / `YRS` / `Mths` 等后缀,只留"区间 + Y/M"。

Ticket 里的 region 表顺序不一定是小→大(常常中文顺序 或 随机),读取后要手动排序。

### 4. Tag Type 决定贴纸物理参数
- `Small Self-Adhesive Label` → 通常 3×4cm
- `Large Self-Adhesive` → 4×6cm
- `Hangtag` → 纸卡,不是不干胶
- 中东款(GCC)和中东欧款(NE1/NE2)因为多币种文字多,**贴纸尺寸通常更大**(如 3×4cm vs 普通 1×3cm),要在国家列括注尺寸:`中东单\n贴纸尺寸3*4cm`

### 5. 颜色英文 ≠ 中文照搬
- `Pink` → 粉色
- `Navy` → 藏青/深蓝(不是"海军色")
- `Cream` → 米色(不是"奶油色")
- `Charcoal` → 炭灰
- `Heather Grey` → 麻灰
- 不确定时**保留英文 + 写"色卡为准"**

### 6. 日期格式
采购单上的日期用中文习惯 `YYYY.M.D`(如 `2026.4.23`),不要用 `2026-04-23`。

---

## 使用示例(口径)

> "做 26RS4AK007 单的条码贴采购单"
> → 找 `Ticket_Request_*.PDF` + `*<PO号>*.PDF` → 按本 skill 流程出 `.xls`

> "我没有 PO 文件,只有 Ticket"
> → 按 `round(Ticket÷1.02)` 反推数量,并在邮件里**显式提醒用户补 PO 确认**

> "核对一下我已经做好的采购单对不对"
> → 用 `primark-ticket-check` skill 比对工厂打回的条码贴 PDF;用本 skill 反推每个数字来源

---

## 关联 Skill

- **primark-ticket-check** - 收到工厂打回的条码贴 PDF 后,反向核对是否与 Ticket/PO 一致
- **xlsx** - 通用 Excel 处理(如客户改要 .xlsx 格式时使用)
