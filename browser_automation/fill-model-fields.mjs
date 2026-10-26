#!/usr/bin/env node
import {readFile,writeFile,realpath,lstat} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {BrowserSession} from './browser-session.mjs';
import {fillModelFields} from './model-form-fields.mjs';

const file=path.resolve(process.argv[2]||'');
if(!/^\/srv\/llm-authoring-browser-lab\/tasks\/[^/]+\/browser\/model-fields\/[a-f0-9]{64}\/spec.json$/.test(file)
    ||await realpath(file)!==file||!(await lstat(file)).isFile())throw Error('Ordinary bound model-field spec required');
const root=file.split('/browser/model-fields/')[0],lab=path.join(path.dirname(path.dirname(root)),'bin/lab');
const verify=()=>JSON.parse(execFileSync(lab,['--task',root,'browser-model-verify',file],{encoding:'utf8',maxBuffer:4*1024*1024}));
const job=verify(),cdp=await BrowserSession.connect(job.binding);
try {
  await cdp.assertBound();
  // BrowserSession checks binding before/after; also check within the mutation.
  const expression=`(async()=>{const b=${JSON.stringify(job.binding)},u=new URL(location.href);
    if(u.origin!=='https://aidp.bytedance.com'||u.pathname!=='/management/task-v2/'+b.task_id+'/mark-v3/1'
      ||u.searchParams.getAll('itemID').length!==1||u.searchParams.get('itemID')!==b.item_id
      ||['templateID','templateType'].some((k,i)=>u.searchParams.has(k)&&(u.searchParams.getAll(k).length!==1||u.searchParams.get(k)!==[b.template_id,b.template_type][i])))throw Error('Wrong bound item');
    const hosts=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot?.querySelector('[data-field-id="question-input"]'));
    if(hosts.length!==1)throw Error('Need one native form');
    return await (${fillModelFields.toString()})(hosts[0].shadowRoot,${JSON.stringify(job)});})()`;
  const value=await cdp.call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(value.exceptionDetails)throw Error(value.exceptionDetails.exception?.description||'Native model fill failed');
  await cdp.assertBound();
  if(JSON.stringify(verify())!==JSON.stringify(job))throw Error('Local model contract changed during fill; inspect original page');
  const receipt={at:new Date().toISOString(),binding:job.binding,role:job.role,
    question_sha256:job.question_sha256,model_name:job.model_name,result:value.result.value,submitted:false};
  const out=path.join(path.dirname(file),Date.now()+'-text-fill.json');
  await writeFile(out,JSON.stringify(receipt,null,2)+'\n',{flag:'wx',mode:0o600});
  console.log(JSON.stringify({role:job.role,written:receipt.result.written,selection:receipt.result.selection,receipt:out,uploaded:false,submitted:false}));
} finally {cdp.close();}
