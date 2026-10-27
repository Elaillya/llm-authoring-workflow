import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createPiWebClient, normalizeBaseUrl, sessionUrl, resolveModel, selectReply} from '../skills/llm-authoring-workflow/references/automation-recipes/piweb-client.mjs';

const ROLE_MODELS={seed:'doubao-seed-2.1-turbo',gpt:'gpt-5.6-sol',claude:'claude-opus-4-6'};

const model={provider:'custom',modelId:ROLE_MODELS.seed,displayName:ROLE_MODELS.seed};
const prompt='  中文问题？\r\n```x\r\nvalue\r\n```\r\n';
const reply='\n# 原文\r\n```js\n42\n```\n ';
const catalog={modelList:Object.values(ROLE_MODELS).map(id=>({id,provider:'custom'})),thinkingLevels:Object.fromEntries(Object.values(ROLE_MODELS).map(id=>['custom:'+id,['low','high']]))};
const assistant=(stopReason='stop',text=reply)=>({role:'assistant',content:[{type:'thinking',thinking:'private'},{type:'text',text}],stopReason,thinkingLevel:'high'});
const detail=(replies=[assistant()])=>({sessionId:'test-session',toolNames:[],leafId:'a'+replies.length,context:{model,thinkingLevel:'high',hasMore:false,entryIds:['u',...replies.map((_,i)=>'a'+(i+1))],messages:[{role:'user',content:[{type:'text',text:prompt}]},...replies]}});
const expected={sessionId:'test-session',prompt,model};
const runtime=()=>({running:true,state:{model:{provider:model.provider,id:model.modelId},thinkingLevel:'high',isStreaming:false,isPromptRunning:false,isCompacting:false,isBashRunning:false,pendingMessageCount:0}});

async function fixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'piweb-test-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const file=path.join(root,'prompt.md');await fs.writeFile(file,prompt);
 const state={detail:detail(),runtime:runtime(),running:[],waiting:[],posts:[],failPost:false,empty:false,gets:[],httpError:null};
 const fetchImpl=async(url,options)=>{
   const u=new URL(url);assert.ok(u.pathname.startsWith('/prefix/api/'));assert.equal(options.redirect,'error');
   if(options.method==='GET'){state.gets.push(u.pathname);if(state.httpError)return {ok:false,status:state.httpError};}
   let result;
   if(options.method==='POST'){
     const body=JSON.parse(options.body);state.posts.push({path:u.pathname,body});
     if(state.failPost)throw Error('secret authorization');
     result={success:true,sessionId:'test-session',model,thinkingLevel:'high'};
   }else if(u.pathname.endsWith('/models')){assert.equal(u.searchParams.get('cwd'),'server project');result=catalog;}
   else if(u.pathname.endsWith('/running'))result={runningSessionIds:state.running,awaitingInputSessionIds:state.waiting};
   else if(u.pathname.includes('/sessions/'))result=state.empty?{sessionId:'test-session',toolNames:[],context:{hasMore:false,messages:[]}}:state.detail;
   else result=state.runtime;
   return {ok:true,json:async()=>structuredClone(result)};
 };
 const client=createPiWebClient({baseUrl:'http://test.invalid/prefix',cwd:'server project',headers:{Authorization:'secret'},fetchImpl});
 return {root,file,state,client,args:{directory:path.join(root,'attempt'),promptFile:file,role:'seed',version:'r0001'}};
}

