import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fillStage,startChecks,observeChecks,waitChecks,uploadScreenshot} from '../skills/llm-authoring-workflow/references/automation-recipes/platform-stages.mjs';

// Page contract fake; low-level DOM selectors are tested separately in ego_platform.
async function fixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'platform-stage-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const state={values:{},selections:{},savedAt:'10-26 01:00:00',clicks:[],uploads:0,files:[],lost:false,noDispatch:false,save:true,
   checks:['insight','core-point','attainment'].map(key=>({key,running:false,disabled:false,calls:1,observation:'result_visible',conclusion:'通过',sectionText:'old result'}))};
 const page={
  evaluate:async(_, {itemId,request:r})=>{
   assert.equal(itemId,'1511');
   if(r.operation==='stage')return {itemId,values:Object.fromEntries((r.ids||[]).map(id=>[id,state.values[id]||'value'])),selections:Object.fromEntries((r.selectionIds||[]).map(id=>[id,state.selections[id]||'selected'])),savedAt:state.savedAt};
   if(r.operation==='fill'){Object.assign(state.values,Object.fromEntries(Object.entries(r.values).map(([k,v])=>[k,v.replace(/\r\n?/g,'\n')])));return [];}
   if(r.operation==='checks')return structuredClone(state.checks);
   if(r.operation==='upload')return {files:structuredClone(state.files),busy:false,complete:!!state.files.length};
   if(['verify','scroll'].includes(r.operation))return {};
   throw Error('unexpected request');
  },
  click:async selector=>{
   state.clicks.push(selector);
   if(selector.includes('暂存')){if(state.save)state.savedAt='10-26 01:01:00';}
   else if(selector.includes('label:text-is'))state.selections['question-type-radio']=JSON.parse(selector.match(/text-is\((.+)\)$/)[1]);
   else if(selector.includes('ant-select-item-option'))state.selections[state.selectedField]=JSON.parse(selector.match(/title=(.+)\]$/)[1]);
   else if(selector.includes('-select'))state.selectedField=selector.match(/data-field-id="([^"]+)"/)[1];
   else{const key=selector.match(/"(insight|core-point|attainment)-agent-run-button/)[1];
    if(!state.noDispatch)Object.assign(state.checks.find(c=>c.key===key),{running:true,observation:'running',calls:2});}
   if(state.lost)throw Error('response lost');
  },
  setInputFiles:async(_,files)=>{state.uploads++;state.files.push({id:'new-preview',name:path.basename(files[0])});if(state.lost)throw Error('lost');}
 };
 const args={itemId:'1511',version:'r0001',directory:path.join(root,'stage'),windowMs:2,intervalMs:1};
 return {root,state,page,args};
}
test('fill/save lost response resumes without writing or saving again',async t=>{
 const {page,state,args}=await fixture(t);state.lost=true;
 const input={...args,values:{'question-input':'question\r\n'}};
 assert.equal((await fillStage(page,input)).status,'saved');
 assert.equal((await fillStage(page,input)).status,'saved');assert.equal(state.clicks.length,1);
 state.values['question-input']='changed';assert.equal((await fillStage(page,input)).status,'mismatch');
 await assert.rejects(fillStage(page,{...input,version:'r0002'}),/inputs changed/);
});
test('running checks block a fill without consuming its write intent',async t=>{
 const {page,state,args}=await fixture(t);state.checks[0].running=true;
 assert.equal((await fillStage(page,args)).status,'blocked');
 await assert.rejects(fs.access(path.join(args.directory,'write-intent.json')),/ENOENT/);
 state.checks[0].running=false;assert.equal((await fillStage(page,args)).status,'saved');
});
test('fill uses visible labels through standard controls and verifies resulting choices',async t=>{
 const {page,state,args}=await fixture(t);
 const selections={'question-type-radio':'How-to','question-domain-select':'商科'};
 assert.equal((await fillStage(page,{...args,selections})).status,'saved');
 assert.deepEqual(state.selections,selections);assert.equal(state.clicks.length,4);
});
test('checks link running evidence after click errors and never accept old results',async t=>{
 const {page,state,args}=await fixture(t);state.lost=true;
 const input={...args,keys:['core-point','attainment']};
 assert.equal((await startChecks(page,input)).status,'running');assert.equal(state.clicks.length,2);
 assert.equal((await startChecks(page,input)).status,'running');assert.equal(state.clicks.length,2);
 let screenshots=0;
 assert.equal((await waitChecks(page,args,{windowMs:2,intervalMs:1,onWindow:async()=>{screenshots++;}})).status,'running');assert.equal(screenshots,1);
 for(const c of state.checks.slice(1))Object.assign(c,{running:false,observation:'result_visible',sectionText:'new result'});
 assert.equal((await observeChecks(page,args)).status,'complete');
 state.values['doubao-achievement-note-input']='edited note';
 const changed=await observeChecks(page,args);assert.equal(changed.status,'needs_attention');
 assert.deepEqual(changed.results.map(r=>r.status),['complete','mismatch']);
 state.values['question-input']='edited';assert.ok((await observeChecks(page,args)).results.every(r=>r.status==='mismatch'));
});
test('unknown dispatch stops subsequent checks and resume cannot click either again',async t=>{
 const {page,state,args}=await fixture(t);state.noDispatch=true;
 const input={...args,keys:['core-point','attainment']};
 assert.equal((await startChecks(page,input)).status,'unknown');
 assert.equal((await startChecks(page,input)).status,'needs_attention');assert.equal(state.clicks.length,1);
});

