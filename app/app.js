/* 背单词 App 核心逻辑: SM-2 间隔重复 + localStorage 持久化 */
'use strict';

/* ================= 数据 ================= */
// WORDS 由 words-data.js 提供: [{w,t,ky,c6,kyF,c6F,imp,bs,ex,r,c}]

const STORE_KEY = 'vocabApp.v1';
const TAG_NAMES = { 3: '双重点', 2: '考研重点', 1: '六级重点', 0: '普通词' };

const state = loadState();
let studyQueue = [];      // 本次学习队列: {word, isNew}
let studyIndex = 0;
let studyTotal = 0;

/* ================= 状态管理 ================= */
function defaultState() {
  return {
    settings: { daily: 20, scope: 'key', basic: false },
    progress: {},          // w -> {ef, ivl, reps, due(ts)}
    daily: { date: today(), newDone: 0, revDone: 0 },
    streak: { last: '', count: 0 },
  };
}
function today() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const s = JSON.parse(raw);
      const def = defaultState();
      return {
        settings: Object.assign(def.settings, s.settings || {}),
        progress: s.progress || {},
        daily: s.daily || def.daily,
        streak: s.streak || def.streak,
      };
    }
  } catch (e) { /* 损坏则重建 */ }
  return defaultState();
}
function saveState() { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }

function rollDaily() {
  const t = today();
  if (state.daily.date !== t) {
    state.daily = { date: t, newDone: 0, revDone: 0 };
    saveState();
  }
}

/* ================= 词表工具 ================= */
// 学习顺序: 重点等级降序 -> 综合词频降序
const STUDY_ORDER = WORDS.slice().sort((a, b) =>
  (b.imp - a.imp) || ((b.kyF + b.c6F) - (a.kyF + a.c6F)));
const WORD_MAP = {};
WORDS.forEach(w => { WORD_MAP[w.w] = w; });

function eligibleNewWords() {
  return STUDY_ORDER.filter(w => {
    if (state.progress[w.w]) return false;
    if (!state.settings.basic && w.bs) return false;
    if (state.settings.scope === 'key' && w.imp === 0) return false;
    return true;
  });
}
function dueReviews(now) {
  const list = [];
  for (const w in state.progress) {
    const p = state.progress[w];
    if (p.due <= now && WORD_MAP[w]) list.push({ word: WORD_MAP[w], isNew: false });
  }
  list.sort((a, b) => (b.word.imp - a.word.imp) || (b.word.kyF - a.word.kyF)); // 重点词优先复习
  return list;
}

/* ================= SM-2 调度 ================= */
// q: 2=忘了 3=模糊 4=认识
function schedule(word, q) {
  let p = state.progress[word.w] || { ef: 2.5, ivl: 0, reps: 0, due: 0 };
  let ef = p.ef, ivl = p.ivl, reps = p.reps;
  if (q < 3) {
    ef = Math.max(1.3, ef - 0.2);
    ivl = 0; reps = 0;
  } else {
    ef = Math.max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
    if (q === 3) {
      ivl = reps === 0 ? 1 : Math.max(1, Math.round(ivl * 0.6));
    } else {
      ivl = reps === 0 ? 1 : reps === 1 ? 6 : Math.round(ivl * ef);
    }
    reps += 1;
  }
  const due = ivl === 0 ? Date.now() : Date.now() + ivl * 86400000;
  state.progress[word.w] = { ef: Math.round(ef * 100) / 100, ivl, reps, due };
  saveState();
  return ivl === 0; // 返回是否需要当场重现
}

/* ================= 页面路由 ================= */
function nav(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('scr-' + name).classList.add('active');
  if (name === 'home') renderHome();
  if (name === 'stats') renderStats();
  if (name === 'settings') renderSettings();
}
document.querySelectorAll('[data-nav]').forEach(btn =>
  btn.addEventListener('click', () => nav(btn.dataset.nav)));

let toastTimer = null;
function toast(msg) {
  let el = document.querySelector('.toast');
  if (!el) { el = document.createElement('div'); el.className = 'toast'; document.body.appendChild(el); }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2200);
}

