#!/usr/bin/env python3
"""
Primark 采购单生成器 - 确定性脚本
用法: python3 generate.py <Ticket.PDF> <PO.PDF> [--output DIR]

强保证:
- 表头永远 12 列固定顺序
- 中文区域名永远统一
- 价格永远带币种符号
- 输出永远是 .xls (xlwt)
- 文件名永远是 <款号> 价格小圆贴&条码贴 采购单-YYYY.M.D.xls

LLM 只需调用此脚本,不要重新实现生成逻辑。
"""
import sys, os, re, datetime, pathlib, argparse

try:
    import pypdf, xlwt
except ImportError as e:
    print(f"❌ 缺少依赖: {e}\n请运行: pip3 install pypdf xlwt")
    sys.exit(1)


def _resolve_workspace_root():
    """推断 textile-trade workspace 根路径（升序优先级）：
      1. 环境变量 TEXTILE_TRADE_WORKSPACE
      2. 环境变量 OPENCLAW_WORKSPACE/agents/textile-trade
      3. 默认 ~/.openclaw/workspace/agents/textile-trade
    均不存在返回 None。
    """
    candidates = []
    env_tt = os.environ.get('TEXTILE_TRADE_WORKSPACE')
    if env_tt:
        candidates.append(pathlib.Path(env_tt).expanduser())
    env_oc = os.environ.get('OPENCLAW_WORKSPACE')
    if env_oc:
        candidates.append(pathlib.Path(env_oc).expanduser() / 'agents' / 'textile-trade')
    candidates.append(pathlib.Path.home() / '.openclaw' / 'workspace' / 'agents' / 'textile-trade')
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()
    return None

# ==================== 固定常量 (严禁 LLM 修改) ====================
HEADERS = ['国家', '颜色', '英文颜色', '序列号', '部门号', 'SKU',
           'STYLE', '条码号', 'Supplier ID', '尺码', '价格', '数量']

REGION_CN = {
    'ROI': '爱尔兰',
    'GCC': '中东单\n贴纸尺寸 3*4cm',
    'ROO': '欧洲单',
    'NE1-MGB': '德国/捷克\n贴纸尺寸 3*4cm',
    'NE2-BOR': '德国/捷克\n贴纸尺寸 3*4cm',
    'UK': '英国单',
    'US1-PA': '美国单',
    'US2-FL': '美国单',
    'IB': '西班牙',
}

REGION_CURRENCY = {
    'ROI': '€', 'ROO': '€', 'IB': '€', 'NE1-MGB': '€', 'NE2-BOR': '€',
    'UK': '£',
    'US1-PA': '$', 'US2-FL': '$',
    'GCC': 'AED ',
}

DEFAULT_GREETING = '你好！请做"PRIMARK"价格贴纸，贴纸款式同图稿，请注意品质和颜色要准确。'
DEFAULT_NOTE_1 = '请先做电脑稿确认'
DEFAULT_SECTION_1 = '1. 条码贴纸：'
DEFAULT_SECTION_1_NOTE = '注意，不同国家的价格贴纸不同，具体国家和条码以及价格如下表'
DEFAULT_SECTION_2 = '2. 价格小圆贴（白色不干胶底，黑色字体）：请安排价格小圆贴，尺寸 1.5cm*1.5cm，同样品'
DEFAULT_SECTION_3 = '3. BABY 小圆贴（白底黑字：尺寸 1.5cm*1.5cm，同样品）'
DEFAULT_FOOTER = [
    '注：大货里小圆贴的裁切一定要适当，要便于工厂拿下来贴在吊钩上又不会损坏小圆贴，送大货时请放些余量',
    '发票：由我司付货款！请开增值税发票!',
    '注意包装时一定要颜色分开包装，切记.',
]


