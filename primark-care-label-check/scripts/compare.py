#!/usr/bin/env python3
"""
Primark 洗标 PDF vs 洗标采购单 .xls 比对脚本
用法: python3 compare.py <洗标采购单.xls> <洗标 PDF> [--output JSON]

输出: 结构化 JSON {
  "verdict": "PASS" | "WARN" | "FAIL",
  "header": {...},
  "checks": [...],          # 强校验字段 (款号/部门/SKU/Kimball/供应商/季节/成分/制造国)
  "languages": {...},       # 多语言出现情况
  "structure": {...},       # 版面结构 (欧洲/美国/阿拉伯文/EXCLUSIVE OF DECORATION)
  "issues": [...],
  "warnings": [...]
}

LLM 拿 JSON 渲染成 markdown 报告即可,不要重新写比对逻辑。
"""
import sys, os, re, json, argparse, pathlib

try:
    import pypdf, xlrd
except ImportError as e:
    print(f"❌ 缺少依赖: {e}\n请: pip3 install pypdf xlrd", file=sys.stderr)
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


# ==================== 提取采购单 ====================
def parse_purchase_xls(path):
    """从洗标采购单 .xls 提取结构化数据"""
    info = {
        'model': None,        # 26TF4AK006
        'season': None,
        'department': None,
        'style_orin': None,
        'supplier_id': None,
        'color': None,
        'origin': None,
        'sku_rows': [],       # [{size, sku, kimball, color, eu_qty, us_qty}]
        'composition_eu': None,
        'composition_us': None,
        'wash_instruction': None,
        'arabic_lines': [],   # ar: ... 行
        'cover_eu': None,
        'cover_us': None,
        'first_batch_date': None,
        'second_batch_date': None,
    }

    wb = xlrd.open_workbook(str(path))
    ws = wb.sheet_by_index(0)

    # 标题行 R0 提取型号
    title = str(ws.cell_value(0, 0)) if ws.nrows > 0 else ''
    m = re.search(r'(\d{2}[A-Z]{2}\d[A-Z]{2}\d{3})', title)
    if m:
        info['model'] = m.group(1)

    # 逐行扫描标签字段
    for i in range(min(ws.nrows, 50)):
        row = [str(c).strip() if c else '' for c in ws.row_values(i)]
        a, b = row[0] if len(row) > 0 else '', row[1] if len(row) > 1 else ''

        if a == '颜色' and b:
            info['color'] = b
        elif a == '季节' and b:
            info['season'] = b
        elif a == '部门号' and b:
            info['department'] = b
        elif a == 'STYLE' and b:
            info['style_orin'] = b
        elif a == '供应商代码' and b:
            info['supplier_id'] = b
        elif a == '制造国' and b:
            info['origin'] = b
        elif '材质' in a and b:
            info['material'] = b
        elif '水洗方式' in a:
            for cell in row[1:]:
                if cell:
                    info['wash_instruction'] = cell
                    break
        elif '成份及数量' in a or '成分及数量' in a:
            # 下一行 R+1 通常有 en: ... / en-uk: ...
            if i + 1 < ws.nrows:
                next_row = [str(c) for c in ws.row_values(i + 1)]
                for cell in next_row:
                    if 'en:' in cell or 'en-uk:' in cell:
                        if 'en-uk:' in cell:
                            info['composition_us'] = cell
                        else:
                            info['composition_eu'] = cell
        elif a.startswith('ar:') or (len(row) > 1 and any('ar:' in str(c) for c in row)):
            for cell in row:
                if 'ar:' in str(cell):
                    info['arabic_lines'].append(str(cell))

        # SKU 数据行: R10-R12 范围,匹配 213/212 + 数字
        if re.match(r'\d+\+?Y', a) or 'YRS' in a or '-' in a:
            if len(row) >= 4 and re.match(r'21\d{7}', str(row[1] or '')):
                info['sku_rows'].append({
                    'size': a,
                    'sku': str(row[1]),
                    'kimball': str(row[2]) if len(row) > 2 else '',
                    'color': str(row[3]) if len(row) > 3 else '',
                    'eu_qty': str(row[4]) if len(row) > 4 else '',
                    'us_qty': str(row[5]) if len(row) > 5 else '',
                })

    return info


