// 配方 v1（验证日期 2026-10-24）：一次性填写做题平台某个模型区块（Markdown 回复 / 达成判断 / 达成性备注）。
// 用前替换 DATA 四个字段；整段作为 evaluate 表达式脚本执行（同步 <3s，DATA 须在 IIFE 内——evaluate 按表达式求值）。
// 返回 JSON：各字段 ok / needs_manual；达成下拉失败时按手册 §2.9 键盘法补齐。
(() => {
const DATA = {
  modelLabel: '豆包 turbo 2.1',   // 区块标题精确文本：豆包 turbo 2.1 | GPT-5.6-sol（中/Medium及以上推理） | Claude opus 4.6（Medium及以上推理）
  reply: '<该模型完整 Markdown 回复>',
  attainment: '未达成',           // 达成 | 未达成
  note: '<逐考点达成性备注全文>',
};
try {
  const host = document.querySelector('div[id^="garfish_app_for_vibe-coding"]');
  if (!host || !host.shadowRoot) return JSON.stringify({ok: false, error: 'shadow host not found'});
  const root = host.shadowRoot;
  const report = {ok: true};

  // 1) 定位模型区块：从标题文本向上找到一个同时包含"Markdown 回复"与"决定性核心考点是否达成"的容器
  let section = null;
  root.querySelectorAll('*').forEach(el => {
    if (!section && el.children.length === 0 && (el.textContent || '').trim() === DATA.modelLabel) {
      let node = el;
      for (let i = 0; i < 10 && node; i++) {
        node = node.parentElement;
        const t = node ? (node.textContent || '') : '';
        if (t.includes('Markdown 回复') && t.includes('决定性核心考点是否达成') && t.includes('回复截图')) { section = node; break; }
        if (t.includes('出题内容')) break; // 爬过头则放弃
      }
    }
  });
  if (!section) return JSON.stringify({ok: false, error: 'model section not found: ' + DATA.modelLabel});

  const mouse = (el, type) => el.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
  const key = (el, k) => el.dispatchEvent(new KeyboardEvent('keydown', {key: k, bubbles: true, cancelable: true}));
  const readSelect = (sel) => { const item = sel.querySelector('.ant-select-selection-item'); return item ? item.textContent.trim() : null; };

  // 2) 回复与备注文本域（placeholder 定位 + 原生 setter）
  const fillTextarea = (placeholder, value, name) => {
    try {
      let box = null;
      section.querySelectorAll('textarea').forEach(t => { if (!box && (t.placeholder || '').includes(placeholder)) box = t; });
      if (!box) { report[name] = 'needs_manual'; return; }
      box.scrollIntoView({block: 'center'});
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(box, value);
      box.dispatchEvent(new Event('input', {bubbles: true}));
      box.dispatchEvent(new Event('change', {bubbles: true}));
      report[name] = box.value === value ? 'ok' : 'needs_manual';
    } catch (e) { report[name] = 'needs_manual'; }
  };
  fillTextarea('的 Markdown 回复', DATA.reply, 'reply');
  fillTextarea('请说明达成或未达成的依据', DATA.note, 'note');

  // 3) 达成判断下拉（React fiber 直调 onChange；合成事件不可靠）
  try {
    const VALUES = {'达成': 'achieved', '未达成': 'notAchieved'};
    const sel = section.querySelector('.ant-select');
    if (!sel) { report.attainment = 'needs_manual'; }
    else if (readSelect(sel) === DATA.attainment) { report.attainment = 'ok'; }
    else {
      const value = VALUES[DATA.attainment];
      const fiberKey = Object.keys(sel).find(k => k.startsWith('__reactFiber$'));
      let node = fiberKey ? sel[fiberKey] : null, handler = null;
      for (let i = 0; i < 10 && node && !handler; i++) {
        if (typeof (node.memoizedProps || {}).onChange === 'function') { handler = node.memoizedProps.onChange; break; }
        node = node.return;
      }
      if (!handler || !value) { report.attainment = 'needs_manual'; }
      else {
        handler(value, {value: value, label: DATA.attainment});
        report.attainment = readSelect(sel) === DATA.attainment ? 'ok' : 'needs_manual';
      }
    }
  } catch (e) { report.attainment = 'needs_manual'; }

  if (Object.values(report).some(v => v !== 'ok' && v !== true)) report.ok = false;
  return JSON.stringify(report);
} catch (e) { return JSON.stringify({ok: false, error: String(e)}); } })()