test('explicit configuration, prefixes, provider aliases and high support',()=>{
 assert.throws(()=>normalizeBaseUrl(),/confirmed/);assert.throws(()=>normalizeBaseUrl('https://secret:pass@host'),/credentials/);
 assert.equal(sessionUrl('https://host/prefix','id'),'https://host/prefix/?session=id');
 assert.deepEqual(resolveModel(catalog,'seed'),model);
 const ambiguous=structuredClone(catalog);ambiguous.modelList.push({id:model.modelId,provider:'second'});
 assert.throws(()=>resolveModel(ambiguous,'seed'),/ambiguous/);assert.deepEqual(resolveModel(ambiguous,'seed','custom'),model);
 const low=structuredClone(catalog);low.thinkingLevels['custom:'+model.modelId]=['low'];assert.throws(()=>resolveModel(low,'seed'),/high/);
 assert.throws(()=>createPiWebClient({baseUrl:'http://host'}),/cwd/);
});
test('reply selection preserves exact text and never concatenates failed attempts',()=>{
 assert.equal(selectReply(detail(),expected).text,reply);
 const chosen=selectReply(detail([assistant('error','partial'),assistant()]),expected);
 assert.equal(chosen.text,reply);assert.equal(chosen.meta.previousErrors,1);assert.equal(chosen.meta.entryId,'a2');
 for(const stop of ['error','aborted','length','toolUse'])assert.equal(selectReply(detail([assistant(stop)]),expected).status,'failed');
 assert.equal(selectReply(detail([assistant('stop','  ')]),expected).status,'failed');
 assert.equal(selectReply(detail([assistant(null)]),expected).status,'unknown');
 assert.equal(selectReply(detail([assistant(),assistant('error')]),expected).status,'ambiguous');
});
test('incomplete context, extra turns and changed configuration cannot import',()=>{
 const d=detail();d.context.hasMore=true;assert.equal(selectReply(d,expected).status,'unknown');
 d.context.hasMore=false;d.toolNames=['bash'];assert.equal(selectReply(d,expected).status,'mismatch');
 assert.equal(selectReply(detail(),{...expected,prompt:prompt.trim()}).status,'mismatch');
 const extra=detail();extra.context.messages.push({role:'user',content:prompt});extra.context.entryIds.push('u2');assert.equal(selectReply(extra,expected).status,'mismatch');
 const duplicate=detail();duplicate.context.entryIds=['u','u'];assert.equal(selectReply(duplicate,expected).status,'unknown');
});
test('runtime retry/queue/waiting state dominates persisted error',async t=>{
 const {client,state}=await fixture(t);state.detail=detail([assistant('error')]);
 state.runtime.state.isPromptRunning=true;assert.equal((await client.observeSession(expected)).status,'running');
 state.runtime.state.isPromptRunning=false;state.runtime.state.pendingMessageCount=1;assert.equal((await client.observeSession(expected)).status,'running');
 state.waiting=['test-session'];assert.equal((await client.observeSession(expected)).status,'awaiting_input');
 state.waiting=[];state.runtime.state.pendingMessageCount=0;assert.equal((await client.observeSession(expected)).status,'failed');
 state.detail=detail();state.runtime={running:false};assert.equal((await client.observeSession(expected)).status,'complete');
});
test('single dispatch is exact and concurrent calls are guarded by durable intent',async t=>{
 const {client,state,args}=await fixture(t);
 const results=await Promise.allSettled([client.startSingle(args),client.startSingle(args)]);
 assert.equal(results.filter(x=>x.status==='fulfilled').length,1);assert.equal(state.posts.length,1);
 assert.equal(state.posts[0].body.message,prompt);assert.deepEqual(state.posts[0].body.toolNames,[]);
 assert.equal(state.posts[0].body.thinkingLevel,'high');
 assert.ok(!(await fs.readFile(path.join(args.directory,'create-intent.json'),'utf8')).includes('secret'));
});

