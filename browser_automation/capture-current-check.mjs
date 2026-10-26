// Read an already completed native result; never click a quality-check button.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {BrowserSession} from './browser-session.mjs';
import {digest,validateSpec} from './qa-observer.mjs';
const file=path.resolve(process.argv[2]||''),spec=validateSpec(JSON.parse(await readFile(file,'utf8')));
if(Object.keys(spec.expected).join()!=='question'||path.basename(path.dirname(file))!==digest(spec))throw Error('Current question spec required');
const c=await BrowserSession.connect(spec.binding),directory=path.join(path.dirname(file),'dom-result');
try{
 await mkdir(directory,{mode:0o700});
 async function snapshot(scroll){
  await c.assertBound();
  const r=await c.call('Runtime.evaluate',{expression:`(()=>{const u=new URL(location.href),hosts=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot?.querySelector('[data-field-id="question-input"]'));if(hosts.length!==1)throw Error('Need one bound form');const root=hosts[0].shadowRoot,section=root.querySelector('[data-field-id="insight-agent-section"]'),button=root.querySelector('[data-field-id="insight-agent-run-button"]'),warning=section?.querySelector('[data-field-id$="rerun-warning"]');const types={openRecommendation:'开放推荐',analysisDecision:'分析决策',howTo:'How-to'};const value={observed_at:new Date().toISOString(),location_binding:{task_id:u.pathname.split('/')[3],item_id:u.searchParams.get('itemID'),template_id:u.searchParams.get('templateID'),template_type:u.searchParams.get('templateType')},inputs:{'题目':root.querySelector('[data-field-id="question-input"]')?.value,'出题说明':root.querySelector('[data-field-id="insight-input"]')?.value,'领域':root.querySelector('[data-field-id="question-domain-select"] .ant-select-selection-item')?.innerText?.trim(),'题目类型':types[root.querySelector('[data-field-id="question-type-radio"] input:checked')?.value]},dirty:!!warning?.getClientRects().length,busy:!button||button.disabled||button.classList.contains('ant-btn-loading'),result_text:root.querySelector('[data-field-id="insight-agent-result"]')?.innerText,call_count:Number(section?.innerText.match(/Agent\\s*已调用\\s*(\\d+)\\s*次/)?.[1]||0)};for(const [key,value_]of Object.entries(${JSON.stringify(spec.expected.question.params)})){if(key==='from_agentic')continue;if(value.inputs[key]!==value_)throw Error('Current inputs differ: '+key);}if(value.dirty||value.busy||!value.call_count||!/^题目AI质检结论\\n(通过|不通过)\\n题目AI质检详情\\n/.test(value.result_text||''))throw Error('Native result is absent, stale or busy');if(${JSON.stringify(scroll)}==='top')section.scrollIntoView({block:'start'});if(${JSON.stringify(scroll)}==='bottom')section.lastElementChild?.scrollIntoView({block:'end'});return value;})()`,returnByValue:true});
  if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description);return r.result.value;
 }
 const before=await snapshot('top');await c.call('Page.bringToFront');await new Promise(r=>setTimeout(r,350));
 const files={};
 async function save(name,bytes){await writeFile(path.join(directory,name),bytes,{flag:'wx',mode:0o600});files[name]=createHash('sha256').update(bytes).digest('hex');}
 await save('before.json',Buffer.from(JSON.stringify(before,null,2)+'\n'));
 const top=await c.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await save('check-001.png',Buffer.from(top.data,'base64'));
 await snapshot('bottom');await new Promise(r=>setTimeout(r,350));
 const bottom=await c.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await save('check-002.png',Buffer.from(bottom.data,'base64'));
 const after=await snapshot('none');await save('after.json',Buffer.from(JSON.stringify(after,null,2)+'\n'));
 for(const k of ['location_binding','inputs','dirty','busy','result_text','call_count'])if(digest(before[k])!==digest(after[k]))throw Error('Page changed during evidence capture');
 const capture={schema_version:1,source:'genuine_current_platform_page',spec_sha256:digest(spec),stage:'question',platform_binding:spec.binding,files:{...files},network_request_observed:false};
 await save('capture.json',Buffer.from(JSON.stringify(capture,null,2)+'\n'));
 await writeFile(path.join(directory,'verification.json'),JSON.stringify({capture_sha256:digest(capture),reviewer:'',inputs_and_fresh_result_verified:null,screenshots_reviewed:[]},null,2)+'\n',{flag:'wx',mode:0o600});
 console.log(JSON.stringify({directory,call_count:after.call_count,screenshots:['check-001.png','check-002.png'],network_request_observed:false,submitted:false}));
}finally{c.close()}