test('first visible call links only to its recorded running dispatch',async t=>{
 const {page,state,args}=await fixture(t);state.checks[1].calls=null;
 const click=page.click;page.click=async s=>{await click(s);state.checks[1].calls=1;};
 await startChecks(page,{...args,keys:['core-point']});
 Object.assign(state.checks[1],{running:false,observation:'result_visible',sectionText:'first result'});
 assert.equal((await observeChecks(page,args)).status,'complete');
 assert.equal(state.clicks.length,1);
});
test('upload lost response observes preview and saved state, without a second upload',async t=>{
 const {root,page,state,args}=await fixture(t);state.lost=true;
 const imageFile=path.join(root,'reply.png');await fs.writeFile(imageFile,'synthetic image bytes');
 const input={...args,prefix:'doubao',imageFile};
 assert.equal((await uploadScreenshot(page,input)).status,'uploaded');
 assert.equal((await uploadScreenshot(page,input)).status,'uploaded');assert.equal(state.uploads,1);assert.equal(state.clicks.length,1);
 await fs.writeFile(imageFile,'different bytes');await assert.rejects(uploadScreenshot(page,input),/inputs changed/);
});
test('preexisting filename cannot be adopted as a verified upload',async t=>{
 const {root,page,state,args}=await fixture(t);const imageFile=path.join(root,'reply.png');await fs.writeFile(imageFile,'bytes');state.files.push({id:'old',name:'reply.png'});
 assert.equal((await uploadScreenshot(page,{...args,prefix:'doubao',imageFile})).status,'needs_attention');assert.equal(state.uploads,0);
});

test('agent-selected attainment dispatch does not enforce criteria outcome and still cannot replay',async t=>{
 const {page,state,args}=await fixture(t);
 // Evidence/exception decisions belong to the agent, not this operation helper.
 for (const observation of ['result_visible','stale_or_no_result']) {
  Object.assign(state.checks[1],{running:false,observation,conclusion:observation==='result_visible'?'不通过':null});
  Object.assign(state.checks[2],{running:false,calls:1,observation:'result_visible',conclusion:'通过'});
  const input={...args,directory:path.join(args.directory,observation),keys:['attainment']};
  assert.equal((await startChecks(page,input)).status,'running');
  const clicks=state.clicks.length;await startChecks(page,input);assert.equal(state.clicks.length,clicks);
 }
 assert.ok(state.clicks.every(selector=>selector.includes('attainment-agent-run-button')));
});
