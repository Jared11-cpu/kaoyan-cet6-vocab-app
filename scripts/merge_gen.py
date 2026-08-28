# -*- coding: utf-8 -*-
"""合并子代理生成结果到 app/words-data.js, 并报告缺失/异常"""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

words = json.load(open('data/words.json', encoding='utf-8'))
gen = {}
indir, outdir = 'data/gen/in', 'data/gen/out'
if os.path.isdir(outdir):
    for fn in sorted(os.listdir(outdir)):
        if not fn.endswith('.json'):
            continue
        try:
            items = json.load(open(os.path.join(outdir, fn), encoding='utf-8'))
        except Exception as e:
            print(f'!! 非法JSON: {fn}: {e}')
            continue
        for it in items:
            w = (it.get('w') or '').strip().lower()
            if w:
                gen[w] = it

missing_r = [w['w'] for w in words if w['w'] not in gen]
print(f'词库: {len(words)} | 已生成: {len(gen)} | 缺失: {len(missing_r)}')

no_c = 0
for w in words:
    g = gen.get(w['w'])
    if not g:
        continue
    w['r'] = (g.get('r') or '').strip()
    c = g.get('c')
    if w['ex']:
        pass  # 有真题例句, 不需要生成例句
    elif isinstance(c, list) and len(c) == 2 and c[0].strip():
        w['c'] = [c[0].strip(), c[1].strip()]
    else:
        no_c += 1
print(f'缺生成例句(无真题例句且代理未生成): {no_c}')
if missing_r:
    print('缺失样例:', missing_r[:20])

with open('app/words-data.js', 'w', encoding='utf-8') as f:
    f.write('// 自动生成, 勿手改: scripts/merge_gen.py\nconst WORDS = ')
    json.dump(words, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
size = os.path.getsize('app/words-data.js')
print(f'已写出 app/words-data.js ({size/1024:.0f} KB)')
