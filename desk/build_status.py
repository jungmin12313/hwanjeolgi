#!/usr/bin/env python3
"""desk/projects/* 를 읽어 desk/status.json 을 만든다. (편집국 현황판 데이터)"""
import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
D = Path(__file__).resolve().parent
STAGES = ['기획안', '취재', '편집 방향', '구성안', '초고', '팩트체크', '퇴고·심사', '발행']
DOCS = [('00_상태.md', '상태'), ('01_기획안.md', '기획안'), ('02_취재표.md', '취재표'), ('03_구성안.md', '구성안'),
        ('04_초고.md', '초고'), ('05_검수보고서.md', '검수보고서'), ('caption.txt', '캡션'), ('06_발행기록.md', '발행기록')]
def kv(t, k):
    m = re.search(rf'^{k}:\s*(.*)$', t, re.M); return m.group(1).strip() if m else ''
out = []
for p in sorted((D / 'projects').iterdir()):
    if not p.is_dir() or p.name.startswith('_'): continue
    st = (p / '00_상태.md').read_text(encoding='utf-8') if (p / '00_상태.md').exists() else ''
    rep = (p / '05_검수보고서.md').read_text(encoding='utf-8') if (p / '05_검수보고서.md').exists() else ''
    score = re.search(r'합계:\s*(\d+)', rep)
    docs = []
    for fn, label in DOCS:
        f = p / fn
        if f.exists():
            t = f.read_text(encoding='utf-8')
            filled = bool(t.strip()) and '(슬러그)' not in t
            docs.append({'file': fn, 'label': label, 'text': t, 'filled': filled})
    pngs = [f'projects/{p.name}/{d}/{x.name}' for d in ('png', 'png_draft') if (p / d).exists() for x in sorted((p / d).glob('*.png'))]
    date, _, slug = p.name.partition('_')
    out.append({'id': p.name, 'date': date, 'title': slug.replace('-', ' · '),
                'series': kv(st, '시리즈'),
                'stage': int(kv(st, '현재 단계') or 1), 'state': kv(st, '상태'), 'blocker': kv(st, '막힌 이유'),
                'next': kv(st, '다음 할 일'), 'needsPublisher': kv(st, '발행인 확인 필요') == '예',
                'score': int(score.group(1)) if score else None, 'verdict': kv(rep, '판정'),
                'pngs': pngs, 'draft': bool(pngs) and all('/png_draft/' in x for x in pngs), 'docs': docs})
now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y.%m.%d %H:%M')
json.dump({'updated': now, 'stages': STAGES, 'projects': out}, open(D / 'status.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'status.json: 프로젝트 {len(out)}건 ({now})')