# ==================== 提取 PDF ====================
def parse_label_pdf(path):
    """从洗标 PDF 提取所有出现的字符串/数字"""
    with open(path, 'rb') as f:
        text = ''.join(p.extract_text() or '' for p in pypdf.PdfReader(f).pages)

    text_compact = re.sub(r'\s+', '', text)

    info = {
        'raw_text': text,
        'styles': list(set(re.findall(r'(99\d{7})', text_compact))),
        'skus': list(set(re.findall(r'(21\d{7})', text_compact))),
        'kimballs': list(set(re.findall(r'(\d{7})', text_compact))),
        'departments': list(set(re.findall(r'(15-\d{2}-\d{2})', text))),
        'suppliers': list(set(re.findall(r'(8[04]\d{3})', text_compact))),
        'origins': [],
        'languages_found': {},
        'has_arabic': bool(re.search(r'[\u0600-\u06FF]', text)),
        'has_eu_composition': 'POLYESTER' in text or 'COTTON' in text or 'COMPOSITION' in text,
        'has_us_composition': 'EXCLUSIVE OF DECORATION' in text,
        'cover_body': {
            'has_cover': 'COVER' in text.upper() or 'cover:' in text.lower(),
            'has_body': 'BODY' in text.upper() or 'body:' in text.lower(),
        },
        'warning_keep_away_from_fire': 'KEEP AWAY FROM FIRE' in text,
    }

    # 制造国
    for country in ['CHINA', 'TAIZHOU', 'NINGBO', 'HANGZHOU', 'BANGLADESH', 'INDIA', 'VIETNAM']:
        if country in text:
            info['origins'].append(country)

    # 多语言前缀
    for lang in ['en:', 'en-uk:', 'en-us:', 'fr:', 'es:', 'de:', 'it:', 'pt:', 'nl:',
                 'pl:', 'cs:', 'ro:', 'hu:', 'sk:', 'el:', 'sv:', 'da:', 'fi:',
                 'no:', 'tr:', 'ar:']:
        info['languages_found'][lang.rstrip(':')] = lang in text

    return info


# ==================== 比对 ====================
def compare(purchase, pdf_info):
    checks = []
    issues = []
    warnings = []

    def add_check(field, expected, actual, ok):
        checks.append({
            'field': field,
            'expected': str(expected) if expected else '-',
            'actual': str(actual) if actual else '-',
            'status': '✅' if ok else '❌',
        })
        if not ok:
            issues.append(f"{field}: 期望 {expected}, 实际 {actual}")

    # === 1. 强校验字段 ===
    if purchase['style_orin']:
        ok = purchase['style_orin'] in pdf_info['styles']
        add_check('STYLE ORIN', purchase['style_orin'],
                  '已出现' if ok else f"未找到 (PDF 中 styles={pdf_info['styles']})", ok)

    if purchase['department']:
        ok = purchase['department'] in pdf_info['departments']
        add_check('部门号', purchase['department'],
                  '已出现' if ok else f"未找到 (PDF 中 departments={pdf_info['departments']})", ok)

    if purchase['supplier_id']:
        ok = purchase['supplier_id'] in pdf_info['suppliers']
        add_check('供应商号', purchase['supplier_id'],
                  '已出现' if ok else f"未找到 (PDF 中 suppliers={pdf_info['suppliers']})", ok)

    if purchase['season']:
        # 季节是 AW26/SS26 这种短码
        ok = purchase['season'] in pdf_info['raw_text']
        add_check('季节', purchase['season'], '已出现' if ok else '未找到', ok)

    # SKU 集合
    if purchase['sku_rows']:
        purchase_skus = set(s['sku'] for s in purchase['sku_rows'])
        sample_skus = set(pdf_info['skus'])
        missing = purchase_skus - sample_skus
        ok = not missing
        add_check('SKU 集合', f"{len(purchase_skus)} 个: {sorted(purchase_skus)}",
                  f"匹配 {len(purchase_skus & sample_skus)}/{len(purchase_skus)}", ok)
        if missing:
            issues.append(f"洗标 PDF 缺少 SKU: {sorted(missing)}")

        # Kimball 集合 - 直接在 compact text 里搜索全字串 (避免 \d{7} 各种干扰)
        text_compact_for_k = re.sub(r'\s+', '', pdf_info['raw_text'])
        purchase_kimballs = set(s['kimball'] for s in purchase['sku_rows'] if s['kimball'])
        matched_k = {k for k in purchase_kimballs if k in text_compact_for_k}
        missing_k = purchase_kimballs - matched_k
        ok = not missing_k
        add_check('Kimball 集合', f"{len(purchase_kimballs)} 个: {sorted(purchase_kimballs)}",
                  f"匹配 {len(matched_k)}/{len(purchase_kimballs)}", ok)
        if missing_k:
            issues.append(f"洗标 PDF 缺少 Kimball: {sorted(missing_k)}")

    # === 2. 制造国 ===
    if purchase.get('origin'):
        # 采购单写"中国/CHINA",PDF 可能是 TAIZHOU/CHINA 或 NINGBO/CHINA
        ok = 'CHINA' in pdf_info['origins'] or any(c in pdf_info['origins'] for c in ['TAIZHOU', 'NINGBO', 'HANGZHOU'])
        add_check('制造国', purchase['origin'],
                  '/'.join(pdf_info['origins']) if pdf_info['origins'] else '未识别', ok)

    # === 3. 成分关键字 ===
    if purchase.get('composition_eu'):
        # 抽采购单成分里的纤维名 (POLYESTER / COTTON 等)
        fibers = re.findall(r'\b(POLYESTER|COTTON|ACRYLIC|POLYAMIDE|ELASTANE|VISCOSE|WOOL|NYLON|POLYAMIDE)\b',
                            purchase['composition_eu'].upper())
        fibers = list(set(fibers))
        if fibers:
            missing_fibers = [f for f in fibers if f not in pdf_info['raw_text'].upper()]
            ok = not missing_fibers
            add_check('成分纤维', f"采购单含 {fibers}",
                      f"PDF 含 {[f for f in fibers if f not in missing_fibers]}", ok)
            if missing_fibers:
                issues.append(f"PDF 缺少成分纤维: {missing_fibers}")

    # === 4. 版面结构 ===
    structure = {
        'has_arabic': pdf_info['has_arabic'],
        'has_eu_composition': pdf_info['has_eu_composition'],
        'has_us_composition (EXCLUSIVE OF DECORATION)': pdf_info['has_us_composition'],
        'has_cover_body_label': pdf_info['cover_body']['has_cover'] and pdf_info['cover_body']['has_body'],
        'languages_count': sum(1 for v in pdf_info['languages_found'].values() if v),
    }

    # 阿拉伯文检查
    if purchase['arabic_lines']:
        if not pdf_info['has_arabic']:
            issues.append("采购单要求阿拉伯文,但 PDF 中未检测到阿拉伯字符 (U+0600-06FF)")
        else:
            checks.append({
                'field': '阿拉伯文', 'expected': '需要', 'actual': '已出现', 'status': '✅'
            })

    # === 5. 多语言数量 ===
    lang_count = structure['languages_count']
    if lang_count < 10:
        warnings.append(f"洗标 PDF 仅检测到 {lang_count} 种语言前缀,欧洲单通常需 14 种以上,请人工核对")

    # === 6. 数量友情提醒 ===
    if purchase['sku_rows']:
        total_eu = sum(int(float(s['eu_qty'])) for s in purchase['sku_rows'] if s['eu_qty'].replace('.', '').isdigit())
        total_us = sum(int(float(s['us_qty'])) for s in purchase['sku_rows'] if s['us_qty'].replace('.', '').isdigit())
        warnings.append(f"采购单总数: 欧洲 {total_eu:,} / 美国 {total_us:,} (洗标 PDF 张数请人工对照检查)")

    verdict = 'FAIL' if issues else ('WARN' if warnings else 'PASS')
    return {
        'verdict': verdict,
        'checks': checks,
        'structure': structure,
        'languages_found': pdf_info['languages_found'],
        'issues': issues,
        'warnings': warnings,
    }


