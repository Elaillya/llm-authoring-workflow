// v1, 2026-10-26. DOM operations validated on the current platform form.
// This module neither invokes checks nor submits a task. See ../platform-automation.md.
async function platformDom(page, itemId, request) {
  if (typeof itemId !== 'string' || !/^\d+$/.test(itemId)) {
    throw new Error('Use the verified platform itemID as a string');
  }
  return page.evaluate(({itemId, request}) => {
    const url = new URL(location.href);
    if (url.hostname !== 'aidp.bytedance.com' || !url.pathname.includes('/mark-v3/')) {
      throw new Error('Not a platform question page; cannot verify itemID');
    }
    const visibleId = document.body.innerText.match(/题目\s*ID\s*[：:]\s*(\d+)/i)?.[1];
    if (visibleId && visibleId !== itemId) throw Error('Visible platform itemID differs from the confirmed target; verify the actual question');
    const root = document.querySelector('div[id^="garfish_app_for_vibe-coding"]')?.shadowRoot;
    if (!root) {
      if (request.operation === 'stage') return {itemId, values: {}, selections: {}, savedAt: null,
        readStatus: 'loading', issues: [{reason: 'Platform form is not ready'}]};
      throw new Error('Platform form is not ready');
    }
    if (!visibleId) {
      if(request.operation==='stage')return {itemId,values:{},selections:{},savedAt:null,readStatus:'loading',issues:[{reason:'Visible itemID unavailable'}]};
      throw Error('Visible platform itemID unavailable; wait for the target header');
    }
    const find = id => {
      if (typeof id !== 'string' || !/^[a-z0-9-]+$/.test(id)) throw new Error('Invalid field ID');
      const matches = root.querySelectorAll(`[data-field-id="${id}"]`);
      if (matches.length !== 1) throw new Error(`Missing or ambiguous field: ${id}`);
      return matches[0];
    };
    const normalize = value => value.replace(/\r\n?/g, '\n');
    if (request.operation === 'verify') {
      const urlItemId=url.searchParams.get('itemID');
      return {itemId:visibleId, targetSource:'visible_header', url:url.href, urlItemId,
        urlMatchesVisible:urlItemId===null ? null : urlItemId===visibleId};
    }
    if (request.operation === 'feedback') {
      if (!['insight','core-point','attainment'].includes(request.key)) throw Error('Invalid check key');
      const id = `${request.key}-agent-section`, section = find(id), scope = `[data-field-id="${id}"]`;
      const labels = [...section.querySelectorAll('label')];
      const options = labels.map((e,index) => ({label:e.querySelector('input[type="radio"]') ? e.textContent.trim() : '', selected:!!e.querySelector('input[type="radio"]:checked'),
        selector:`${scope} label >> nth=${index}`})).filter(e => ['正常','异常'].includes(e.label));
      if (options.length && (options.length !== 2 || new Set(options.map(e=>e.label)).size !== 2)) throw Error('Ambiguous feedback controls');
      const notes = [...section.querySelectorAll('textarea')].map((e,index) => ({value:e.value, selector:`${scope} textarea >> nth=${index}`}));
      return {status:options.length ? 'ready' : 'not_present', options, notes};
    }
    if (request.operation === 'radio-target') {
      const container = find(request.id), labels = [...container.querySelectorAll('label')];
      const matches = labels.map((label, index) => ({label, index})).filter(({label}) => label.textContent.trim() === request.label);
      if (matches.length !== 1 || !matches[0].label.querySelector('input[type="radio"]')) throw Error('Missing or ambiguous radio label');
      return {selector: `[data-field-id="${request.id}"] label >> nth=${matches[0].index}`};
    }
    if (request.operation === 'stage') {
      const issues = [], controls = {};
      const readField = (id, reader) => {
        try { const value = reader(find(id)); controls[id] = {status: 'read', value}; return value; }
        catch (error) { issues.push({id, reason: error.message}); controls[id] = {status: 'locator_error'}; return null; }
      };
      const values = Object.fromEntries((request.ids || []).map(id => {
        return [id, readField(id, e => {
          if (e.tagName !== 'TEXTAREA') throw new Error(`Expected textarea: ${id}`);
          return e.value;
        })];
      }));
      const selections = Object.fromEntries((request.selectionIds || []).map(id => {
        return [id, readField(id, e => {
          const active = e.querySelector('.ant-select-selection-item') || e.querySelector('input[type="radio"]:checked')?.closest('label');
          return active ? active.textContent.trim() : null;
        })];
      }));
      const checkboxes = Object.fromEntries((request.checkboxIds || []).map(id => [id, readField(id, e => {
        const input = e.matches?.('input[type="checkbox"]') ? e : e.querySelector('input[type="checkbox"]');
        if (!input) throw Error(`Expected checkbox: ${id}`);
        return input.checked;
      })]));
      const text = document.body.innerText + '\n' + root.textContent;
      const savedAt = text.match(/最近暂存时间[：:]\s*(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/)?.[1] || null;
      return {itemId, values, selections, checkboxes, savedAt, readStatus: issues.length ? 'locator_error' : 'ready', issues, controls,
        saveObservation: savedAt ? 'timestamp_visible' : 'unavailable'};
    }
    if (request.operation === 'upload') {
      if (!['doubao', 'gpt56', 'claude'].includes(request.prefix)) throw new Error('Invalid model prefix');
      const prefix = request.prefix, card = find(`${prefix}-response-card`), area = find(`${prefix}-screenshot-upload`);
      const files = [...card.querySelectorAll(`[data-field-id^="${prefix}-screenshot-delete-"]`)].map(e => ({
        id: e.getAttribute('data-field-id'), name: (e.getAttribute('aria-label') || '').replace(/^删除/, ''),
      }));
      return {files, busy: !!area.querySelector('.ant-spin-spinning'),
        complete: /回复截图\s*已完成/.test(card.textContent)};
    }
    if (request.operation === 'fill') {
      // Validate the entire batch before modifying any field.
      const entries = Object.entries(request.values).map(([id, value]) => {
        const element = find(id);
        if (element.tagName !== 'TEXTAREA' || typeof value !== 'string') {
          throw new Error(`Expected textarea and string: ${id}`);
        }
        return {id, element, value: normalize(value)};
      });
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      return entries.map(({id, element, value}) => {
        const changed = element.value !== value;
        if (changed) {
          setter.call(element, value);
          element.dispatchEvent(new Event('input', {bubbles: true}));
          element.dispatchEvent(new Event('change', {bubbles: true}));
        }
        return {id, changed, domMatches: element.value === value};
      });
    }
    if (request.operation === 'read') {
      return request.ids.map(id => {
        const element = find(id);
        if (element.tagName !== 'TEXTAREA') throw new Error(`Expected textarea: ${id}`);
        return {id, value: element.value};
      });
    }
    if (request.operation === 'scroll') {
      const element = find(request.id);
      element.scrollIntoView({block: 'center'});
      return element.getBoundingClientRect().toJSON();
    }
    if (request.operation === 'checks') {
      return ['insight', 'core-point', 'attainment'].map(key => {
        const field = suffix => root.querySelector(`[data-field-id="${key}-agent-${suffix}"]`);
        const section = find(`${key}-agent-section`), button = find(`${key}-agent-run-button`);
        const result = field('result');
        const running = button.classList.contains('ant-btn-loading') || !!button.querySelector('.anticon-loading');
        const raw = result?.textContent || '';
        const conclusion = (raw.match(/结论\s*(不通过|通过|暂无)/) || [])[1] || null;
        const count = (section.textContent.match(/Agent 已调用\s*(\d+)\s*次/) || [])[1];
        const calls = count === undefined ? null : Number(count);
        const needsRerun = !!field('rerun-warning');
        // An observation is not proof that a particular request has completed.
        // Bind it to the recorded input and dispatch evidence in the platform procedure.
        const observation = running ? 'running' : button.disabled ? 'blocked' :
          needsRerun ? 'stale_or_no_result' :
          conclusion && conclusion !== '暂无' ? 'result_visible' :
          !result && calls === null ? 'not_run' : 'unresolved';
        return {key, observation, running, disabled: button.disabled, calls, needsRerun,
          conclusion: observation === 'result_visible' ? conclusion : null,
          resultText: request.details && !running ? raw : null,
          sectionText: request.details && !running ? section.textContent : null};
      });
    }
    throw new Error('Unsupported platform operation');
  }, {itemId, request});
}

export const verifyTarget = (page, itemId) => platformDom(page, itemId, {operation: 'verify'});
export const fillTextBatch = (page, itemId, values) => platformDom(page, itemId, {operation: 'fill', values});
export const readTextFields = (page, itemId, ids) => platformDom(page, itemId, {operation: 'read', ids});
export const scrollToField = (page, itemId, id) => platformDom(page, itemId, {operation: 'scroll', id});
export const readChecks = (page, itemId, {details = false} = {}) => platformDom(page, itemId, {operation: 'checks', details});
export const readStage = (page, itemId, {ids = [], selectionIds = [], checkboxIds = []} = {}) => platformDom(page, itemId, {operation: 'stage', ids, selectionIds, checkboxIds});
export const radioTarget = (page, itemId, id, label) => platformDom(page, itemId, {operation: 'radio-target', id, label});
export const readUpload = (page, itemId, prefix) => platformDom(page, itemId, {operation: 'upload', prefix});
export const readFeedback = (page,itemId,key) => platformDom(page,itemId,{operation:'feedback',key});
