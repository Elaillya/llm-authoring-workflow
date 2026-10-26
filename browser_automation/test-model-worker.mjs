import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {validateRpc,validateContract,verifyClaude} from './model-worker.mjs';
import {ensureCurrentInput} from './ensure-current-input.mjs';

const id='00000000-0000-4000-8000-000000000001';
test('only fixed model registration, screenshots and bounded navigation are accepted',()=>{
  assert.equal(validateRpc({id,action:'navigate',job_id:id,navigation:'page_down'}).navigation,'page_down');
  assert.equal(validateRpc({id,action:'gpt_register',session_id:id,prompt_sha256:'a'.repeat(64)}).session_id,id);
  for(const request of [
    {id,action:'exec',command:'whoami'},
    {id,action:'capture',job_id:id,path:'C:\\private'},
    {id,action:'navigate',job_id:id,navigation:'ENTER'},
    {id,action:'navigate',job_id:'../../',navigation:'page_up'},
    {id,action:'gpt_register',session_id:id,prompt_sha256:'bad'},
    {id,action:'capabilities',prompt:'unused text'},
  ])assert.throws(()=>validateRpc(request));
});
test('frozen user prompt is preserved without format suffixes or model substitution',()=>{
  const prompt='合成独立测试题？';
  const value={source_kind:'official_client_automation',prompt_policy:'prompt_only',role:'claude',
    model:'claude-opus-4-6',effort:'high',prompt,prompt_bytes_sha256:createHash('sha256').update(prompt).digest('hex')};
  assert.equal(validateContract(value).prompt,prompt);
  for(const change of [{format_instruction:'extra'},{model:'some-other-model'},{effort:'low'},{prompt:prompt+'\n'}])assert.throws(()=>validateContract({...value,...change}));
});
test('original Claude result must match completed process, session, model and Markdown',()=>{
  const raw={is_error:false,session_id:id,result:'原始合成回复。',modelUsage:{'claude-opus-4-6':{canonicalModel:'claude-opus-4-6'}}};
  const status={state:'completed',exit_code:0,returned_session_id:id,result:raw.result};
  assert.equal(verifyClaude(raw,status,id).reply,raw.result);
  for(const changed of [{...raw,is_error:true},{...raw,result:'不同原文'},{...raw,session_id:'other'},{...raw,modelUsage:{}}])assert.throws(()=>verifyClaude(changed,status,id));
  assert.throws(()=>verifyClaude(raw,{...status,state:'running'},id));
  assert.throws(()=>verifyClaude(raw,{...status,exit_code:1},id));
});
test('paid dispatch rechecks the active frozen input through the gated toolkit',async()=>{
  const file='/srv/llm-authoring-browser-lab/tasks/1262/client-input/'+('a'.repeat(64))+'/seed/request.json';
  let called;
  await ensureCurrentInput(file,'seed',async(command,args)=>{called={command,args};return {stdout:JSON.stringify({request:file})};});
  assert.equal(called.command,'/srv/llm-authoring-browser-lab/bin/lab');
  assert.deepEqual(called.args,['--task','/srv/llm-authoring-browser-lab/tasks/1262','client-prepare','seed']);
  await assert.rejects(ensureCurrentInput(file,'seed',async()=>({stdout:JSON.stringify({request:file.replace('a'.repeat(64),'b'.repeat(64))})})),/active prompt changed/);
  await assert.rejects(ensureCurrentInput(file,'claude',async()=>{throw Error('Must not execute')}),/request path/);
});
