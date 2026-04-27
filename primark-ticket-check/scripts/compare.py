#!/usr/bin/env python3
"""
Primark 条码贴/价签 vs Ticket Request 比对脚本
用法: python3 compare.py <Ticket_Request.PDF> <工厂打样.PDF> [--output JSON]

输出: 结构化 JSON {
  "verdict": "PASS" | "WARN" | "FAIL",
  "header": {...},          # 商品基本信息
  "checks": [               # 逐项比对
    {"field": "...", "ticket": "...", "sample": "...", "status": "✅/❌/⚠️"}
  ],
  "quantities": {...},      # 数量明细 (友情提醒)
  "issues": [...],          # 发现的问题
  "warnings": [...]         # 友情提醒
}

LLM 拿 JSON 渲染成 markdown 报告即可,不要重新写比对逻辑。
"""
import sys, os, re, json, argparse, pathlib

try:
    import pypdf
except ImportError:
    print("❌ 缺少 pypdf,请: pip3 install pypdf", file=sys.stderr)
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


# ==================== 提取逻辑 ====================
def extract_pdf_text(path):
    with open(path, 'rb') as f:
        return ''.join(p.extract_text() or '' for p in pypdf.PdfReader(f).pages)


def parse_ticket_request(text):
    """从 Ticket Request PDF 提取所有商品/SKU 信息"""
    info = {
        'po': None,
        'style_orin': None,
        'style_name': None,
        'kimball': None,
        'supplier_id': None,
        'department': None,
        'tag_type': None,
        'total_tickets': None,
        'skus_by_region': {},  # {region: [{sku, barcode, kimball_ext, color, qty, size_desc, price}, ...]}
    }

    m = re.search(r'Purchase Order[:\s]+(\d{7})', text)
    info['po'] = m.group(1) if m else None
    m = re.search(r'Style ORIN[:\s]+(\d{9})', text)
    info['style_orin'] = m.group(1) if m else None
    m = re.search(r'Name:\s*(.+?)\s+Kimball', text)
    info['style_name'] = m.group(1).strip() if m else None
    m = re.search(r'Kimball[:\s]+(\d{5})', text)
    info['kimball'] = m.group(1) if m else None
    m = re.search(r'Supplier ID[:\s]+(\d{5})', text)
    info['supplier_id'] = m.group(1) if m else None
    m = re.search(
        r'Department[:\s]+(\d{2})\s+Name:\s*.+?Section[:\s]+(\d{2})\s+Name:\s*.+?Subsection[:\s]+(\d+)',
        text, re.DOTALL,
    )
    if m:
        info['department'] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r'Total Units QTY of Tickets[:\s]+([\d,]+)', text)
    if m:
        info['total_tickets'] = int(m.group(1).replace(',', ''))
    m = re.search(r'Tag Type[:\s]+(.+?)(?:\n|$)', text)
    info['tag_type'] = m.group(1).strip() if m else None

    # SKU 行
    region_pattern = r'(ROI|GCC|ROO|NE1-MGB|NE2-BOR|UK|US1-PA|US2-FL|IB)'
    current_region = None
    for line in text.split('\n'):
        rm = re.match(rf'^{region_pattern}\s*$', line.strip())
        if rm:
            current_region = rm.group(1)
            info['skus_by_region'].setdefault(current_region, [])
            continue
        m = re.match(
            r'\s*(212\d{6})\s+(\d{13})\s+(\d{7})\s+(\w+)\s+([\d,]+)\s+(\d+)\s+(\S+)',
            line,
        )
        if m and current_region:
            price = re.search(r'([\d.]+)\s*$', line)
            info['skus_by_region'][current_region].append({
                'sku': m.group(1),
                'barcode': m.group(2),
                'kimball_ext': m.group(3),
                'color': m.group(4),
                'qty': int(m.group(5).replace(',', '')),
                'size_desc': m.group(7),
                'price': price.group(1) if price else None,
            })
    return info


