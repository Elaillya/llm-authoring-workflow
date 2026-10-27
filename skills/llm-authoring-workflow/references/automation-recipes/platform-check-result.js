// 配方 v1（验证日期 2026-10-25）：读取指定 AI 质检区块的三态状态（供轮询与完成判定，只读无副作用）。
// 返回 running（按钮 loading 中）、conclusion（通过/不通过/暂无）、calls、agentResult（正常/异常/未选）、objectionNoteLen。
// 判定规则见手册 §2.6：running=true 时不读结论不选异常；仅 running=false 且 conclusion 更新后才是本次结果。
(() => {
const DATA = { stage: 'question' };   // question=题目难度&标签辅助判断 | criteria=考点质检 | attainment=达成性判断
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
  let runBtn = null;
  section.querySelectorAll('button').forEach(b => {
    const name = (b.textContent || '').replace(/\s+/g, '');
    if (!runBtn && name.startsWith(RUNNAMES[DATA.stage])) runBtn = b;
  });
  const running = runBtn ? (runBtn.classList.contains('ant-btn-loading') || !!runBtn.querySelector('img[alt="loading"], .anticon-loading') || runBtn.disabled) : null;
  const text = (section.textContent || '');
  const cm = text.match(/题目AI质检结论\s*(通过|不通过|暂无)/);
  const calls = (text.match(/Agent 已调用\s*(\d+)\s*次/) || [])[1] || null;
  let agentResult = null;
  section.querySelectorAll('input[type="radio"]').forEach(r => {
    const label = r.closest('label');
    if (r.checked && label && ['正常', '异常'].includes((label.textContent || '').trim())) agentResult = (label.textContent || '').trim();
  });
  let objectionNoteLen = 0;
  section.querySelectorAll('textarea').forEach(t => {
    if ((t.placeholder || '').startsWith('如果不认同辅标结果为不通过')) objectionNoteLen = (t.value || '').length;
  });
  return JSON.stringify({ok: true, stage: DATA.stage, running: running, resultAreaPresent: text.includes('题目AI质检结论'), conclusion: cm ? cm[1] : null, calls: calls, agentResult: agentResult, objectionNoteLen: objectionNoteLen});
} catch (e) { return JSON.stringify({ok: false, error: String(e)}); } })()
