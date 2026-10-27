// 配方 v1（验证日期 2026-10-25）：标记指定 AI 质检的 Agent 结果（正常/异常），并可同时填写异议备注。
// 仅在完成态使用（先经 platform-check-result.js 确认 running=false 且结论已更新）；异常仅在本次真实报错时选择。
(() => {
const DATA = {
  stage: 'question',            // question=题目难度&标签辅助判断 | criteria=考点质检 | attainment=达成性判断
  result: '正常',               // 正常 | 异常
  objectionNote: '',            // 可选：不认同不通过结论时的备注（≤1000字）；留空跳过
};
try {
  const host = document.querySelector('div[id^="garfish_app_for_vibe-coding"]');
  if (!host || !host.shadowRoot) return JSON.stringify({ok: false, error: 'shadow host not found'});
  const root = host.shadowRoot;
  const HEADINGS = {question: '题目难度&标签辅助判断', criteria: '考点质检', attainment: '达成性判断'};
  const RUNNAMES = {question: '运行辅助判断', criteria: '运行考点质检', attainment: '运行达成性判断'};
  let section = null;
  root.querySelectorAll('h4').forEach(el => {
    if (!section && (el.textContent || '').trim() === HEADINGS[DATA.stage]) {
      let node = el;
      for (let i = 0; i < 8 && node; i++) {
        node = node.parentElement;
        if (node) {
          const buttons = node.querySelectorAll('button');
          for (const b of buttons) {
            if ((b.textContent || '').replace(/\s+/g, '').startsWith(RUNNAMES[DATA.stage])) { section = node; break; }
          }
        }
        if (section) break;
      }
    }
  });
  if (!section) return JSON.stringify({ok: false, error: 'section not found: ' + HEADINGS[DATA.stage]});
  const report = {ok: true};
  // 1) 选择 正常/异常（label 承接点击；界面在调用次数≥2 后才渲染，缺失时如实报告）
  try {
    let label = null;
    section.querySelectorAll('label').forEach(el => {
      if (!label && (el.textContent || '').trim() === DATA.result) label = el;
    });
    if (!label) { report.result = 'not_present（正常/异常界面尚未出现，通常需调用≥2次）'; }
    else {
      label.click();
      const input = label.querySelector('input[type="radio"]');
      report.result = (input && input.checked) ? 'ok' : 'needs_manual';
    }
  } catch (e) { report.result = 'needs_manual'; }
  // 2) 异议备注（可选）
  if (DATA.objectionNote) {
    try {
      let box = null;
      section.querySelectorAll('textarea').forEach(t => { if (!box && (t.placeholder || '').startsWith('如果不认同辅标结果为不通过')) box = t; });
      if (!box) { report.objectionNote = 'needs_manual'; }
      else {
        const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        setter.call(box, DATA.objectionNote);
        box.dispatchEvent(new Event('input', {bubbles: true}));
        box.dispatchEvent(new Event('change', {bubbles: true}));
        report.objectionNote = box.value === DATA.objectionNote ? 'ok' : 'needs_manual';
      }
    } catch (e) { report.objectionNote = 'needs_manual'; }
  }
  if (Object.values(report).some(v => v === 'needs_manual')) report.ok = false;
  return JSON.stringify(report);} catch (e) { return JSON.stringify({ok: false, error: String(e)}); } })()