def parse_sample_pdf(text, kimball_5=None):
    """从工厂打样 PDF 提取条码/SKU/价格等

    kimball_5: 从 Ticket 读出的 5 位 Kimball 基础号,用来动态构造
               Kimball-7 正则(避免硬编码前缀造成新款式误报)。
    """
    info = {
        'barcodes': [],   # 所有出现的 EAN-13
        'skus': [],       # 所有出现的 SKU (212xxxxxx)
        'kimballs': [],   # Kimball-7 (3876xxx / 1636xxx / 动态 kimball_5+xx)
        'styles': [],     # ORIN (9 位)
        'suppliers': [],  # 供应商号
        'prices': [],     # 价格字符串
        'departments': [],
        'tag_counts': [], # "xxxxx张" 等张数
    }

    # 去除所有空白, 避免条码/Kimball 在 PDF 中被空格切断
    text_compact = re.sub(r'\s+', '', text)

    # 条码 (13 位数字, 5397362xxxxxx 开头 - Primark 供应商前缀)
    for m in re.finditer(r'(5397362\d{6})', text_compact):
        info['barcodes'].append(m.group(1))
    # 其他 539 开头 13 位
    for m in re.finditer(r'(539\d{10})', text_compact):
        if m.group(1) not in info['barcodes']:
            info['barcodes'].append(m.group(1))

    # SKU (212 + 6 位)
    for m in re.finditer(r'(212\d{6})', text_compact):
        info['skus'].append(m.group(1))

    # Kimball-7: 优先用 Ticket 里读出的 5 位基础号动态构造正则
    # (避免硬编码前缀造成新款型误报,例如 28130xx / 25612xx 等)
    if kimball_5 and re.fullmatch(r'\d{5}', kimball_5):
        for m in re.finditer(r'(' + re.escape(kimball_5) + r'\d{2})', text_compact):
            info['kimballs'].append(m.group(1))
    # 历史硬编码前缀作为兜底(保证老文档不回归)
    for m in re.finditer(r'(3876\d{3})', text_compact):
        if m.group(1) not in info['kimballs']:
            info['kimballs'].append(m.group(1))
    for m in re.finditer(r'(1636\d{3})', text_compact):
        if m.group(1) not in info['kimballs']:
            info['kimballs'].append(m.group(1))

    # 9 位 STYLE (在原文中)
    for m in re.finditer(r'\b(99\d{7})\b', text):
        info['styles'].append(m.group(1))

    # 供应商号 (5 位 80xxx 或 84xxx)
    for m in re.finditer(r'(8[04]\d{3})', text_compact):
        info['suppliers'].append(m.group(1))

    # 价格 (£/€/$/AED + 数字)
    for m in re.finditer(r'(?:£|€|\$|AED)\s*\d+(?:\.\d+)?', text):
        info['prices'].append(m.group(0))

    # 部门号 15-XX-XX (保留原始文本以保连字符)
    for m in re.finditer(r'(15-\d{2}-\d{2})', text):
        info['departments'].append(m.group(1))

    # 9 位 STYLE 补充从 compact 找
    for m in re.finditer(r'(99\d{7})', text_compact):
        if m.group(1) not in info['styles']:
            info['styles'].append(m.group(1))

    # 张数标注 "xxxxx张" 或 "xxxxxᵥ" (PDF 中可能变乱码)
    for m in re.finditer(r'(\d+)[张ᵥᕥ]', text):
        info['tag_counts'].append(int(m.group(1)))

    return info