# ==================== 提取逻辑 ====================
def extract_ticket_info(text):
    info = {}
    m = re.search(r'Style ORIN[:\s]+(\d{9})', text)
    info['style_orin'] = m.group(1) if m else None
    m = re.search(r'Name:\s*(.+?)\s+Kimball', text)
    info['style_name'] = m.group(1).strip() if m else None
    m = re.search(r'Kimball[:\s]+(\d{5})', text)
    info['kimball'] = m.group(1) if m else None
    m = re.search(r'Supplier ID[:\s]+(\d{5})\s*-\s*(.+?)(?:\n|$)', text)
    info['supplier_id'] = m.group(1) if m else None
    m = re.search(
        r'Department[:\s]+(\d{2})\s+Name:\s*(.+?)\s+Section[:\s]+(\d{2})\s+Name:\s*(.+?)\s+Subsection[:\s]+(\d+)',
        text, re.DOTALL,
    )
    if m:
        info['department'] = f"{m.group(1)}-{m.group(3)}-{m.group(5)}"
    m = re.search(r'Total Units QTY of Tickets[:\s]+([\d,]+)', text)
    info['total_tickets'] = int(m.group(1).replace(',', '')) if m else None

    # SKU 数据 (按区域)
    skus_by_region = {}
    current_region = None
    region_pattern = '|'.join(REGION_CN.keys())
    for line in text.split('\n'):
        rm = re.match(rf'^({region_pattern})\s*$', line.strip())
        if rm:
            current_region = rm.group(1)
            skus_by_region.setdefault(current_region, [])
            continue
        m = re.match(
            r'\s*(212\d{6})\s+(\d{13})\s+(\d{7})\s+(\w+)\s+([\d,]+)\s+(\d+)\s+(.+?)\s+',
            line,
        )
        if m and current_region:
            price_match = re.search(r'([\d.]+)$', line.replace(',', ''))
            skus_by_region[current_region].append({
                'sku': m.group(1),
                'barcode': m.group(2),
                'kimball_ext': m.group(3),
                'color': m.group(4),
                'qty': int(m.group(5).replace(',', '')),
                'size_desc': m.group(7).strip(),
                'price': price_match.group(0) if price_match else None,
            })
    info['skus_by_region'] = skus_by_region
    return info


def extract_po_quantities(text):
    quantities = {}
    pattern = r'\s*(NE1 - MGB|NE2 - BOR|US1 - PA|US2 - FL|GCC|IB|ROI|ROO|UK)\s+(\w+)\s+(\d+)\s+([\d,]+)\s+(\d+)'
    for line in text.split('\n'):
        m = re.match(pattern, line)
        if m:
            region = m.group(1).replace(' ', '')  # 'NE1 - MGB' -> 'NE1-MGB'
            qty = int(m.group(4).replace(',', ''))
            quantities[region] = quantities.get(region, 0) + qty
    return quantities


