// ego Page adapter for the observed pi-web 0.12.2 chat DOM. No browser dependency.
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
import {sessionUrl, sha256} from './piweb-client.mjs';

const SCROLLER = '.chat-content .scrollbar-subtle.overflow-y-auto';
const fail = (ok, why) => { if (!ok) throw new Error(why); };

export function screenshotFilename(modelLabel) {
  fail(typeof modelLabel === 'string' && modelLabel.trim(), 'Model display name is required');
  let name = modelLabel.trim().replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').slice(0, 180).replace(/[. ]+$/, '');
  fail(name.length > 0, 'Invalid model display name');
  if (/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) name = '_'+name;
  return name+'.png';
}

// Old plans/receipts stay intact; expose a byte-identical, model-named upload copy.
async function namedScreenshot(receipt, outputDir, modelLabel) {
  const imageFile = path.join(outputDir, screenshotFilename(modelLabel));
  if (receipt.imageFile !== imageFile) {
    try { await fs.copyFile(receipt.imageFile, imageFile, fs.constants.COPYFILE_EXCL); }
    catch (e) { if (e.code !== 'EEXIST') throw e; }
    fail(sha256(await fs.readFile(imageFile)) === receipt.sha256, 'Model-named screenshot differs; preserve existing files');
  }
  return {...receipt, imageFile};
}

