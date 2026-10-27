// v1, 2026-10-26. DOM operations validated on the current platform form.
// This module neither invokes checks nor submits a task. See ../platform-automation.md.
async function platformDom(page, itemId, request) {
  if (typeof itemId !== 'string' || !/^\d+$/.test(itemId)) {
    throw new Error('Use the verified platform itemID as a string');
  }
  return page.evaluate(({itemId, request}) => {
    const url = new URL(location.href);
    if (url.hostname !== 'aidp.bytedance.com' || !url.pathname.includes('/mark-v3/') ||
        url.searchParams.get('itemID') !== itemId) {
      throw new Error('Platform page does not match the expected itemID');
    }
    const root = document.querySelector('div[id^="garfish_app_for_vibe-coding"]')?.shadowRoot;
    if (!root) throw new Error('Platform form is not ready');
    const find = id => {
      if (typeof id !== 'string' || !/^[a-z0-9-]+$/.test(id)) throw new Error('Invalid field ID');
      const matches = root.querySelectorAll(`[data-field-id="${id}"]`);
      if (matches.length !== 1) throw new Error(`Missing or ambiguous field: ${id}`);
      return matches[0];
    };
    const normalize = value => value.replace(/\r\n?/g, '\n');
    if (request.operation === 'verify') return {itemId, url: url.href};
    if (request.operation === 'stage') {
      const values = Object.fromEntries((request.ids || []).map(id => {
        const e = find(id);
        if (e.tagName !== 'TEXTAREA') throw new Error(`Expected textarea: ${id}`);
        return [id, e.value];
      }));
      const selections = Object.fromEntries((request.selectionIds || []).map(id => {
        const e = find(id), active = e.querySelector('.ant-select-selection-item') || e.querySelector('input[type="radio"]:checked')?.closest('label');
        return [id, active ? active.textContent.trim() : null];
      }));
      const text = document.body.innerText + '\n' + root.textContent;
      const savedAt = text.match(/最近暂存时间[：:]\s*(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/)?.[1] || null;
      return {itemId, values, selections, savedAt};
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
export const readStage = (page, itemId, {ids = [], selectionIds = []} = {}) => platformDom(page, itemId, {operation: 'stage', ids, selectionIds});
export const readUpload = (page, itemId, prefix) => platformDom(page, itemId, {operation: 'upload', prefix});