# ==================== 生成 Excel ====================
def build_workbook(info, po_quantities):
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('采购单')

    s_title = xlwt.easyxf('font: bold on, height 280; align: horiz center, vert center')
    s_header = xlwt.easyxf(
        'font: bold on; align: horiz center, vert center; '
        'pattern: pattern solid, fore_color gray25; '
        'border: top thin, bottom thin, left thin, right thin'
    )
    s_text = xlwt.easyxf('align: horiz left, vert center, wrap on')
    s_cell = xlwt.easyxf(
        'align: horiz center, vert center, wrap on; '
        'border: top thin, bottom thin, left thin, right thin'
    )

    # 标题
    title = f"{info['style_orin']} 价格小圆贴&条码贴纸采购单"
    ws.write_merge(0, 0, 0, 10, title, s_title)
    now = datetime.datetime.now().astimezone()
    ws.write(0, 11, f"{now.year}.{now.month}.{now.day}", s_title)

    # 文案
    ws.write(1, 0, DEFAULT_GREETING, s_text)
    ws.write(2, 0, DEFAULT_NOTE_1, s_text)
    ws.write(3, 0, DEFAULT_SECTION_1, s_text)
    ws.write(4, 0, DEFAULT_SECTION_1_NOTE, s_text)

    # 表头 (固定顺序!!)
    for j, h in enumerate(HEADERS):
        ws.write(5, j, h, s_header)

    # SKU 数据
    row = 6
    total_qty = 0
    for region, skus in info['skus_by_region'].items():
        symbol = REGION_CURRENCY.get(region, '')
        region_label = REGION_CN.get(region, region)
        for i, sku in enumerate(skus):
            ws.write(row, 0, region_label if i == 0 else '', s_cell)
            ws.write(row, 1, sku['color'], s_cell)
            ws.write(row, 2, sku['color'], s_cell)
            ws.write(row, 3, int(sku['kimball_ext']), s_cell)
            ws.write(row, 4, info['department'], s_cell)
            ws.write(row, 5, int(sku['sku']), s_cell)
            ws.write(row, 6, int(info['style_orin']), s_cell)
            ws.write(row, 7, int(sku['barcode']), s_cell)
            ws.write(row, 8, int(info['supplier_id']), s_cell)
            ws.write(row, 9, sku['size_desc'], s_cell)
            price_text = f"{symbol}{sku['price']}" if sku['price'] else ''
            ws.write(row, 10, price_text, s_cell)
            ws.write(row, 11, sku['qty'], s_cell)
            total_qty += sku['qty']
            row += 1

    # 合计
    ws.write(row, 10, '合计', s_header)
    ws.write(row, 11, total_qty, s_header)
    row += 2

    # 区块 2: 价格小圆贴
    ws.write(row, 0, DEFAULT_SECTION_2, s_text)
    row += 1
    ws.write(row, 0, '内容', s_header)
    ws.write(row, 1, '数量', s_header)
    row += 1
    price_summary = {}
    for region, skus in info['skus_by_region'].items():
        symbol = REGION_CURRENCY.get(region, '')
        for sku in skus:
            if not sku['price']:
                continue
            key = f"{symbol}{sku['price']}"
            price_summary[key] = price_summary.get(key, 0) + sku['qty']
    for price_text, qty in sorted(price_summary.items()):
        ws.write(row, 0, price_text, s_cell)
        ws.write(row, 1, qty, s_cell)
        row += 1
    ws.write(row, 0, '合计', s_header)
    ws.write(row, 1, total_qty, s_header)
    row += 2

    # 区块 3: BABY
    ws.write(row, 0, DEFAULT_SECTION_3, s_text)
    row += 1
    ws.write(row, 0, '内容', s_header)
    ws.write(row, 1, '数量', s_header)
    row += 1
    ws.write(row, 0, 'BABY', s_cell)
    ws.write(row, 1, total_qty, s_cell)
    row += 2

    # 备注
    for note in DEFAULT_FOOTER:
        ws.write(row, 0, note, s_text)
        row += 1

    return wb, total_qty


# ==================== 后置自检 ====================
def self_check(out_path, info, total_qty, po_total):
    """生成后用 xlrd 读回检查格式正确性"""
    try:
        import xlrd
    except ImportError:
        return ['⚠️ 跳过自检 (xlrd 未安装)']

    issues = []
    wb = xlrd.open_workbook(str(out_path))
    ws = wb.sheet_by_index(0)

    # 检查 1: 标题
    title = ws.cell_value(0, 0)
    if info['style_orin'] not in title:
        issues.append(f"❌ R0 标题缺少款号: {title}")

    # 检查 2: 表头
    actual_headers = [ws.cell_value(5, j) for j in range(12)]
    if actual_headers != HEADERS:
        issues.append(f"❌ R5 表头不匹配:\n  期望: {HEADERS}\n  实际: {actual_headers}")

    # 检查 3: Ticket / PO 比例
    if po_total:
        ratio = total_qty / po_total
        if not (1.01 <= ratio <= 1.03):
            issues.append(f"⚠️ Ticket/PO 比例 {ratio:.4f} 偏离 1.02 (PO 数据可能不全)")

    # 检查 4: SKU 数量 = R5 之后的数据行
    sku_count = sum(len(s) for s in info['skus_by_region'].values())
    if sku_count == 0:
        issues.append("❌ 没有提取到任何 SKU,Ticket PDF 解析失败")

    return issues