# ==================== 入口 ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('purchase', help='洗标采购单 .xls 路径')
    parser.add_argument('pdf', help='洗标 PDF 路径')
    parser.add_argument('--output', '-o', default=None, help='输出 JSON 路径 (默认 stdout)')
    args = parser.parse_args()

    p1 = pathlib.Path(args.purchase).resolve()
    p2 = pathlib.Path(args.pdf).resolve()
    if not p1.exists() or not p2.exists():
        print(f"❌ 文件不存在", file=sys.stderr)
        sys.exit(1)

    purchase = parse_purchase_xls(p1)
    pdf_info = parse_label_pdf(p2)
    result = compare(purchase, pdf_info)
    result['header'] = {
        'model': purchase['model'],
        'style_orin': purchase['style_orin'],
        'department': purchase['department'],
        'supplier_id': purchase['supplier_id'],
        'season': purchase['season'],
        'color': purchase['color'],
        'origin': purchase['origin'],
        'purchase_file': p1.name,
        'pdf_file': p2.name,
    }

    out = json.dumps(result, ensure_ascii=False, indent=2)

    # 输出路径: --output 优先; 否则默认 projects/Primark/<型号或款号>/<日期>/
    if args.output:
        out_path = pathlib.Path(args.output).resolve()
    else:
        import datetime
        workspace_root = _resolve_workspace_root()
        now = datetime.datetime.now().astimezone()
        date_str = f"{now.year}{now.month:02d}{now.day:02d}-{now.hour:02d}{now.minute:02d}"
        key = purchase.get('model') or purchase.get('style_orin') or 'unknown'
        if workspace_root is not None:
            out_dir = workspace_root / 'projects' / 'Primark' / key
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"比对结果-洗标-{date_str}.json"
        else:
            out_path = p1.parent / f"比对结果-洗标-{date_str}.json"
        out_path = out_path.resolve()

    out_path.write_text(out, encoding='utf-8')
    print(f"✅ 结果已写入")
    print(f"📍 绝对路径: {out_path}")
    print(f"📁 目录: {out_path.parent}")
    print(f"\nVerdict: {result['verdict']}")
    print(f"通过: {sum(1 for c in result['checks'] if c['status']=='✅')}/{len(result['checks'])}")
    print(f"问题: {len(result['issues'])}, 警告: {len(result['warnings'])}")


if __name__ == '__main__':
    main()
