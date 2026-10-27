// 配方 v1（验证日期 2026-10-25）：点击运行一次平台 AI 质检并确认已进入调用中。
// DATA.stage 三选一；返回 clicked 与 loading 状态。等待结果用 platform-check-result.js 轮询（evaluate 有 3 秒上限，配方内不等待）。
(() => {
const DATA = { stage: 'question' };   // question=运行辅助判断 | criteria=运行考点质检 | attainment=运行达成性判断
try {
  const host = document.querySelector('div[id^="garfish_app_for_vibe-coding"]');
  if (!host || !host.shadowRoot) return JSON.stringify({ok: false, error: 'shadow host not found'});
  const root = host.shadowRoot;
  const NAMES = {question: '运行辅助判断', criteria: '运行考点质检', attainment: '运行达成性判断'};
  let btn = null;
  root.querySelectorAll('button').forEach(b => {
    const name = (b.textContent || '').replace(/\s+/g, '');
    if (!btn && name.startsWith(NAMES[DATA.stage])) btn = b;
  });
  if (!btn) return JSON.stringify({ok: false, error: 'run button not found: ' + NAMES[DATA.stage]});
  if (btn.classList.contains('ant-btn-loading') || btn.disabled) {
    return JSON.stringify({ok: true, clicked: false, loading: true, note: '已在调用中，勿重复点击'});
  }
  btn.scrollIntoView({block: 'center'});
  btn.click();
  const loading = btn.classList.contains('ant-btn-loading') || !!btn.querySelector('img[alt="loading"], .anticon-loading') || btn.disabled;
  return JSON.stringify({ok: true, clicked: true, loading: loading});
} catch (e) { return JSON.stringify({ok: false, error: String(e)}); } })()