/* ================= 首页 ================= */
function renderHome() {
  rollDaily();
  const now = Date.now();
  const reviews = dueReviews(now);
  const dailyLeft = Math.max(0, state.settings.daily - state.daily.newDone);
  const news = eligibleNewWords().slice(0, dailyLeft);
  document.getElementById('home-date').textContent =
    new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' });
  document.getElementById('home-new').textContent = news.length;
  document.getElementById('home-review').textContent = reviews.length;
  document.getElementById('home-done').textContent =
    '已完成 新词 ' + state.daily.newDone + ' · 复习 ' + state.daily.revDone;
  const startBtn = document.getElementById('btn-start');
  const total = news.length + reviews.length;
  startBtn.disabled = total === 0;
  startBtn.textContent = total === 0 ? '今日已完成' : '开始学习';
  const scopeTxt = state.settings.scope === 'key' ? '重点词优先' : '全部词汇';
  document.getElementById('home-range').textContent =
    '范围: ' + scopeTxt + (state.settings.basic ? ' · 含基础词' : '') + ' · 每日新词 ' + state.settings.daily;
  const learned = Object.keys(state.progress).length;
  const mastered = Object.values(state.progress).filter(p => p.reps >= 3 && p.ivl >= 21).length;
  document.getElementById('home-overall').textContent =
    '已学 ' + learned + ' 词 · 已掌握 ' + mastered + ' 词 · 连续 ' + state.streak.count + ' 天';
}

/* ================= 学习流程 ================= */
document.getElementById('btn-start').addEventListener('click', startStudy);
document.getElementById('btn-exit').addEventListener('click', () => { studyQueue = []; nav('home'); });

function startStudy() {
  rollDaily();
  const now = Date.now();
  const reviews = dueReviews(now);
  const dailyLeft = Math.max(0, state.settings.daily - state.daily.newDone);
  const news = eligibleNewWords().slice(0, dailyLeft).map(w => ({ word: w, isNew: true }));
  studyQueue = reviews.concat(news);   // 复习优先
  if (studyQueue.length === 0) { toast('今日任务已完成'); return; }
  studyIndex = 0;
  studyTotal = studyQueue.length;
  nav('study');
  showCard();
}

function showCard() {
  if (studyIndex >= studyQueue.length) { finishStudy(); return; }
  const { word, isNew } = studyQueue[studyIndex];
  document.getElementById('study-progress').textContent = (studyIndex + 1) + ' / ' + studyQueue.length;
  document.getElementById('study-type').textContent = isNew ? '新词' : '复习';
  document.getElementById('study-bar').style.width = (studyIndex / studyQueue.length * 100) + '%';

  // 正面
  const tags = document.getElementById('word-tags');
  tags.innerHTML = '';
  const tag = document.createElement('span');
  tag.className = 'tag tag-' + word.imp;
  tag.textContent = TAG_NAMES[word.imp];
  tags.appendChild(tag);
  if (word.bs) { const b = document.createElement('span'); b.className = 'tag tag-basic'; b.textContent = '基础词'; tags.appendChild(b); }
  document.getElementById('word-text').textContent = word.w;
  document.getElementById('word-freq').textContent =
    (word.ky ? '考研词频 ' + word.kyF : '') + (word.ky && word.c6 ? ' · ' : '') + (word.c6 ? '六级词频 ' + word.c6F : '');

  // 背面
  document.getElementById('word-text2').textContent = word.w;
  document.getElementById('word-def').textContent = word.t || '';
  document.getElementById('word-root').textContent = word.r || '（暂无拆解）';
  const exampleEl = document.getElementById('word-example');
  const exampleZhEl = document.getElementById('word-example-zh');
  if (word.c && word.c.length === 2) {
    exampleEl.textContent = word.c[0];
    exampleZhEl.textContent = word.c[1];
  } else if (word.ex) {
    exampleEl.textContent = word.ex + '（六级真题）';
    exampleZhEl.textContent = '';
  } else {
    exampleEl.textContent = '（暂无例句）';
    exampleZhEl.textContent = '';
  }

  // 先显示正面
  document.getElementById('card-front').style.display = 'flex';
  document.getElementById('card-back').style.display = 'none';
  document.getElementById('reveal-bar').classList.add('show');
  document.getElementById('answer-bar').classList.remove('show');
}

document.getElementById('btn-reveal').addEventListener('click', reveal);
document.getElementById('card-front').addEventListener('click', reveal);

function reveal() {
  document.getElementById('card-front').style.display = 'none';
  document.getElementById('card-back').style.display = 'flex';
  document.getElementById('reveal-bar').classList.remove('show');
  document.getElementById('answer-bar').classList.add('show');
}

document.getElementById('btn-forgot').addEventListener('click', () => answer(2));
document.getElementById('btn-fuzzy').addEventListener('click', () => answer(3));
document.getElementById('btn-know').addEventListener('click', () => answer(4));

