// Serialized into the genuine page by Runtime.evaluate. No model request here.
export function openNewDoubaoTask() {
  const entry=document.querySelector('[data-testid="create_office_task_button"]');
  // The current UI puts the testid on an outer div. Clicking that parent
  // cannot bubble down to its child's React handler.
  const selector='button,[role="button"],a';
  const button=entry?.matches(selector)?entry:entry?.querySelector(selector);
  if(!button||button.disabled||button.getAttribute('aria-disabled')==='true'||!button.getClientRects().length)
    throw Error('Official new work task button unavailable');
  button.click();
  return {clicked_new_task:true};
}

export function readFreshDoubaoTask() {
  return {fresh:/^\/chat\/?$/.test(location.pathname)
    &&document.querySelectorAll('[data-testid="receive_message"],[data-testid="send_message"]').length===0
    &&[...document.querySelectorAll('[contenteditable="true"]')].some(e=>e.getClientRects().length)};
}

export function focusNewDoubaoEditor(data) {
  const editors=[...document.querySelectorAll('[contenteditable="true"]')].filter(e=>e.getClientRects().length);
  if(editors.length!==1)throw Error('Need unique prompt editor');
  const editor=editors[0];
  // An empty ProseMirror paragraph with only a trailing <br> has innerText
  // "\n" but no textContent. Do not mistake it for a different user draft.
  if(editor.textContent!==''&&editor.innerText!==data.prompt)throw Error('Existing user draft differs');
  editor.focus();
  return {already_entered:editor.innerText===data.prompt};
}

// Only chooses the already authorized model's effort in our unsent exact draft.
export function highEffortAction(data) {
  if(location.origin!=='https://www.doubao.com'||!/^\/chat\/?$/.test(location.pathname)
      ||document.querySelectorAll('[data-testid="receive_message"],[data-testid="send_message"]').length)
    throw Error('Fresh own draft required for effort selection');
  const editors=[...document.querySelectorAll('[contenteditable="true"]')].filter(e=>e.getClientRects().length);
  if(editors.length!==1||editors[0].innerText!==data.prompt)throw Error('Effort draft differs from frozen prompt');
  const model=document.querySelector('[data-testid="chat_input_action_model"]');
  if(!model?.innerText.includes('2.1 Pro'))throw Error('Select authorized actual Pro model first');
  const high=model.innerText.split('\n').some(t=>t.trim()==='高');
  if(data.stage==='editor'){
    if(!high)throw Error('High effort not selected');
    const rect=editors[0].getBoundingClientRect();return {done:false,x:rect.x+rect.width/2,y:rect.y+rect.height/2};
  }
  if(high)return {done:true};
  if(!['model','effort','high'].includes(data.stage))throw Error('Unknown effort setup stage');
  const choices=data.stage==='model'?[model]:[...document.querySelectorAll('[role="menuitem"],[role="menuitemradio"],[role="option"]')]
    .filter(e=>e.getClientRects().length&&(data.stage==='effort'?/^推理强度(?:\n|$)/.test(e.innerText.trim()):e.innerText.trim()==='高'));
  if(choices.length!==1||choices[0].disabled||choices[0].getAttribute('aria-disabled')==='true')
    throw Error('Unique official effort option unavailable');
  const rect=choices[0].getBoundingClientRect();return {done:false,x:rect.x+rect.width/2,y:rect.y+rect.height/2};
}