# ==================== 比对逻辑 ====================
def compare(ticket_info, sample_info):
    checks = []
    issues = []
    warnings = []

    # 1. STYLE ORIN
    if ticket_info['style_orin']:
        in_sample = ticket_info['style_orin'] in sample_info['styles']
        checks.append({
            'field': 'STYLE ORIN',
            'ticket': ticket_info['style_orin'],
            'sample': '已出现' if in_sample else '未找到',
            'status': '✅' if in_sample else '❌',
        })
        if not in_sample:
            issues.append(f"STYLE ORIN {ticket_info['style_orin']} 未在样品 PDF 出现")

    # 2. Kimball
    if ticket_info['kimball']:
        # Kimball 5 位是基础号,样品里可能是 Kimball-7 (基础号+尺码后缀)
        kimball_5 = ticket_info['kimball']
        in_sample = any(k.startswith(kimball_5) for k in sample_info['kimballs'])
        checks.append({
            'field': 'Kimball',
            'ticket': kimball_5,
            'sample': '已出现' if in_sample else '未找到',
            'status': '✅' if in_sample else '❌',
        })
        if not in_sample:
            issues.append(f"Kimball {kimball_5} 未在样品出现")

    # 3. 供应商号
    if ticket_info['supplier_id']:
        in_sample = ticket_info['supplier_id'] in sample_info['suppliers']
        checks.append({
            'field': '供应商号',
            'ticket': ticket_info['supplier_id'],
            'sample': '已出现' if in_sample else '未找到',
            'status': '✅' if in_sample else '❌',
        })
        if not in_sample:
            issues.append(f"供应商号 {ticket_info['supplier_id']} 未在样品出现")

    # 4. 部门号
    if ticket_info['department']:
        in_sample = ticket_info['department'] in sample_info['departments']
        checks.append({
            'field': '部门号',
            'ticket': ticket_info['department'],
            'sample': '已出现' if in_sample else '未找到',
            'status': '✅' if in_sample else '❌',
        })
        if not in_sample:
            issues.append(f"部门号 {ticket_info['department']} 未在样品出现")

    # 4.5 Kimball-7 检查 (Ticket 里每个 SKU 都有一个 kimball_ext)
    ticket_kimball7 = set()
    for skus in ticket_info['skus_by_region'].values():
        for sku in skus:
            ticket_kimball7.add(sku['kimball_ext'])
    sample_kimball_set = set(sample_info['kimballs'])
    missing_k7 = ticket_kimball7 - sample_kimball_set
    if ticket_kimball7:
        checks.append({
            'field': 'Kimball-7 集合',
            'ticket': f"{len(ticket_kimball7)} 个",
            'sample': f"{len(sample_kimball_set & ticket_kimball7)} 个匹配",
            'status': '✅' if not missing_k7 else '❌',
        })
        if missing_k7:
            issues.append(f"样品缺少 Kimball-7: {sorted(missing_k7)}")

    # 5. SKU 集合
    ticket_skus = set()
    for skus in ticket_info['skus_by_region'].values():
        for sku in skus:
            ticket_skus.add(sku['sku'])
    sample_sku_set = set(sample_info['skus'])

    missing_skus = ticket_skus - sample_sku_set
    extra_skus = sample_sku_set - ticket_skus

    checks.append({
        'field': 'SKU 集合',
        'ticket': f"{len(ticket_skus)} 个",
        'sample': f"{len(sample_sku_set)} 个",
        'status': '✅' if not missing_skus and not extra_skus else '❌',
    })
    if missing_skus:
        issues.append(f"样品缺少 SKU: {sorted(missing_skus)}")
    if extra_skus:
        warnings.append(f"样品多出未在 Ticket 的 SKU: {sorted(extra_skus)}")

    # 6. Barcode 集合
    ticket_barcodes = set()
    for skus in ticket_info['skus_by_region'].values():
        for sku in skus:
            ticket_barcodes.add(sku['barcode'])
    sample_barcode_set = set(sample_info['barcodes'])

    missing_barcodes = ticket_barcodes - sample_barcode_set
    checks.append({
        'field': '条码 (EAN-13)',
        'ticket': f"{len(ticket_barcodes)} 个",
        'sample': f"{len(sample_barcode_set)} 个",
        'status': '✅' if not missing_barcodes else '❌',
    })
    if missing_barcodes:
        issues.append(f"样品缺少条码: {sorted(missing_barcodes)}")

    # 7. EAN-13 校验位 (光看格式不验校验位,这里只验长度)
    bad_barcodes = [b for b in sample_info['barcodes'] if len(b) != 13]
    if bad_barcodes:
        issues.append(f"样品有非 13 位条码: {bad_barcodes}")

    # 8. 数量友情提醒 (不强制)
    quantities = {}
    for region, skus in ticket_info['skus_by_region'].items():
        quantities[region] = sum(s['qty'] for s in skus)

    sample_total = sum(sample_info['tag_counts']) if sample_info['tag_counts'] else None
    if sample_total and ticket_info['total_tickets']:
        diff = sample_total - ticket_info['total_tickets']
        if abs(diff) > ticket_info['total_tickets'] * 0.05:  # >5% 差异才警告
            warnings.append(
                f"样品总张数 {sample_total} vs Ticket {ticket_info['total_tickets']} "
                f"差异 {diff:+d} (>5%)"
            )

    # 综合判定
    if issues:
        verdict = 'FAIL'
    elif warnings:
        verdict = 'WARN'
    else:
        verdict = 'PASS'

    return {
        'verdict': verdict,
        'checks': checks,
        'quantities': quantities,
        'sample_tag_counts': sample_info['tag_counts'],
        'issues': issues,
        'warnings': warnings,
    }