function answer(q) {
  const { word, isNew } = studyQueue[studyIndex];
  const requeue = schedule(word, q);
  // 连续天数
  const t = today();
  if (state.streak.last !== t) {
    const yest = new Date(Date.now() - 86400000);
    const ys = yest.getFullYear() + '-' + String(yest.getMonth() + 1).padStart(2, '0') + '-' + String(yest.getDate()).padStart(2, '0');
    state.streak.count = state.streak.last === ys ? state.streak.count + 1 : 1;
    state.streak.last = t;
  }
  if (isNew) state.daily.newDone += 1; else state.daily.revDone += 1;
  saveState();
  studyIndex += 1;
  if (requeue) studyQueue.push({ word, isNew: false }); // 忘了: 当场重现
  showCard();
}

function finishStudy() {
  studyQueue = [];
  nav('home');
  toast('今日任务完成 🎉');
}

/* ================= 设置页 ================= */
function renderSettings() {
  document.getElementById('set-daily').textContent = state.settings.daily;
  document.querySelectorAll('.step-btn').forEach(b => b.addEventListener('click', () => {
    state.settings.daily = Math.min(200, Math.max(5, state.settings.daily + parseInt(b.dataset.step)));
    saveState(); renderSettings();
  }));
  document.querySelectorAll('.seg-btn').forEach(b => b.addEventListener('click', () => {
    state.settings.scope = b.dataset.scope; saveState(); renderSettings();
  }));
  const tog = document.getElementById('set-basic');
  tog.classList.toggle('on', state.settings.basic);
}
document.getElementById('set-basic').addEventListener('click', () => {
  state.settings.basic = !state.settings.basic;
  saveState(); renderSettings();
});

document.getElementById('btn-export').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(state)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'vocab-progress-' + today() + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('已导出学习记录');
});
document.getElementById('btn-import').addEventListener('click', () => {
  document.getElementById('import-file').click();
});
document.getElementById('import-file').addEventListener('change', ev => {
  const f = ev.target.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const s = JSON.parse(reader.result);
      if (!s.progress || !s.settings) throw new Error('bad');
      localStorage.setItem(STORE_KEY, JSON.stringify(s));
      location.reload();
    } catch (e) { toast('文件格式不正确'); }
  };
  reader.readAsText(f);
  ev.target.value = '';
});
document.getElementById('btn-reset').addEventListener('click', () => {
  if (confirm('确定清空全部学习记录? 此操作不可恢复')) {
    localStorage.removeItem(STORE_KEY);
    location.reload();
  }
});

/* ================= 统计页 ================= */
function renderStats() {
  const ps = Object.values(state.progress);
  const learned = ps.length;
  const mastered = ps.filter(p => p.reps >= 3 && p.ivl >= 21).length;
  document.getElementById('st-learned').textContent = learned;
  document.getElementById('st-reviewing').textContent = learned - mastered;
  document.getElementById('st-mastered').textContent = mastered;
  document.getElementById('st-streak').textContent = state.streak.count;
  document.getElementById('st-total').textContent = WORDS.length;
  document.getElementById('st-today').textContent = state.daily.newDone + state.daily.revDone;

  // 词库构成
  const c = { 3: 0, 2: 0, 1: 0, 0: 0 };
  WORDS.forEach(w => { c[w.imp] += 1; });
  document.getElementById('st-breakdown').innerHTML =
    '词库构成<br>双重点 ' + c[3] + ' 词（考研+六级真题双高频）<br>' +
    '考研重点 ' + c[2] + ' 词（考研真题高频）<br>' +
    '六级重点 ' + c[1] + ' 词（六级真题高频）<br>' +
    '普通词 ' + c[0] + ' 词';
}

/* 查词 */
const searchInput = document.getElementById('search-input');
searchInput.addEventListener('input', () => {
  const q = searchInput.value.trim().toLowerCase();
  const box = document.getElementById('search-result');
  if (!q) { box.innerHTML = ''; return; }
  const hits = WORDS.filter(w => w.w.startsWith(q) || w.w.includes(q)).slice(0, 8);
  box.innerHTML = hits.map(w =>
    '<div class="sr-item"><div class="sr-word">' + w.w +
    ' <span class="tag tag-' + w.imp + '" style="font-size:10px">' + TAG_NAMES[w.imp] + '</span></div>' +
    '<div class="sr-def">' + (w.t || '') + '</div>' +
    '<div class="sr-root">' + (w.r || '') + '</div></div>'
  ).join('') || '<div class="sr-item sr-def">未找到</div>';
});

/* ================= 启动 ================= */
rollDaily();
nav('home');
