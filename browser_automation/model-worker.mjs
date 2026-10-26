#!/usr/bin/env node
import {readFile, writeFile, lstat, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {randomUUID, createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {digest} from './qa-observer.mjs';
import {loopbackEndpoint} from './browser-session.mjs';
import {DEFAULT_HANDSHAKE} from './doctor.mjs';
import {ensureCurrentInput} from './ensure-current-input.mjs';

const UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const SHAPES = {
  capabilities: ['id','action'], claude_start: ['id','action','prompt'],
  status: ['id','action','job_id'], display: ['id','action','job_id','role','session_id'],
  capture: ['id','action','job_id'], gpt_register: ['id','action','session_id','prompt_sha256'],
  navigate: ['id','action','job_id','navigation'],
};
export function validateRpc(request) {
  const fields = SHAPES[request?.action];
  if (!fields || !UUID.test(request.id ?? '') || Object.keys(request).length !== fields.length
      || fields.some(k => !Object.hasOwn(request,k))) throw Error('Invalid fixed worker operation');
  if ('job_id' in request && !UUID.test(request.job_id)) throw Error('Invalid worker job UUID');
  if ('session_id' in request && !UUID.test(request.session_id)) throw Error('Invalid native session UUID');
  if (request.action === 'claude_start' && (typeof request.prompt !== 'string' || !request.prompt.length || request.prompt.length > 20000)) throw Error('Invalid standalone prompt');
  if (request.action === 'display' && !['gpt','claude'].includes(request.role)) throw Error('Unsupported native client');
  if (request.action === 'gpt_register' && !/^[a-f0-9]{64}$/.test(request.prompt_sha256)) throw Error('Invalid prompt bytes SHA256');
  if (request.action === 'navigate' && !['open_transcript','page_up','page_down'].includes(request.navigation)) throw Error('Unsupported bounded navigation');
  return request;
}
export async function rpc(request, {handshake = DEFAULT_HANDSHAKE, fetcher = fetch} = {}) {
  validateRpc(request);
  const stat = await lstat(handshake);
  if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077)) throw Error('Private worker handshake required');
  const cfg = JSON.parse((await readFile(handshake,'utf8')).replace(/^\uFEFF/,''));
  const base = loopbackEndpoint(cfg.endpoint,'19227');
  if (!/^[a-f0-9]{64}$/.test(cfg.token)) throw Error('Invalid worker authentication metadata');
  const response = await fetcher(new URL('/rpc',base),{method:'POST',headers:{'Content-Type':'application/json','X-LLM-Token':cfg.token},
    body:JSON.stringify(request),signal:AbortSignal.timeout(30000),redirect:'error'});
  if (!response.ok) throw Error('Native worker transport failed');
  const data = await response.json();
  if (!data.ok) throw Error(data.error || 'Native worker action rejected');
  return data.result;
}
const bytesSha = value => createHash('sha256').update(value).digest('hex');
async function json(file) {return JSON.parse(await readFile(file,'utf8'));}
async function save(file,value,{exclusive=false}={}) {
  await writeFile(file,JSON.stringify(value,null,2)+'\n',{flag:exclusive?'wx':'w',mode:0o600});
}
export function verifyClaude(raw,status,session) {
  if (status.state !== 'completed' || status.exit_code !== 0 || raw.is_error !== false
      || raw.session_id !== session || status.returned_session_id !== session
      || raw.result !== status.result || typeof raw.result !== 'string' || !raw.result.trim()
      || !raw.modelUsage?.['claude-opus-4-6']
      || raw.modelUsage['claude-opus-4-6'].canonicalModel !== 'claude-opus-4-6') throw Error('Claude original result/model/session mismatch');
  return {reply:raw.result,actual_model:'claude-opus-4-6'};
}
export function validateContract(value) {
  if (value?.source_kind !== 'official_client_automation' || value.prompt_policy !== 'prompt_only'
      || !['gpt','claude'].includes(value.role) || value.effort !== 'high'
      || value.model !== (value.role==='gpt'?'gpt-5.6-sol':'claude-opus-4-6')
      || typeof value.prompt !== 'string' || !value.prompt.length
      || value.prompt_bytes_sha256 !== bytesSha(Buffer.from(value.prompt,'utf8'))
      || Object.hasOwn(value,'format_instruction')) throw Error('Frozen native client contract invalid');
  return value;
}
async function requireProtocol2() {
  const result = await rpc({id:randomUUID(),action:'capabilities'});
  if (result.worker_protocol !== 2 || !result.registered_gpt_display_supported || !result.bounded_transcript_navigation_supported) throw Error('Update and restart the local collector before this step; no model was called');
  return result;
}
async function main() {
  const action = process.argv[2];
  if (action === 'capabilities') {console.log(JSON.stringify(await rpc({id:randomUUID(),action:'capabilities'}),null,2));return;}
  const file = process.argv[3];
  if (!file || !['claude-start','claude-status','gpt-register','display','capture','navigate'].includes(action)) throw Error('Unknown model worker command');
  const stat = await lstat(file);
  if (!stat.isFile() || stat.isSymbolicLink()) throw Error('Ordinary frozen request file required');
  const contract = validateContract(await json(file));
  if (!path.resolve(file).startsWith('/srv/llm-authoring-browser-lab/tasks/')) throw Error('This development adapter is limited to the new parent');
  const run = path.join(path.dirname(path.resolve(file)),'run');
  await requireProtocol2();
  await mkdir(run,{mode:0o700,recursive:true});
  let result;
  if (action === 'claude-start') {
    if (contract.role !== 'claude') throw Error('Claude request required');
    const dispatchFile = path.join(run,'dispatch.json');
    try {
      const previous = await json(dispatchFile);
      if (previous.request_sha256 !== digest(contract)) throw Error('Existing dispatch belongs to different input');
      result = {state:'already_dispatched_do_not_repeat',job_id:previous.request_id,next:'Use claude-status to read the existing original result'};
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
      await ensureCurrentInput(file,'claude');
      const requestId = randomUUID();
      await save(dispatchFile,{request_id:requestId,request_sha256:digest(contract),state:'one_generation_no_auto_retry'},{exclusive:true});
      result = await rpc({id:requestId,action:'claude_start',prompt:contract.prompt});
      await save(path.join(run,'dispatch-response.json'),result,{exclusive:true});
    }
  } else if (action === 'claude-status') {
    const dispatch = await json(path.join(run,'dispatch.json'));
    if (contract.role !== 'claude' || dispatch.request_sha256 !== digest(contract)) throw Error('Claude dispatch binding changed');
    const status = await rpc({id:randomUUID(),action:'status',job_id:dispatch.request_id});
    result = {state:status.state,session_id:dispatch.request_id};
    if (status.state === 'completed') {
      const original = Buffer.from(status.original_stdout_base64 ?? '','base64');
      const native = JSON.parse(original.toString('utf8').replace(/^\uFEFF/,''));
      const proof = verifyClaude(native,status,dispatch.request_id);
      const reply = Buffer.from(proof.reply,'utf8');
      const generation = {schema_version:1,state:'generated_pending_screenshot',source_kind:'official_client_automation',
        request_sha256:digest(contract),prompt_bytes_sha256:contract.prompt_bytes_sha256,
        session_id:dispatch.request_id,actual_model:proof.actual_model,requested_effort:'high',actual_effort:null,
        actual_effort_verified:false,tools_disabled:status.tools_disabled===true,
        reply_sha256:bytesSha(reply),native_stdout_sha256:bytesSha(original),exit_code:status.exit_code,screenshot_verified:false};
      try {
        const old = await json(path.join(run,'generation.json'));
        if (digest(old)!==digest(generation)) throw Error('Existing original generation record differs');
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
        await writeFile(path.join(run,'native-stdout.json'),original,{flag:'wx',mode:0o600});
        await writeFile(path.join(run,'reply.md'),reply,{flag:'wx',mode:0o600});
        await save(path.join(run,'generation.json'),generation,{exclusive:true});
      }
      result = {...generation,native_original_saved:true};
    }
  } else {
    const generation = await json(path.join(run,'generation.json'));
    if (generation.request_sha256 !== digest(contract)) throw Error('Generation contract changed');
    const session = generation.session_id;
    if (action === 'gpt-register') {
      if (contract.role !== 'gpt' || generation.context_verified !== true || generation.actual_model !== contract.model || generation.actual_effort !== 'high') throw Error('Original GPT model/context proof required');
      result = await rpc({id:randomUUID(),action:'gpt_register',session_id:session,prompt_sha256:contract.prompt_bytes_sha256});
    } else if (action === 'display') {
      const displayFile = path.join(run,'display.json');
      try {result = {...await json(displayFile),already_opened:true};}
      catch (error) {
        if (error.code !== 'ENOENT') throw error;
        const requestId = randomUUID(), jobId = randomUUID();
        await save(path.join(run,'display-intent.json'),{request_id:requestId,job_id:jobId,session_id:session},{exclusive:true});
        result = await rpc({id:requestId,action:'display',job_id:jobId,role:contract.role,session_id:session});
        await save(displayFile,result,{exclusive:true});
      }
    } else {
      const display = await json(path.join(run,'display.json'));
      if (display.session_id !== session || display.role !== contract.role) throw Error('Native display binding mismatch');
      if (action === 'navigate') {
        result = await rpc({id:randomUUID(),action:'navigate',job_id:display.job_id,navigation:process.argv[4]});
      } else {
        const captured = await rpc({id:randomUUID(),action:'capture',job_id:display.job_id});
        if (captured.session_id !== session || captured.role !== contract.role || captured.source !== 'real_official_client_console_window') throw Error('Native screenshot binding mismatch');
        const picture = Buffer.from(captured.png_base64,'base64');
        if (picture.subarray(0,8).toString('hex') !== '89504e470d0a1a0a') throw Error('Native PNG required');
        const captureFile = path.join(run,'capture.json');
        let record;
        try {record=await json(captureFile);}catch(error){if(error.code!=='ENOENT')throw error;record={request_sha256:digest(contract),generation_sha256:digest(generation),session_id:session,source:'real_official_client_console_window',frames:[]};}
        if (record.request_sha256!==digest(contract) || record.generation_sha256!==digest(generation)) throw Error('Capture evidence belongs to different generation');
        const filename='screen-'+String(record.frames.length+1).padStart(3,'0')+'.png';
        await writeFile(path.join(run,filename),picture,{flag:'wx',mode:0o600});
        record.frames.push({filename,sha256:bytesSha(picture),source:captured.source,session_id:session,width:captured.width,height:captured.height,local_file:captured.local_file});
        await save(captureFile,record);
        result={saved:path.join(run,filename),width:captured.width,height:captured.height,source:captured.source};
      }
    }
  }
  console.log(JSON.stringify(result,null,2));
}
if (process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) main().catch(error=>{console.error(error.message);process.exitCode=2;});