# ==================== 入口 ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ticket', help='Ticket Request PDF 路径')
    parser.add_argument('sample', help='工厂打样 PDF 路径')
    parser.add_argument('--output', '-o', default=None, help='输出 JSON 路径 (默认 stdout)')
    args = parser.parse_args()

    ticket_path = pathlib.Path(args.ticket).resolve()
    sample_path = pathlib.Path(args.sample).resolve()

    if not ticket_path.exists() or not sample_path.exists():
        print(f"❌ 文件不存在", file=sys.stderr)
        sys.exit(1)

    ticket_text = extract_pdf_text(ticket_path)
    sample_text = extract_pdf_text(sample_path)

    ticket_info = parse_ticket_request(ticket_text)
    sample_info = parse_sample_pdf(sample_text, kimball_5=ticket_info.get('kimball'))

    result = compare(ticket_info, sample_info)
    result['header'] = {
        'po': ticket_info['po'],
        'style_orin': ticket_info['style_orin'],
        'style_name': ticket_info['style_name'],
        'kimball': ticket_info['kimball'],
        'supplier_id': ticket_info['supplier_id'],
        'department': ticket_info['department'],
        'tag_type': ticket_info['tag_type'],
        'ticket_file': ticket_path.name,
        'sample_file': sample_path.name,
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)

    # 输出路径: --output 优先; 否则默认 projects/Primark/<款号>/<日期>/
    if args.output:
        out_path = pathlib.Path(args.output).resolve()
    else:
        import datetime
        workspace_root = _resolve_workspace_root()
        now = datetime.datetime.now().astimezone()
        date_str = f"{now.year}{now.month:02d}{now.day:02d}-{now.hour:02d}{now.minute:02d}"
        style = ticket_info.get('style_orin') or ticket_info.get('po') or 'unknown'
        if workspace_root is not None:
            out_dir = workspace_root / 'projects' / 'Primark' / style
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"比对结果-条码贴-{date_str}.json"
        else:
            out_path = ticket_path.parent / f"比对结果-条码贴-{date_str}.json"
        out_path = out_path.resolve()

    out_path.write_text(output, encoding='utf-8')
    print(f"✅ 结果已写入")
    print(f"📍 绝对路径: {out_path}")
    print(f"📁 目录: {out_path.parent}")
    print(f"\nVerdict: {result['verdict']}")
    print(f"通过: {sum(1 for c in result['checks'] if c['status']=='✅')}/{len(result['checks'])}")
    print(f"问题: {len(result['issues'])}, 警告: {len(result['warnings'])}")


if __name__ == '__main__':
    main()
