// 配方 v1（验证日期 2026-10-24）：一次性填写做题平台"出题内容"区块。
// 用前替换 DATA 四个字段；整段作为 evaluate 表达式脚本执行（同步 <3s，DATA 须在 IIFE 内——evaluate 按表达式求值）。
// 返回 JSON：各字段 ok / needs_manual；needs_manual 项按手册 §2.3–§2.4 真实点击补齐。
(() => {
const DATA = {
  questionType: '分析决策',      // 三选一：开放推荐 | 分析决策 | How-to
  domain: '生活娱乐',           // 领域下拉的选项文本
  prompt: '<题目Prompt全文>',
  insight: '<出题说明Insight全文>',
};
try {
  const host = document.querySelector('div[id^="garfish_app_for_vibe-coding"]');
  if (!host || !host.shadowRoot) return JSON.stringify({ok: false, error: 'shadow host not found'});
  const root = host.shadowRoot;
  const report = {ok: true};
  const mouse = (el, type) => el.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
  const key = (el, k) => el.dispatchEvent(new KeyboardEvent('keydown', {key: k, bubbles: true, cancelable: true}));
  const readSelect = (sel) => { const item = sel.querySelector('.ant-select-selection-item'); return item ? item.textContent.trim() : null; };

  // 1) 题目类型：点击标签文本（单选 input 为隐藏，label 承接点击）
  try {
    let clicked = false;
    root.querySelectorAll('label, span').forEach(el => {
      if (!clicked && el.children.length === 0 && (el.textContent || '').trim() === DATA.questionType) {
        const label = el.closest('label'); if (label) { label.click(); clicked = true; }
      }
    });
    let checked = false;
    root.querySelectorAll('input[type="radio"]').forEach(r => { if (r.checked && r.closest('label') && (r.closest('label').textContent || '').trim() === DATA.questionType) checked = true; });
    report.questionType = checked ? 'ok' : 'needs_manual';
  } catch (e) { report.questionType = 'needs_manual'; }

  // 2) 题目领域：antd Select 经 React fiber 直调 onChange（合成事件不可靠；实测 onChange 直调立即生效）
  try {
    const VALUES = {'法律':'law','教育':'education','计算机与数理科学':'computerAndMathematicalSciences',
      '理工科（非计算机/数理）':'engineeringAndScience','人文社科':'humanitiesAndSocialSciences',
      '商科':'business','医疗':'medical','生活娱乐':'lifestyleHobbies'};
    let target = null;
    root.querySelectorAll('.ant-select').forEach(sel => {
      const ph = sel.querySelector('.ant-select-selection-placeholder');
      if (!target && ph && (ph.textContent || '').trim() === '请选择题目领域') target = sel;
    });
    if (!target) {
      root.querySelectorAll('.ant-select').forEach(sel => {
        const cur = readSelect(sel);
        if (!target && cur && Object.values(VALUES).length && ['法律','教育','计算机与数理科学','理工科（非计算机/数理）','人文社科','商科','医疗','生活娱乐'].includes(cur)) target = sel;
      });
    }
    if (!target) { report.domain = 'needs_manual'; }
    else if (readSelect(target) === DATA.domain) { report.domain = 'ok'; }
    else {
      const value = VALUES[DATA.domain];
      const fiberKey = Object.keys(target).find(k => k.startsWith('__reactFiber$'));
      let node = fiberKey ? target[fiberKey] : null, handler = null;
      for (let i = 0; i < 10 && node && !handler; i++) {
        if (typeof (node.memoizedProps || {}).onChange === 'function') { handler = node.memoizedProps.onChange; break; }
        node = node.return;
      }
      if (!handler || !value) { report.domain = 'needs_manual'; }
      else {
        handler(value, {value: value, label: DATA.domain});
        report.domain = readSelect(target) === DATA.domain ? 'ok' : 'needs_manual';
      }
    }
  } catch (e) { report.domain = 'needs_manual'; }

  // 3/4) 文本域：placeholder 定位 + 原生 setter 触发 React 受控更新
  const fillTextarea = (placeholder, value, name) => {
    try {
      let box = null;
      root.querySelectorAll('textarea').forEach(t => { if (!box && (t.placeholder || '') === placeholder) box = t; });
      if (!box) { report[name] = 'needs_manual'; return; }
      box.scrollIntoView({block: 'center'});
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(box, value);
      box.dispatchEvent(new Event('input', {bubbles: true}));
      box.dispatchEvent(new Event('change', {bubbles: true}));
      report[name] = box.value === value ? 'ok' : 'needs_manual';
    } catch (e) { report[name] = 'needs_manual'; }
  };
  fillTextarea('请编写本次出题任务的题目Prompt', DATA.prompt, 'prompt');
  fillTextarea('请填写本题的出题说明（关键洞察insight）', DATA.insight, 'insight');

  if (Object.values(report).some(v => v !== 'ok' && v !== true)) report.ok = false;
  return JSON.stringify(report);
} catch (e) { return JSON.stringify({ok: false, error: String(e)}); } })()
