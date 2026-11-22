#!/usr/bin/env python3
"""환절기 편집국 ⑦ 제작 매니저 — final.json을 카드뉴스 PNG로 렌더한다.

사용:  python3 desk/render.py desk/projects/2026-11-26_슬러그 [--draft]

게이트 (--draft가 아니면):
  - 05_검수보고서.md 에 '판정: 발행본' 과 '합계: 90' 이상
  - final.json 에 '[…]' 빈칸, '확인할 것', 'TODO' 가 없을 것
  - 렌더 후 글 넘침(⚠) 장이 없을 것
"""
import asyncio, base64, json, re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / 'fonts'
FACES = [('Gothic A1', 400, 'GothicA1-Regular.ttf'), ('Gothic A1', 500, 'GothicA1-Medium.ttf'),
         ('Gothic A1', 700, 'GothicA1-Bold.ttf'), ('Gothic A1', 800, 'GothicA1-ExtraBold.ttf'),
         ('Gothic A1', 900, 'GothicA1-Black.ttf'), ('East Sea Dokdo', 400, 'EastSeaDokdo-Regular.ttf')]


def fail(msg):
    print(f'✖ 렌더 중단: {msg}')
    sys.exit(1)


def gate(proj: Path, data: dict):
    rep = proj / '05_검수보고서.md'
    if not rep.exists():
        fail('05_검수보고서.md 가 없습니다.')
    t = rep.read_text(encoding='utf-8')
    if not re.search(r'판정:\s*발행본', t):
        fail("검수보고서 판정이 '발행본'이 아닙니다.")
    m = re.search(r'합계:\s*(\d+)', t)
    if not m or int(m.group(1)) < 90:
        fail(f"발행 심사 합계가 90점 미만입니다 ({m.group(1) if m else '없음'}).")
    s = json.dumps(data, ensure_ascii=False)
    for pat, name in [(r'\[[^\]\n]{1,40}\]', "'[ ]' 빈칸"), (r'확인할 것', "'확인할 것'"), (r'TODO', 'TODO')]:
        hit = re.search(pat, s)
        if hit:
            fail(f'final.json 에 {name} 이 남아 있습니다: {hit.group(0)}')


async def render(proj: Path, data: dict, outdir: Path):
    from playwright.async_api import async_playwright
    css = ''.join(f"@font-face{{font-family:'{f}';font-weight:{w};src:url('{(FONTS / fn).as_uri()}')}}" for f, w, fn in FACES)
    html = (ROOT / 'index.html').read_text(encoding='utf-8').replace('<style>', '<style>' + css, 1)
    tmp = proj / '.render.html'
    tmp.write_text(html, encoding='utf-8')
    outdir.mkdir(exist_ok=True)
    for old in outdir.glob('*.png'):
        old.unlink()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1500, 'height': 1000})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file') else r.abort())
        await pg.goto(tmp.as_uri())
        await pg.wait_for_timeout(1200)
        await pg.click('#btnImport')
        await pg.fill('#importText', json.dumps(data, ensure_ascii=False))
        await pg.click('#btnImportOk')
        await pg.wait_for_timeout(600)
        labels = await pg.evaluate("[...document.querySelectorAll('#strip .thumb span')].map(s=>s.textContent)")
        files = []
        for i, lab in enumerate(labels):
            await pg.evaluate(f"document.querySelectorAll('#strip .thumb')[{i}].click()")
            await pg.wait_for_timeout(150)
            u = await pg.evaluate("document.querySelector('#stageCanvas canvas').toDataURL('image/png')")
            name = f"{i:02d}_{re.sub(r'[^0-9A-Za-z가-힣]+', '', lab.replace('⚠', ''))}.png"
            (outdir / name).write_bytes(base64.b64decode(u.split(',')[1]))
            files.append((name, '⚠' in lab))
        await b.close()
    tmp.unlink()
    if errs:
        print('⚠ 페이지 오류:', errs)
    return files


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    draft = '--draft' in sys.argv
    if not args:
        fail('프로젝트 폴더를 지정하세요.')
    proj = Path(args[0]).resolve()
    data = json.loads((proj / 'final.json').read_text(encoding='utf-8'))
    if not data.get('format'):
        fail('final.json 에 format 이 없습니다.')
    if not draft:
        gate(proj, data)
    out = proj / ('png_draft' if draft else 'png')
    files = asyncio.run(render(proj, data, out))
    over = [n for n, o in files if o]
    for n, o in files:
        print(('⚠ 넘침 ' if o else '✔ ') + n)
    if over and not draft:
        fail(f'글이 넘친 장이 있습니다: {over}')
    z = out / f'환절기_{proj.name}.zip'
    with zipfile.ZipFile(z, 'w') as zf:
        for n, _ in files:
            zf.write(out / n, n)
        cap = proj / 'caption.txt'
        if cap.exists() and cap.read_text(encoding='utf-8').strip():
            zf.write(cap, 'caption.txt')
    print(f"{'시안' if draft else '발행본'} {len(files)}장 → {z}")


if __name__ == '__main__':
    main()
