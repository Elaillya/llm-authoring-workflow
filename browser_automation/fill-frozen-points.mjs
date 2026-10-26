#!/usr/bin/env node
// Fill only the current frozen rubric on its bound AIDP page. No model call,
// check click, upload, save, confirmation, or submission is performed here.
import {readFile,writeFile,realpath,lstat,readdir,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {BrowserSession} from './browser-session.mjs';
import {digest} from './qa-observer.mjs';

const root=path.resolve(process.argv[2]||'');
if(!/^\/srv\/llm-authoring-browser-lab\/tasks\/[^/]+$/.test(root)||await realpath(root)!==root)
  throw Error('Use an ordinary task in the isolated browser pilot parent');
async function json(file){const s=await lstat(file);if(!s.isFile()||s.isSymbolicLink())throw Error('Ordinary frozen evidence required');return JSON.parse(await readFile(file,'utf8'));}
const task=await json(path.join(root,'TASK.json'));
if(task.response_mode!=='official_clients'||task.platform_check_mode!=='browser')throw Error('Browser pilot task required');
const pointer=await json(path.join(root,'CURRENT.json'));
if(!/^r\d{4}$/.test(pointer.revision))throw Error('Current revision invalid');
const frozen=await json(path.join(root,'revisions',pointer.revision,'question.json'));
function validate(wrapper){const q=wrapper.question;
  if(!q||q.task_id!==task.task_id||wrapper.question_sha256!==digest(q)
    ||wrapper.prompt_sha256!==digest(q.prompt)||wrapper.rubric_sha256!==digest(q.points))throw Error('Frozen input changed');
  return q;
}
function fields(q){return Object.fromEntries([['insight-description-input','decisive'],['non-decisive-insight-description-input','supporting']]
  .map(([id,kind])=>[id,q.points.filter(p=>p.kind===kind).map(p=>p.id+'：'+p.criterion).join('\n')||'无']));}
const q=validate(frozen),expected=fields(q),previous={};
for(const entry of await readdir(path.join(root,'revisions'),{withFileTypes:true})){
  if(!entry.isDirectory()||!/^r\d{4}$/.test(entry.name))continue;
  const old=validate(await json(path.join(root,'revisions',entry.name,'question.json')));
  for(const [id,value] of Object.entries(fields(old)))(previous[id]??=[]).push(value);
}
const binding=await json(path.join(root,'browser','binding.json'));
const cdp=await BrowserSession.connect(binding);
try{
  if(digest(await json(path.join(root,'CURRENT.json')))!==digest(pointer))throw Error('Revision changed before fill');
  await cdp.assertBound();
  const result=await cdp.call('Runtime.evaluate',{expression:`(async()=>{
    const b=${JSON.stringify(binding)},u=new URL(location.href);
    if(u.origin!=='https://aidp.bytedance.com'||u.pathname!=='/management/task-v2/'+b.task_id+'/mark-v3/1'
      ||u.searchParams.getAll('itemID').length!==1||u.searchParams.get('itemID')!==b.item_id
      ||['templateID','templateType'].some((k,i)=>u.searchParams.has(k)&&(u.searchParams.getAll(k).length!==1||u.searchParams.get(k)!==[b.template_id,b.template_type][i])))throw Error('Wrong bound item');
    const hosts=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot?.querySelector('[data-field-id="question-input"]'));
    if(hosts.length!==1)throw Error('Need one bound form');const form=hosts[0].shadowRoot;
    const q=${JSON.stringify({prompt:q.prompt,insight:q.insight})},values=${JSON.stringify(expected)},previous=${JSON.stringify(previous)};
    function unchanged(){if(form.querySelector('[data-field-id="question-input"]')?.value!==q.prompt
      ||form.querySelector('[data-field-id="insight-input"]')?.value!==q.insight)throw Error('Page does not match current frozen question');}
    unchanged();const before={};
    for(const [id,value] of Object.entries(values)){
      const e=form.querySelector('[data-field-id="'+id+'"]');
      if(!e||e.tagName!=='TEXTAREA'||e.disabled||e.readOnly||e.maxLength>0&&value.length>e.maxLength)throw Error('Rubric field unavailable: '+id);
      if(e.value&&e.value!==value&&!previous[id]?.includes(e.value))throw Error('Unrecorded existing rubric, preserve it: '+id);
      before[id]=e.value;
    }
    const written=[];
    for(const [id,value] of Object.entries(values)){
      unchanged();const e=form.querySelector('[data-field-id="'+id+'"]');
      if(e.value===value)continue;
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,value);
      e.dispatchEvent(new Event('input',{bubbles:true,composed:true}));e.dispatchEvent(new Event('change',{bubbles:true,composed:true}));
      await new Promise(r=>setTimeout(r,100));
      if(form.querySelector('[data-field-id="'+id+'"]')?.value!==value)throw Error('Rubric readback differs: '+id);
      written.push(id);
    }
    unchanged();return {written,before,after:values};
  })()`,returnByValue:true,awaitPromise:true});
  if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||'Rubric fill failed');
  await cdp.assertBound();
  if(digest(await json(path.join(root,'CURRENT.json')))!==digest(pointer))throw Error('Revision changed while filling; inspect the original page');
  const receipt={at:new Date().toISOString(),binding,revision:pointer.revision,question_sha256:frozen.question_sha256,
    rubric_sha256:frozen.rubric_sha256,result:result.result.value,submitted:false};
  const directory=path.join(root,'browser','form-progress');await mkdir(directory,{recursive:true,mode:0o700});
  if(await realpath(directory)!==directory)throw Error('Ordinary receipt directory required');
  const file=path.join(directory,Date.now()+'-frozen-points.json');
  await writeFile(file,JSON.stringify(receipt,null,2)+'\n',{flag:'wx',mode:0o600});
  console.log(JSON.stringify({revision:pointer.revision,written:receipt.result.written,receipt:file,submitted:false}));
}finally{cdp.close();}
