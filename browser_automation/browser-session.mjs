import {EventEmitter} from 'node:events';
import {pageMatches} from './qa-observer.mjs';

export function loopbackEndpoint(value, port = '19226') {
  const u = new URL(value);
  if (u.protocol !== 'http:' || u.hostname !== '127.0.0.1' || u.port !== port
      || u.pathname !== '/' || u.username || u.password || u.search || u.hash) throw Error('Unexpected loopback endpoint');
  return u;
}
export function pageSocket(value, endpoint) {
  const u = new URL(value);
  if (u.protocol !== 'ws:' || !['127.0.0.1', 'localhost', '[::1]'].includes(u.hostname)
      || !/^\/devtools\/page\/[A-Za-z0-9-]+$/.test(u.pathname) || u.username || u.password || u.search || u.hash) throw Error('Unexpected page debugger endpoint');
  u.host = endpoint.host;
  return u.href;
}
export function chooseBoundTab(tabs, binding) {
  const matches = tabs.filter(t => t.type === 'page' && pageMatches(t.url, binding));
  if (matches.length !== 1) throw Error('Expected exactly one tab for the bound platform item');
  return matches[0];
}

const METHODS = new Set(['Runtime.enable', 'Runtime.evaluate', 'Network.enable', 'Network.getResponseBody', 'Network.getRequestPostData',
  'Page.captureScreenshot', 'Page.navigate', 'Input.insertText', 'Input.dispatchMouseEvent',
  'Browser.getWindowForTarget', 'Browser.getWindowBounds', 'Browser.setWindowBounds', 'Page.bringToFront']);

export class BrowserSession extends EventEmitter {
  static async connect(binding, endpoint = 'http://127.0.0.1:19226/') {
    const base = loopbackEndpoint(endpoint);
    const tabs = await (await fetch(new URL('/json/list', base), {signal: AbortSignal.timeout(10000)})).json();
    const tab = chooseBoundTab(tabs, binding), socket = new WebSocket(pageSocket(tab.webSocketDebuggerUrl, base));
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => { socket.close(); reject(Error('Browser connection timed out')); }, 10000);
      socket.addEventListener('open', () => {clearTimeout(timer); resolve();}, {once: true});
      socket.addEventListener('error', () => {clearTimeout(timer); socket.close(); reject(Error('Browser connection failed'));}, {once: true});
    });
    const session = new BrowserSession(socket, binding);
    try { await session.call('Runtime.enable'); await session.assertBound(); return session; }
    catch (error) { session.close(); throw error; }
  }
  constructor(socket, binding) {
    super();
    Object.assign(this, {socket, binding: structuredClone(binding), next: 0, pending: new Map()});
    socket.addEventListener('message', event => {
      let msg;
      try { msg = JSON.parse(String(event.data)); } catch { this.emit('protocol_error'); return; }
      if (msg.method) { this.emit('protocol_event', msg); return; }
      const item = this.pending.get(msg.id);
      if (!item) return;
      clearTimeout(item.timer); this.pending.delete(msg.id);
      if (msg.error) item.reject(Error('Browser command failed: ' + item.method));
      else item.resolve(msg.result);
    });
    socket.addEventListener('close', () => {
      for (const item of this.pending.values()) { clearTimeout(item.timer); item.reject(Error('Browser disconnected')); }
      this.pending.clear(); this.emit('disconnected');
    });
  }
  call(method, params = {}) {
    if (!METHODS.has(method)) throw Error('Unsupported browser operation');
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      // Per-command transport timeout only; there is no quality-check completion deadline.
      const timer = setTimeout(() => {this.pending.delete(id); reject(Error('Browser transport timed out: ' + method));}, 30000);
      this.pending.set(id, {timer, resolve, reject, method});
      try { this.socket.send(JSON.stringify({id, method, params})); }
      catch { clearTimeout(timer); this.pending.delete(id); reject(Error('Browser transport unavailable')); }
    });
  }
  async assertBound() {
    const r = await this.call('Runtime.evaluate', {expression: 'location.href', returnByValue: true});
    if (r.exceptionDetails || !pageMatches(r.result?.value, this.binding)) throw Error('Browser changed platform item; stop');
  }
  async readForm() {
    const b = this.binding;
    const expression = `(()=>{const u=new URL(location.href);const b=${JSON.stringify(b)};
      if(u.origin!=='https://aidp.bytedance.com'||u.pathname!=='/management/task-v2/'+b.task_id+'/mark-v3/1'
        ||u.searchParams.getAll('itemID').length!==1||u.searchParams.get('itemID')!==b.item_id
        ||['templateID','templateType'].some((k,i)=>u.searchParams.has(k)&&(u.searchParams.getAll(k).length!==1||u.searchParams.get(k)!==[b.template_id,b.template_type][i])))throw Error('Wrong item');
      const roots=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot?.querySelector('[data-field-id="question-input"]'));
      if(roots.length!==1)return {form_found:false};const root=roots[0].shadowRoot;
      return {form_found:true,item_id:b.item_id,fields:[...root.querySelectorAll('textarea[data-field-id],input[data-field-id]')].map(e=>({field:e.dataset.fieldId,type:e.type,characters:typeof e.value==='string'?e.value.length:null,disabled:e.disabled})),
        checks:Object.fromEntries(['insight','core-point','attainment'].map(k=>[k,root.querySelector('[data-field-id="'+k+'-agent-result"]')?.innerText??null])),
        question_types:[...root.querySelectorAll('[data-field-id="question-type-radio"] input')].map(e=>({value:e.value,label:e.closest('label')?.innerText,checked:e.checked})),
        selected_domain:root.querySelector('[data-field-id="question-domain-select"] .ant-select-selection-item')?.innerText??null};})()`;
    const r = await this.call('Runtime.evaluate', {expression, returnByValue: true});
    if (r.exceptionDetails || !r.result?.value) throw Error('Bound form inspection failed');
    await this.assertBound();
    return r.result.value;
  }
  close() {this.socket.close();}
}
