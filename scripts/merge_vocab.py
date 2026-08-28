# -*- coding: utf-8 -*-
"""合并考研(NETEM)与六级词库，生成统一词库 words.json

数据源:
- netem_full_list.json      考研5530大纲词 + 真题词频 + 人工校对释义 (exam-data/NETEMVocabulary, CC BY-NC-SA)
- cet6_high_frequency_words.csv  2020-2025六级35套真题词频 + 真题例句 (wangjiuyi543-ui/cet6-vocabulary, MIT)
- cet6_words_kylebing.txt   六级词表(词性+中文释义) (KyleBing/english-vocabulary)
- junior/senior_words.txt   初中/高中基础词表, 用于过滤过于简单的词

标注逻辑(资深出题人视角):
- 考研重点: 考研真题词频>=40 (NETEM官方口径: 平均每5套卷遇到一次, 即真正高频词)
- 六级重点: 六级真题词频>=5  (35套卷中出现>=5次, 约每7套遇到一次)
- 双重点: 两者都满足
- basic: 初中基础词, 默认不进入学习队列(太简单), 可在设置中开启
"""
import json, csv, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

KY_FREQ_TH = 40   # 考研重点阈值(NETEM官方)
C6_FREQ_TH = 5    # 六级重点阈值

# ---------- 1. 考研词库 ----------
netem = json.load(open('data/netem_full_list.json', encoding='utf-8'))['5530考研词汇词频排序表']
ky = {}
for w in netem:
    word = (w['单词'] or '').strip().lower()
    if not word:
        continue
    ky[word] = {
        'def': (w['释义'] or '').strip(),
        'freq': int(w['词频'] or 0),
        'cat': w.get('分类') or '',
    }
print(f'考研大纲词: {len(ky)}')

# ---------- 2. 六级词表(带释义) ----------
cet6book = {}
for line in open('data/cet6_words_kylebing.txt', encoding='utf-8'):
    line = line.strip()
    if not line or '\t' not in line:
        continue
    parts = line.split('\t')
    word = parts[0].strip().lower()
    meaning = parts[1].strip() if len(parts) > 1 else ''
    if word:
        cet6book[word] = meaning
print(f'六级词表: {len(cet6book)}')

# ---------- 3. 六级真题词频+例句 ----------
cet6freq = {}
with open('data/cet6_high_frequency_words.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        word = (r['word'] or '').strip().lower()
        if not word:
            continue
        try:
            f6 = int(float(r['total_frequency'] or 0))
        except ValueError:
            f6 = 0
        ex = (r['example_sentence_from_exam'] or '').strip()
        # 清理例句中的换行
        ex = re.sub(r'\s+', ' ', ex)
        # 过滤低价值词(专有名词等)
        low = bool((r.get('filter_reason') or '').strip())
        cet6freq[word] = {'freq': f6, 'exam': ex, 'low': low}
print(f'六级真题词频表: {len(cet6freq)} (低价值标注 {sum(1 for v in cet6freq.values() if v["low"])})')

# ---------- 4. 基础词表 ----------
def load_basic(fn):
    words = set()
    for line in open(f'data/{fn}', encoding='utf-8'):
        line = line.strip()
        if not line or '\t' not in line:
            continue
        words.add(line.split('\t')[0].strip().lower())
    return words

junior = load_basic('junior_words.txt')
senior = load_basic('senior_words.txt')
print(f'初中词: {len(junior)} | 高中词: {len(senior)}')

# ---------- 5. 合并 ----------
# 词集 = 考研大纲 ∪ 六级词表 (真题词频表仅提供词频/例句, 不扩词, 避免词形还原残缺词干混入)
all_words = set(ky) | set(cet6book)
# 去掉带空格/连字符的短语的异常项、单字母
all_words = {w for w in all_words if re.fullmatch(r"[a-z][a-z'-]*", w)}
print(f'合并后总词数: {len(all_words)}')

out = []
for w in sorted(all_words):
    k = ky.get(w)
    c6f = cet6freq.get(w)
    is_cet6 = w in cet6book or (c6f is not None and not c6f['low'] and c6f['freq'] >= 2)
    # 释义: 考研释义优先(人工校对), 其次六级词表释义
    definition = ''
    if k and k['def']:
        definition = k['def']
    elif cet6book.get(w):
        definition = cet6book[w]
    # 考研重点 / 六级重点
    ky_key = bool(k and k['freq'] >= KY_FREQ_TH)
    c6_key = bool(is_cet6 and c6f and c6f['freq'] >= C6_FREQ_TH)
    basic = w in junior
    rec = {
        'w': w,
        't': definition,                       # 释义
        'ky': 1 if k else 0,                   # 属于考研大纲
        'c6': 1 if is_cet6 else 0,             # 属于六级范围
        'kyF': k['freq'] if k else 0,          # 考研真题词频
        'c6F': c6f['freq'] if c6f else 0,      # 六级真题词频
        'imp': (3 if (ky_key and c6_key) else 2 if ky_key else 1 if c6_key else 0),  # 重点等级: 3双重点 2考研重点 1六级重点 0普通
        'bs': 1 if basic else 0,               # 初中基础词
        'ex': c6f['exam'] if c6f and c6f['exam'] else '',  # 六级真题例句
    }
    if k and k['cat']:
        rec['cat'] = k['cat']
    out.append(rec)

# 缺释义的词统计
no_def = [r['w'] for r in out if not r['t']]
print(f'缺释义: {len(no_def)} -> {no_def[:20]}')

# ---------- 6. 统计 ----------
from collections import Counter
cnt = Counter(r['imp'] for r in out)
print(f'重点分布: 双重点(3)={cnt[3]} 考研重点(2)={cnt[2]} 六级重点(1)={cnt[1]} 普通(0)={cnt[0]}')
print(f'基础词: {sum(1 for r in out if r["bs"])}')
print(f'带真题例句: {sum(1 for r in out if r["ex"])}')
no_def_high = [r['w'] for r in out if not r['t'] and r['imp'] > 0]
print(f'重点词中缺释义: {len(no_def_high)} -> {no_def_high[:20]}')

json.dump(out, open('data/words.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'已写出 data/words.json ({len(out)} 词)')