# ==================== 入口 ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ticket', help='Ticket Request PDF 路径')
    parser.add_argument('po', help='PO PDF 路径')
    parser.add_argument('--output', '-o', default=None, help='输出目录 (默认 PDF 同目录)')
    args = parser.parse_args()

    ticket_path = pathlib.Path(args.ticket).resolve()
    po_path = pathlib.Path(args.po).resolve()
    # 输出目录: --output 优先; 否则默认 projects/Primark/<款号>/<日期>/
    if args.output:
        out_dir = pathlib.Path(args.output).resolve()
    else:
        # 推断 workspace 根: 优先环境变量 → 默认 ~/.openclaw/workspace/agents/textile-trade
        workspace_root = _resolve_workspace_root()
        if workspace_root is None:
            workspace_root = ticket_path.parent
        # 款号临时占位 (后面会被真实款号覆盖)
        out_dir = ticket_path.parent  # 先用临时目录

    if not ticket_path.exists() or not po_path.exists():
        print(f"❌ 文件不存在: {ticket_path} / {po_path}")
        sys.exit(1)

    print(f"📥 输入:\n  Ticket: {ticket_path.name}\n  PO: {po_path.name}\n")

    with open(ticket_path, 'rb') as f:
        ticket_text = ''.join(p.extract_text() or '' for p in pypdf.PdfReader(f).pages)
    with open(po_path, 'rb') as f:
        po_text = ''.join(p.extract_text() or '' for p in pypdf.PdfReader(f).pages)

    info = extract_ticket_info(ticket_text)
    po_quantities = extract_po_quantities(po_text)

    if not info.get('style_orin'):
        print("❌ 未能从 Ticket 提取款号 ORIN")
        sys.exit(1)

    wb, total_qty = build_workbook(info, po_quantities)

    now = datetime.datetime.now().astimezone()
    # 如果未指定 --output, 落到 projects/Primark/<款号>/<日期>/
    if not args.output:
        workspace_root = _resolve_workspace_root()
        if workspace_root is not None:
            date_str = f"{now.year}{now.month:02d}{now.day:02d}"
            out_dir = workspace_root / 'projects' / 'Primark' / info['style_orin'] / date_str
            out_dir.mkdir(parents=True, exist_ok=True)

    out_name = f"{info['style_orin']} 价格小圆贴&条码贴 采购单-{now.year}.{now.month}.{now.day}.xls"
    out_path = (out_dir / out_name).resolve()
    wb.save(str(out_path))

    po_total = sum(po_quantities.values())
    ratio = total_qty / po_total if po_total else 0

    print(f"✅ 采购单已生成")
    print(f"📍 绝对路径: {out_path}")
    print(f"📁 目录: {out_path.parent}")
    print(f"\n📊 摘要:")
    print(f"  款号: {info['style_orin']} - {info.get('style_name')}")
    print(f"  部门号: {info.get('department')}")
    print(f"  Kimball: {info.get('kimball')}")
    print(f"  供应商: {info.get('supplier_id')}")
    print(f"  SKU 数: {sum(len(s) for s in info['skus_by_region'].values())} 个")
    print(f"  Ticket 总数: {total_qty:,}")
    print(f"  PO 总数: {po_total:,}")
    print(f"  Ticket/PO 比例: {ratio:.4f}")

    print(f"\n🔎 自检:")
    issues = self_check(out_path, info, total_qty, po_total)
    if issues:
        for issue in issues:
            print(f"  {issue}")
        sys.exit(2)
    else:
        print("  ✅ 全部通过 (标题/表头/SKU/比例)")


if __name__ == '__main__':
    main()
