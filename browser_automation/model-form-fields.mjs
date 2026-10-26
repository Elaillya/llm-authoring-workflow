// Pure native-form mutation. Never starts a check, upload, save, or submission.
export async function fillModelFields(root, job) {
  const keys={seed:'doubao',gpt:'gpt56',claude:'claude'};
  const key=keys[job.role];
  if(!key||key!==job.platform_key||job.selection?.field!==key+'-achievement-select'
      ||!['已达成','未达成'].includes(job.selection?.label))throw Error('Invalid model field contract');
  if(Object.keys(job.text_fields).sort().join('|')!==[key+'-markdown-input',key+'-achievement-note-input'].sort().join('|'))
    throw Error('Unexpected text field');
  const baseIds=['question-input','insight-input','insight-description-input','non-decisive-insight-description-input'];
  if(Object.keys(job.expected_base).sort().join('|')!==baseIds.sort().join('|')
      ||Object.values(job.expected_base).some(v=>typeof v!=='string'||!v))throw Error('Incomplete base contract');
  const unchanged=()=>{
    for(const [id,value] of Object.entries(job.expected_base))
      if(root.querySelector('[data-field-id="'+id+'"]')?.value!==value)throw Error('Native base differs: '+id);
    if(root.querySelector('[data-field-id="question-domain-select"] .ant-select-selection-item')?.innerText?.trim()!==job.expected_selection?.domain
        ||root.querySelector('[data-field-id="question-type-radio"] input:checked')?.value!==job.expected_selection?.type)
      throw Error('Native domain or type differs');
  };
  unchanged();
  const before={};
  for(const [id,value] of Object.entries(job.text_fields)) {
    const el=root.querySelector('[data-field-id="'+id+'"]');
    if(!el||el.tagName!=='TEXTAREA'||el.disabled||el.readOnly||typeof value!=='string'||!value
        ||el.maxLength>0&&value.length>el.maxLength)throw Error('Model field unavailable: '+id);
    if(el.value&&el.value!==value)throw Error('Unrecognized existing model field; preserve: '+id);
    before[id]=el.value;
  }
  const field=root.querySelector('[data-field-id="'+job.selection.field+'"]');
  if(!field||field.classList.contains('ant-select-disabled'))throw Error('Attainment select unavailable');
  const selected=field.querySelector('.ant-select-selection-item')?.innerText?.trim()||'';
  if(selected&&selected!==job.selection.label)throw Error('Existing attainment differs; preserve before repair');
  const written=[];
  for(const [id,value] of Object.entries(job.text_fields)) {
    unchanged();const el=root.querySelector('[data-field-id="'+id+'"]');
    if(el.value===value)continue;
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,value);
    el.dispatchEvent(new Event('input',{bubbles:true,composed:true}));
    el.dispatchEvent(new Event('change',{bubbles:true,composed:true}));
    await new Promise(r=>setTimeout(r,100));
    if(root.querySelector('[data-field-id="'+id+'"]')?.value!==value)throw Error('Model readback differs: '+id);
    written.push(id);
  }
  if(selected!==job.selection.label) {
    unchanged();const selector=field.querySelector('.ant-select-selector');
    if(!selector)throw Error('Native selector missing');
    selector.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,composed:true}));
    await new Promise(r=>setTimeout(r,150));
    const options=[...root.querySelectorAll('.ant-select-item-option')].filter(e=>
      e.getClientRects().length&&e.innerText.trim()===job.selection.label&&!e.classList.contains('ant-select-item-option-disabled'));
    if(options.length!==1)throw Error('Need one exact enabled attainment option');
    unchanged();options[0].click();await new Promise(r=>setTimeout(r,150));
  }
  unchanged();
  for(const [id,value] of Object.entries(job.text_fields))
    if(root.querySelector('[data-field-id="'+id+'"]')?.value!==value)throw Error('Final model readback differs');
  if(root.querySelector('[data-field-id="'+job.selection.field+'"] .ant-select-selection-item')?.innerText?.trim()!==job.selection.label)
    throw Error('Final attainment readback differs');
  return {written,before,after:job.text_fields,selection:job.selection,submitted:false};
}