// Open the verified conversation and collapse thinking using normal UI before calling.
// Uses a fresh output directory; partial images remain evidence, never an uploadable plan.
export async function captureConversation(page, {baseUrl, sessionId, userEntryId, entryId, modelId, modelLabel = modelId,
  outputDir, maxSegments = 80, windowMs = 25000, onProgress = () => {}}) {
  fail(path.isAbsolute(outputDir), 'Use an absolute private output directory');
  fail(Number.isInteger(maxSegments) && maxSegments > 0 && windowMs > 0 && windowMs <= 30000, 'Invalid capture bounds');
  fail([userEntryId, entryId, modelId].every(v => typeof v === 'string' && v), 'Verified message IDs and model are required');
  const expected = new URL(sessionUrl(baseUrl, sessionId)), actual = new URL(await page.url());
  fail(actual.origin === expected.origin && actual.pathname.replace(/\/+$/, '') === expected.pathname.replace(/\/+$/, '') && actual.searchParams.get('session') === sessionId, 'Page is not the verified conversation');
  await fs.mkdir(outputDir, {recursive: true});
  await fs.writeFile(path.join(outputDir, 'capture-intent.json'), JSON.stringify({sessionId, userEntryId, entryId, modelId}), {flag: 'wx'});
  const token = `piweb-capture-${randomUUID()}`;
  let saved;
  const segments = [], started = Date.now();
  try {
    saved = await page.evaluate(async ({selector, token, userEntryId, entryId, modelLabel}) => {
      await document.fonts.ready;
      const s = document.querySelector(selector);
      if (!s) throw Error('Chat scroller missing; inspect the current DOM');
      for (const id of [userEntryId, entryId]) {
        if (![...s.querySelectorAll('[data-entry-id]')].some(e => e.dataset.entryId === id)) throw Error('Expected message is not loaded');
      }
      if (document.querySelector('.chat-content button[title="Change model"]')?.innerText.trim() !== modelLabel ||
          document.querySelector('.chat-content button[aria-label="更改推理级别"]')?.innerText.trim() !== 'high') throw Error('Visible model/high mismatch');
      if ([...s.querySelectorAll('img')].some(i => !i.complete)) throw Error('Images still loading');
      const original = {scrollTop: s.scrollTop, scrollLeft: s.scrollLeft};
      // Only verified navigation chrome, never message/failed-attempt/metadata elements.
      const style = document.createElement('style'); style.id = token;
      style.textContent = `${selector}{scrollbar-width:none!important;scroll-behavior:auto!important;overflow-anchor:none!important} ${selector}::-webkit-scrollbar{display:none!important} .chat-content button.chat-scroll-to-bottom[aria-label="回到最新消息"]{visibility:hidden!important}`;
      document.head.append(style);
      return original;
    }, {selector: SCROLLER, token, userEntryId, entryId, modelLabel});

    let geometry, target = 0;
    for (;;) {
      fail(segments.length < maxSegments && Date.now() - started < windowMs, 'Capture window exceeded; preserve segments and recapture in a new directory after inspection');
      const state = await page.evaluate(async ({selector, target}) => {
        const s = document.querySelector(selector);
        if (!s) throw Error('Chat scroller disappeared');
        s.scrollTop = target; s.scrollLeft = 0;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const r = s.getBoundingClientRect();
        const overflow = [...s.querySelectorAll('*')].some(e => {
          const css = getComputedStyle(e);
          // KaTeX exposes a visually clipped MathML twin for accessibility.
          if (e.matches('.katex-mathml') && e.clientWidth === 1 && e.clientHeight === 1 && css.position === 'absolute') return false;
          return e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1 && ['auto', 'scroll', 'hidden'].includes(css.overflowX);
        });
        if (overflow || s.scrollWidth > s.clientWidth + 1) throw Error('Horizontal content is clipped; use UI to expose it before capturing');
        return {scroll_top: s.scrollTop, container: {left: r.left, top: r.top, width: r.width,
          client_height: s.clientHeight, content_height: s.scrollHeight}, viewport: [innerWidth, innerHeight]};
      }, {selector: SCROLLER, target});
      if (!geometry) geometry = {container: state.container, viewport: state.viewport};
      fail(JSON.stringify(geometry) === JSON.stringify({container: state.container, viewport: state.viewport}), 'Layout changed during capture; do not stitch');
      fail(segments.length === 0 ? state.scroll_top === 0 : state.scroll_top > segments.at(-1).scroll_top, 'Scroller did not advance');
      const file = path.join(outputDir, `segment-${String(segments.length).padStart(3, '0')}.png`);
      await page.screenshot({path: file, scale: 'css'});
      // Detect asynchronous changes between measurement and screenshot too.
      const unchanged = await page.evaluate(({selector, state}) => {
        const s = document.querySelector(selector), r = s?.getBoundingClientRect();
        return !!s && s.scrollTop === state.scroll_top && s.scrollHeight === state.container.content_height && s.clientHeight === state.container.client_height && r.left === state.container.left && r.top === state.container.top && r.width === state.container.width && innerWidth === state.viewport[0] && innerHeight === state.viewport[1];
      }, {selector: SCROLLER, state});
      fail(unchanged, 'Layout changed while taking a screenshot');
      segments.push({file, scroll_top: state.scroll_top, sha256: sha256(await fs.readFile(file))});
      await fs.writeFile(path.join(outputDir, 'progress.json'), JSON.stringify({geometry, segments}, null, 2));
      await onProgress({segments: segments.length, scrollTop: state.scroll_top});
      const c = geometry.container, max = Math.max(0, c.content_height - c.client_height);
      if (state.scroll_top >= max) break;
      target = Math.min(max, state.scroll_top + Math.max(1, c.client_height - 80));
    }
    const {container: c, viewport} = geometry;
    const plan = {schema: 2, sessionId, userEntryId, entryId, modelId, modelLabel, segments, container: c, viewport,
      bar_strip: {file: segments.at(-1).file, box: [c.left, c.top + c.client_height, c.left + c.width, viewport[1]]},
      out: path.join(outputDir, screenshotFilename(modelLabel))};
    await fs.writeFile(path.join(outputDir, 'plan.json'), JSON.stringify(plan, null, 2), {flag: 'wx'});
    return {planFile: path.join(outputDir, 'plan.json'), segments: segments.length, captureMs: Date.now() - started};
  } finally {
    await page.evaluate(({selector, token, saved}) => {
      document.getElementById(token)?.remove();
      const s = document.querySelector(selector);
      if (s && saved) { s.scrollTop = saved.scrollTop; s.scrollLeft = saved.scrollLeft; }
    }, {selector: SCROLLER, token, saved: saved ?? null});
  }
}

