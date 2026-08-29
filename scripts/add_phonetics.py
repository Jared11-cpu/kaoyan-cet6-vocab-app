# -*- coding: utf-8 -*-
"""为 words.json 补美音音标(ph字段): CMUdict(ARPAbet) -> IPA
查找顺序: 直接命中 -> 英式拼写变体 -> 美式拼写映射表 -> 手工IPA
用法: python scripts/add_phonetics.py
"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ---------- ARPAbet -> IPA (美音, 不标长音符) ----------
VOWELS = {
    'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'aʊ', 'AY': 'aɪ',
    'EH': 'ɛ', 'ER': 'ɝ', 'EY': 'eɪ', 'IH': 'ɪ', 'IY': 'i',
    'OW': 'oʊ', 'OY': 'ɔɪ', 'UH': 'ʊ', 'UW': 'u',
}
CONS = {
    'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'F': 'f', 'G': 'ɡ', 'HH': 'h',
    'JH': 'dʒ', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ', 'P': 'p',
    'R': 'r', 'S': 's', 'SH': 'ʃ', 'T': 't', 'TH': 'θ', 'V': 'v', 'W': 'w',
    'Y': 'j', 'Z': 'z', 'ZH': 'ʒ',
}

# 英语合法音节开头辅音簇(IPA符号组), 用于重音符定位
VALID_ONSETS = {
    ('p', 'l'), ('p', 'r'), ('p', 'j'), ('t', 'w'), ('t', 'r'), ('t', 'j'),
    ('k', 'l'), ('k', 'r'), ('k', 'w'), ('k', 'j'), ('b', 'l'), ('b', 'r'), ('b', 'j'),
    ('d', 'w'), ('d', 'r'), ('d', 'j'), ('g', 'l'), ('g', 'r'), ('g', 'j'),
    ('f', 'l'), ('f', 'r'), ('f', 'j'), ('s', 'l'), ('s', 'w'), ('s', 'j'),
    ('s', 'm'), ('s', 'n'), ('s', 'p'), ('s', 't'), ('s', 'k'), ('s', 'f'),
    ('ʃ', 'r'), ('θ', 'r'), ('θ', 'w'), ('θ', 'j'), ('m', 'j'), ('n', 'j'),
    ('l', 'j'), ('v', 'j'), ('h', 'j'),
    ('s', 'p', 'r'), ('s', 't', 'r'), ('s', 'k', 'r'), ('s', 'p', 'l'),
    ('s', 'k', 'w'), ('s', 'p', 'j'), ('s', 't', 'j'), ('s', 'k', 'j'),
}

def onset_len(cluster):
    """辅音簇末尾有多少个属于重读元音所在音节的开头(最大音节开头原则)"""
    if len(cluster) >= 3 and tuple(cluster[-3:]) in VALID_ONSETS:
        return 3
    if len(cluster) >= 2 and tuple(cluster[-2:]) in VALID_ONSETS:
        return 2
    return min(1, len(cluster))

def to_ipa(phones):
    """ARPAbet音素序列 -> IPA; 重音符按音节开头定位"""
    toks = []  # [符号, 是否元音, 重读'1'/'2'/None]
    for p in phones:
        m = re.match(r'^([A-Z]+?)([012])?$', p)
        if not m:
            return None
        base, stress = m.group(1), m.group(2)
        if base in VOWELS:
            if base == 'AH' and stress == '0':
                sym = 'ə'
            elif base == 'ER' and stress == '0':
                sym = 'ər'
            else:
                sym = VOWELS[base]
            toks.append([sym, True, stress if stress in '12' else None])
        elif base in CONS:
            toks.append([CONS[base], False, None])
        else:
            return None
    out = []
    for i, (sym, isv, stress) in enumerate(toks):
        if isv and stress:
            # 收集该元音之前的辅音串
            cluster = []
            j = i - 1
            while j >= 0 and not toks[j][1]:
                cluster.insert(0, toks[j][0])
                j -= 1
            if j < 0:
                keep = len(cluster)          # 词首: 整簇即开头
            else:
                keep = onset_len(cluster)    # 取音节开头部分
            for _ in range(len(cluster)):    # 弹出主循环已追加的辅音
                out.pop()
            split = len(cluster) - keep
            out.extend([[c, False, None] for c in cluster[:split]])
            out.append(['ˈ' if stress == '1' else 'ˌ', False, None])
            out.extend([[c, False, None] for c in cluster[split:]])
        out.append([sym, isv, None])
    return ''.join(t[0] for t in out)

# ---------- 英式 -> 美式拼写变体 ----------
def spelling_variants(w):
    vs = [w]
    for a, b in [('isation', 'ization'), ('ise', 'ize'), ('yse', 'yze'),
                 ('our', 'or'), ('ence', 'ense'), ('ll', 'l'),
                 ('ae', 'e'), ('oe', 'e'), ('ogue', 'og')]:
        v = vs[-1].replace(a, b)
        if v != vs[-1]:
            vs.append(v)
    vs.append(re.sub(r're$', 'er', w))  # litre->liter, centre->center
    return vs

# 英式词 -> cmudict里的美式拼写
US_MAP = {
    'aeroplane': 'airplane', 'appal': 'appall', 'artefact': 'artifact',
    'cigaret': 'cigarette', 'dependant': 'dependent', 'despatch': 'dispatch',
    'enrol': 'enroll', 'gaol': 'jail', 'instalment': 'installment',
    'jewellery': 'jewelry', 'pyjamas': 'pajamas', 'sceptical': 'skeptical',
    'skilful': 'skillful', 'waggon': 'wagon', 'manoeuvre': 'maneuver',
}

# cmudict查不到/新词, 手工美音IPA
MANUAL_IPA = {
    'aspirational': 'ˌæspəˈreɪʃənl', 'coronavirus': 'kəˈroʊnəˌvaɪrəs',
    'destine': 'ˈdɛstɪn', 'entreat': 'ɪnˈtrit', 'faultless': 'ˈfɔltləs',
    'fearlessly': 'ˈfɪrləsli', 'gramophone': 'ˈɡræməfoʊn',
    'immersive': 'ɪˈmɜrsɪv', 'motorway': 'ˈmoʊtərweɪ', 'nought': 'nɔt',
    'pedlar': 'ˈpɛdlər', 'preindustrial': 'ˌpriɪnˈʌstriəl',
    'preposition': 'ˌprɛpəˈzɪʃən', 'proximately': 'ˈprɑksəmətli',
    'regenerative': 'rɪˈdʒɛnərətɪv', 'southwards': 'ˈsaʊθwərdz',
    'subscript': 'ˈsʌbskrɪpt', 'tradesman': 'ˈtreɪdzmən',
    'untiring': 'ʌnˈtaɪrɪŋ', 'up-to-date': 'ˌʌptəˈdeɪt', 'workpiece': 'ˈwɜrkpis',
}

def main():
    cmu = {}
    for line in open('data/cmudict.dict', encoding='utf-8'):
        parts = line.strip().split(' ', 1)
        if len(parts) < 2:
            continue
        w = re.sub(r'\(\d+\)$', '', parts[0]).lower()
        if w not in cmu:
            cmu[w] = parts[1].split()

    words = json.load(open('data/words.json', encoding='utf-8'))
    hit = variant = manual = miss = 0
    missing = []
    for w in words:
        key = w['w'].lower()
        src = None
        if key in cmu:
            src = key; hit += 1
        elif key in US_MAP and US_MAP[key] in cmu:
            src = US_MAP[key]; variant += 1
        else:
            v = next((x for x in spelling_variants(key) if x in cmu), None)
            if v:
                src = v; variant += 1
        if src:
            w['ph'] = to_ipa(cmu[src])
            if not w['ph']:
                missing.append(key); miss += 1
        elif key in MANUAL_IPA:
            w['ph'] = MANUAL_IPA[key]; manual += 1
        else:
            missing.append(key); miss += 1
    print(f'词库 {len(words)} | 直接命中 {hit} | 拼写变体 {variant} | 手工 {manual} | 缺失 {miss}')
    if missing:
        print('缺失:', missing[:30])
    empty = [w['w'] for w in words if not w.get('ph')]
    print('空音标词数:', len(empty), empty[:10])
    if miss == 0 and not empty:
        with open('data/words.json', 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, separators=(',', ':'))
        print('已写回 data/words.json')
    else:
        print('!! 有缺失, 未写回')

if __name__ == '__main__':
    main()