test('receiving an existing user session is GET-only and does not fabricate creation records',async t=>{
 const {client,state,args}=await fixture(t);
 const input={...args,sessionId:'test-session'};
 assert.equal((await client.receiveSession(input)).status,'complete');
 assert.equal((await client.receiveSession(input)).status,'complete');
 assert.equal(state.posts.length,0);
 assert.equal(JSON.parse(await fs.readFile(path.join(args.directory,'result.json'),'utf8')).sourceKind,'piweb_user');
 await assert.rejects(fs.access(path.join(args.directory,'create-intent.json')),/ENOENT/);
 await assert.rejects(client.receiveSession({...input,sessionId:'other'}),/binding changed/);
});
test('lost creation receipt never authorizes another POST',async t=>{
 const {client,state,args}=await fixture(t);state.failPost=true;
 await assert.rejects(client.startSingle(args),/outcome unknown/);
 await assert.rejects(client.startSingle(args),/EEXIST/);
 assert.equal((await client.observeAttempt(args.directory)).status,'unknown');assert.equal(state.posts.length,1);
});
test('prepared send loss recovers read-only with no replay',async t=>{
 const {client,state,args}=await fixture(t);state.empty=true;
 assert.equal((await client.createSession(args)).status,'prepared');assert.equal(state.posts[0].body.type,'ensure_session');assert.ok(!('message' in state.posts[0].body));
 state.failPost=true;await assert.rejects(client.sendPrompt(args.directory),/outcome unknown/);
 await assert.rejects(client.sendPrompt(args.directory),/EEXIST/);assert.equal(state.posts.length,2);
 state.empty=false;assert.equal((await client.observeAttempt(args.directory)).status,'complete');assert.equal(state.posts.length,2);
});
test('changed prompt blocks recovery; archive is exact, idempotent, tamper evident',async t=>{
 const {client,args,file}=await fixture(t);await client.startSingle(args);
 const manifest=await client.archiveAttempt(args.directory);assert.equal(manifest.rawCheck.status,'unavailable');
 assert.equal(await fs.readFile(manifest.replyFile,'utf8'),reply);assert.deepEqual(await client.archiveAttempt(args.directory),manifest);
 await fs.unlink(manifest.replyFile);await assert.rejects(client.archiveAttempt(args.directory),/ENOENT/);
 await fs.writeFile(file,prompt+' ');await assert.rejects(client.observeAttempt(args.directory),/binding changed/);
});
test('HTTP authentication failures do not leak headers',async()=>{
 const client=createPiWebClient({baseUrl:'http://test.invalid',cwd:'x',headers:{Authorization:'secret'},fetchImpl:async()=>({ok:false,status:401})});
 await assert.rejects(client.preflight(),e=>e.message.includes('401')&&!e.message.includes('secret'));
});
test('UI display name is authoritative; opaque backend and returned IDs are allowed',async t=>{
 const alias={modelList:[{id:'routing-id-v99',name:'seed-2.1-turbo',provider:'custom'}],thinkingLevels:{'custom:routing-id-v99':['high']}};
 assert.deepEqual(resolveModel(alias,'seed'),{provider:'custom',modelId:'routing-id-v99',displayName:'seed-2.1-turbo'});
 const wrong={...alias,modelList:[{id:ROLE_MODELS.seed,name:'Different model',provider:'custom'}]};
 assert.throws(()=>resolveModel(wrong,'seed'),/missing/);
 const d=detail();d.context.messages[1].model='upstream-internal-id';d.context.messages[1].responseModel='upstream-another-id';
 assert.equal(selectReply(d,expected).status,'complete');
});

test('collector resumes archive without network or duplicate dispatch and refuses corruption',async t=>{
 const {client,state,args}=await fixture(t);
 assert.equal((await client.collectRole(args)).status,'archived');
 const gets=state.gets.length;state.httpError=503;
 assert.equal((await client.collectRole(args)).status,'archived');
 assert.equal(state.gets.length,gets);assert.equal(state.posts.length,1);
 await fs.unlink(path.join(args.directory,'reply.md'));
 assert.equal((await client.collectRole(args)).status,'local_error');
 assert.equal(state.gets.length,gets);
});
test('collector retains lost dispatch and confirmed technical failure without resampling',async t=>{
 const {client,state,args}=await fixture(t);state.failPost=true;
 assert.equal((await client.collectRole(args)).status,'unknown');state.failPost=false;
 assert.equal((await client.collectRole(args)).status,'unknown');assert.equal(state.posts.length,1);
 const next={...args,directory:path.join(path.dirname(args.directory),'failure')};state.detail=detail([assistant('length','truncated')]);
 assert.equal((await client.collectRole(next)).status,'failed');
 assert.equal((await client.collectRole(next)).status,'failed');assert.equal(state.posts.length,2);
 assert.ok((await fs.readFile(path.join(next.directory,'failure.json'),'utf8')).includes('truncated'));
});
test('read errors are bounded, authentication and local integrity errors stop immediately',async t=>{
 const {client,state,args,file}=await fixture(t);await client.startSingle(args);
 state.httpError=503;
 assert.equal((await client.watchAttempt(args.directory,{windowMs:1000,intervalMs:1})).status,'connection_error');
 state.httpError=401;
 assert.equal((await client.watchAttempt(args.directory)).status,'auth_required');
 state.httpError=null;await fs.writeFile(file,prompt+'changed');
 assert.equal((await client.watchAttempt(args.directory)).status,'local_error');
 await fs.writeFile(path.join(args.directory,'create-intent.json'),'{"secret":');
 const broken=await client.collectRole(args);assert.equal(broken.status,'local_error');assert.ok(!broken.reason.includes('secret'));
 assert.equal(state.posts.length,1);
});
test('catalog is shared within a client and can be refreshed explicitly',async t=>{
 const {client,state,args}=await fixture(t);
 await Promise.all([client.readModels(),client.readModels()]);await client.startSingle(args);
 assert.equal(state.gets.filter(p=>p.endsWith('/models')).length,1);
 await client.readModels({refresh:true});assert.equal(state.gets.filter(p=>p.endsWith('/models')).length,2);
});
