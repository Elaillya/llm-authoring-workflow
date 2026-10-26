import {readFile,writeFile,lstat,realpath} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {BrowserSession} from '/srv/llm-authoring-staging/20261025-browser-workflow-design/workflow/browser_automation/browser-session.mjs';

const root='/srv/llm-authoring-browser-lab/tasks/1262-plants';
const spec=root+'/browser/model-fields/b5c9f570aeb193a82fb393c4fc11ca5d9d5875ecbf120bc4c8fb76ec66b9ca1d/spec.json';
const verify=()=>JSON.parse(execFileSync('/srv/llm-authoring-browser-lab/bin/lab',['--task',root,'browser-model-verify',spec],{encoding:'utf8',maxBuffer:4*1024*1024}));
const job=verify();if(job.role!=='seed'||job.model_name!=='Seed 2.1 Pro'||job.screenshots.length!==6)throw Error('Wrong original screenshot contract');
const sha=b=>createHash('sha256').update(b).digest('hex');
const files=[];
for(const [i,frame]of job.screenshots.entries()){
 if(await realpath(frame.file)!==frame.file||!(await lstat(frame.file)).isFile())throw Error('Need ordinary original PNG');
 const b=await readFile(frame.file);
 if(sha(b)!==frame.sha256||!b.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'))||b.length>20*1024*1024)throw Error('Original PNG changed or exceeds native limit');
 files.push({name:`Seed-2.1-Pro-${String(i+1).padStart(2,'0')}-${frame.sha256.slice(0,10)}.png`,sha256:frame.sha256,bytes:b.length,base64:b.toString('base64')});
}
const directory=path.dirname(spec),intent=directory+'/original-screenshot-upload-intent.json';
const c=await BrowserSession.connect(job.binding);
const guards=`const b=${JSON.stringify(job.binding)},u=new URL(location.href);if(u.origin!=='https://aidp.bytedance.com'||u.pathname!=='/management/task-v2/'+b.task_id+'/mark-v3/1'||u.searchParams.getAll('itemID').length!==1||u.searchParams.get('itemID')!==b.item_id)throw Error('Wrong bound item');const hosts=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot?.querySelector('[data-field-id="question-input"]'));if(hosts.length!==1)throw Error('Need unique native form');const f=hosts[0].shadowRoot;const j=${JSON.stringify(job)};for(const [id,value]of Object.entries({...j.expected_base,...j.text_fields})){if(f.querySelector('[data-field-id="'+id+'"]')?.value!==value)throw Error('Reviewed text changed: '+id);}if(f.querySelector('[data-field-id="question-domain-select"] .ant-select-selection-item')?.innerText.trim()!==j.expected_selection.domain||f.querySelector('[data-field-id="question-type-radio"] input:checked')?.value!==j.expected_selection.type||f.querySelector('[data-field-id="doubao-achievement-select"] .ant-select-selection-item')?.innerText.trim()!==j.selection.label)throw Error('Reviewed selections changed');`;
async function evaluate(code){const r=await c.call('Runtime.evaluate',{expression:`(async()=>{${guards}${code}})()`,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description);await c.assertBound();return r.result.value;}
try{
 const pre=await evaluate(`const input=f.querySelector('[data-field-id="doubao-screenshot-file-input"]');if(!input||input.type!=='file'||input.disabled||!input.multiple)throw Error('Native upload unavailable');const cards=[...f.querySelectorAll('[data-field-id^="doubao-screenshot-delete-"]')];if(cards.length)throw Error('Existing screenshots: preserve instead of duplicating');return {empty:true,multiple:input.multiple,accept:input.accept};`);
 await writeFile(intent,JSON.stringify({at:new Date().toISOString(),binding:job.binding,question_sha256:job.question_sha256,role:'seed',source:'verified_genuine_official_client_png',files:files.map(({base64,...v})=>v),native_preflight:pre,action:'one_native_file_input_change_no_retry',submitted:false},null,2)+'\n',{flag:'wx',mode:0o600});
 if(JSON.stringify(verify())!==JSON.stringify(job))throw Error('Local contract changed before upload');
 const sent=await evaluate(`const input=f.querySelector('[data-field-id="doubao-screenshot-file-input"]');if(!input||input.disabled||f.querySelector('[data-field-id^="doubao-screenshot-delete-"]'))throw Error('Upload state changed');const files=${JSON.stringify(files)};const dt=new DataTransfer();for(const file of files){const s=atob(file.base64),bytes=Uint8Array.from(s,c=>c.charCodeAt(0));const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');if(digest!==file.sha256||bytes.length!==file.bytes)throw Error('Browser PNG bytes differ');dt.items.add(new File([bytes],file.name,{type:'image/png'}));}input.files=dt.files;if(input.files.length!==files.length)throw Error('Native FileList differs');input.dispatchEvent(new Event('change',{bubbles:true,composed:true}));return {files_dispatched:files.length,submitted:false};`);
 await writeFile(directory+'/original-screenshot-upload-dispatched.json',JSON.stringify({at:new Date().toISOString(),...sent},null,2)+'\n',{flag:'wx',mode:0o600});
 for(;;){
  const state=await evaluate(`const cards=[...f.querySelectorAll('[data-field-id^="doubao-screenshot-delete-"]')].map(button=>{const card=button.parentElement;const img=card.querySelector('img')||card.parentElement?.querySelector('img');let origin=null,path=null;try{const u=new URL(img?.currentSrc||img?.src);origin=u.origin;path=u.pathname;}catch{}return {field:button.dataset.fieldId,text:card.innerText?.slice(0,200),image_loaded:!!img?.complete&&img.naturalWidth>0,remote:!!origin&&origin!=='null'&&!origin.startsWith('blob:'),origin,path};});const alerts=[...document.querySelectorAll('[role="alert"],.ant-message-error'),...f.querySelectorAll('[role="alert"],.ant-message-error')].map(e=>e.innerText).filter(t=>/上传|文件|图片|登录|认证|失败/.test(t));return {cards,alerts,upload_text:f.querySelector('[data-field-id="doubao-screenshot-upload"]')?.innerText};`);
  if(state.alerts.length)throw Error('Native upload reports an error; preserve intent and inspect');
  if(state.cards.length>files.length)throw Error('Unexpected additional images: preserve');
  console.log(JSON.stringify({native_uploaded_cards:state.cards.length,loaded_remote_images:state.cards.filter(x=>x.remote&&x.image_loaded).length,expected:files.length,submitted:false}));
  if(state.cards.length===files.length&&state.cards.every(x=>x.remote&&x.image_loaded)){
   if(JSON.stringify(verify())!==JSON.stringify(job))throw Error('Local model evidence changed during upload');
   const receipt={at:new Date().toISOString(),binding:job.binding,question_sha256:job.question_sha256,role:'seed',model:job.model_name,files:files.map(({base64,...v})=>v),native_cards:state.cards.map(({path,...v})=>({...v,remote_path_sha256:sha(path)})),verification:'exact genuine PNG bytes dispatched through native file input; all six native remote thumbnails loaded; no cloud-download hash claim',submitted:false};
   await writeFile(directory+'/original-screenshot-upload-complete.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx',mode:0o600});console.log(JSON.stringify({uploaded:6,receipt:directory+'/original-screenshot-upload-complete.json',submitted:false}));break;
  }
  await new Promise(r=>setTimeout(r,1500));
 }
}finally{c.close()}