// Resume capture/stitch from its immutable archive binding. Visual review remains a human/agent task.
export async function prepareScreenshot(page, {archiveDirectory, outputDir, pythonExecutable, ...captureOptions},
  {run = promisify(execFile)} = {}) {
  fail([archiveDirectory, outputDir, pythonExecutable].every(p => typeof p === 'string' && path.isAbsolute(p)), 'Use absolute archive, screenshot and Python paths');
  const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
  const result = await read(path.join(archiveDirectory, 'result.json'));
  const modelLabel = result.model.displayName || result.model.modelId;
  const imagePaths = [path.join(outputDir, screenshotFilename(modelLabel)), path.join(outputDir, 'merged.png')];
  fail(result.stopReason === 'stop' && sha256(await fs.readFile(path.join(archiveDirectory, 'reply.md'))) === result.replyHash &&
    sha256(await fs.readFile(path.join(archiveDirectory, 'session.json'))) === result.sessionHash, 'Archive evidence changed');
  const binding = {sessionId: result.sessionId, userEntryId: result.userEntryId, entryId: result.entryId,
    baseUrl: result.baseUrl, version: result.version, role: result.role, promptHash: result.promptHash,
    replyHash: result.replyHash, model: result.model};
  await fs.mkdir(outputDir, {recursive: true});
  const bindingFile = path.join(outputDir, 'archive-binding.json');
  let existingBinding;
  try { existingBinding = await read(bindingFile); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  if (!existingBinding) {
    fail((await fs.readdir(outputDir)).length === 0, 'Unbound screenshot files already exist; inspect rather than adopt');
    await fs.writeFile(bindingFile, JSON.stringify(binding), {flag: 'wx'});
  }
  fail(JSON.stringify(await read(bindingFile)) === JSON.stringify(binding), 'Screenshot belongs to a different reply; preserve it and use a new directory');
  const receiptFile = path.join(outputDir, 'screenshot.json'), planFile = path.join(outputDir, 'plan.json');
  let receipt;
  try { receipt = await read(receiptFile); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  if (receipt) {
    fail(imagePaths.includes(receipt.imageFile) && sha256(await fs.readFile(receipt.imageFile)) === receipt.sha256, 'Screenshot changed');
    return {...await namedScreenshot(receipt, outputDir, modelLabel), status: 'needs_visual_review', reused: true};
  }
  let plan;
  try { plan = await read(planFile); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  if (!plan) {
    await captureConversation(page, {...captureOptions, baseUrl: result.baseUrl, sessionId: result.sessionId,
      userEntryId: result.userEntryId, entryId: result.entryId, modelId: result.model.modelId,
      modelLabel: result.model.displayName || result.model.modelId, outputDir});
    plan = await read(planFile);
  }
  fail(plan.sessionId === result.sessionId && plan.userEntryId === result.userEntryId && plan.entryId === result.entryId && imagePaths.includes(plan.out), 'Capture plan differs from archive');
  for (const segment of plan.segments) fail(sha256(await fs.readFile(segment.file)) === segment.sha256, 'Captured segment changed; preserve it for inspection');
  // shell-free invocation: spaces and non-ASCII paths stay intact. Existing output is never overwritten.
  const {stdout} = await run(pythonExecutable, [fileURLToPath(new URL('./stitch-screenshots.py', import.meta.url)), '--plan', planFile], {encoding: 'utf8'});
  const stitched = JSON.parse(stdout);
  fail(stitched.ok === true && stitched.out === plan.out, 'Stitch did not confirm the expected output');
  receipt = {imageFile: plan.out, sha256: sha256(await fs.readFile(plan.out)), sessionId: result.sessionId,
    entryId: result.entryId, replyHash: result.replyHash};
  await fs.writeFile(receiptFile, JSON.stringify(receipt, null, 2), {flag: 'wx'});
  return {...await namedScreenshot(receipt, outputDir, modelLabel), status: 'needs_visual_review', reused: false};
}
