# -*- coding: utf-8 -*-
"""把 words.json 切成批次文件, 供子代理生成词根词缀拆解与情景例句"""
import json, os

words = json.load(open('data/words.json', encoding='utf-8'))
os.makedirs('data/gen/in', exist_ok=True)
os.makedirs('data/gen/out', exist_ok=True)
# 清空旧的批次文件
for d in ('data/gen/in', 'data/gen/out'):
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

BATCH = 200
n = 0
for i in range(0, len(words), BATCH):
    chunk = words[i:i+BATCH]
    n += 1
    entries = [{'w': c['w'], 't': c['t'], 'ex': c['ex']} for c in chunk]
    json.dump(entries, open(f'data/gen/in/batch_{n:02d}.json', 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
print(f'{len(words)} 词 -> {n} 个批次 (每批{BATCH}词)')
