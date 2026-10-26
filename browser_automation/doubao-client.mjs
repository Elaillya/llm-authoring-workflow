#!/usr/bin/env node
// Genuine Doubao UI and its own Copy action. No model API, prior clipboard read, or image rendering.
import {readFile,writeFile,mkdir,lstat} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {BrowserSession,loopbackEndpoint,pageSocket} from './browser-session.mjs';
import {digest} from './qa-observer.mjs';
import {ensureCurrentInput} from './ensure-current-input.mjs';
import {openNewDoubaoTask,readFreshDoubaoTask,focusNewDoubaoEditor,highEffortAction} from './doubao-new-task.mjs';

const action=process.argv[2],requestFile=process.argv[3];
if(!['collect','capture'].includes(action)||!requestFile)throw Error('Usage: doubao-client.mjs collect|capture REQUEST_JSON');
const stat=await lstat(requestFile);
if(!stat.isFile()||stat.isSymbolicLink()||!path.resolve(requestFile).startsWith('/srv/llm-authoring-browser-lab/tasks/'))throw Error('Ordinary request in the new parent required');
const contract=JSON.parse(await readFile(requestFile,'utf8'));
const bytesSha=data=>createHash('sha256').update(data).digest('hex');
if(contract.role!=='seed'||contract.model!=='doubao-seed-2.1-pro'||contract.effort!=='high'||contract.source_kind!=='official_client_automation'
 ||contract.prompt_policy!=='prompt_only'||typeof contract.prompt!=='string'||!contract.prompt.length
 ||contract.prompt_bytes_sha256!==bytesSha(Buffer.from(contract.prompt))||Object.hasOwn(contract,'format_instruction'))throw Error('Frozen Seed Pro High contract invalid');
const run=path.join(path.dirname(path.resolve(requestFile)),'run');await mkdir(run,{recursive:true,mode:0o700});
async function json(file){return JSON.parse(await readFile(file,'utf8'));}
async function exists(file){try{return await lstat(file);}catch(error){if(error.code==='ENOENT')return false;throw error;}}
async function save(name,value,{exclusive=false}={}){await writeFile(path.join(run,name),JSON.stringify(value,null,2)+'\n',{flag:exclusive?'wx':'w',mode:0o600});}
const base=loopbackEndpoint('http://127.0.0.1:19226');
const tabs=await(await fetch(new URL('/json/list',base),{signal:AbortSignal.timeout(10000)})).json();
const matches=tabs.filter(t=>{try{return t.type==='page'&&new URL(t.url).origin==='https://www.doubao.com';}catch{return false;}});
if(matches.length!==1)throw Error('Keep one authorized Doubao tab in the dedicated Chrome');
const tab=matches[0],socket=new WebSocket(pageSocket(tab.webSocketDebuggerUrl,base));
await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{socket.close();reject(Error('Doubao connection timed out'))},10000);socket.addEventListener('open',()=>{clearTimeout(timer);resolve()},{once:true});socket.addEventListener('error',()=>{clearTimeout(timer);reject(Error('Doubao connection failed'))},{once:true});});
const cdp=new BrowserSession(socket,{});
let conversation;
try{conversation=await json(path.join(run,'conversation.json'));}catch(error){if(error.code!=='ENOENT')throw error;}
if(conversation&&(!/^\d+$/.test(conversation.session_id)||conversation.request_sha256!==digest(contract)))throw Error('Saved official conversation belongs to different input');
async function evaluate(fn,data={},bind=true){
 const guard=`if(location.origin!=='https://www.doubao.com')throw Error('Wrong official origin');`+(bind&&conversation?`if(location.pathname!==${JSON.stringify('/chat/'+conversation.session_id)})throw Error('Model conversation changed');`:'');
 const r=await cdp.call('Runtime.evaluate',{expression:`(async()=>{${guard}return await (${fn.toString()})(${JSON.stringify(data)});})()`,returnByValue:true,awaitPromise:true});
 if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||'Official page operation failed');return r.result?.value;
}
function state(){
 const replies=[...document.querySelectorAll('[data-testid="receive_message"]')];
 const cards=[...new Set(replies.map(e=>e.closest('[data-testid="union_message"]')).filter(Boolean))];
 const ready=cards.filter(c=>{const b=c.querySelector('[data-testid="message_action_copy"]');return b&&!b.disabled;});
 const stops=[...document.querySelectorAll('button,[role="button"]')].filter(e=>e.getClientRects().length&&(/stop|interrupt/.test(e.dataset.testid||'')||/停止生成|终止任务/.test(e.getAttribute('aria-label')||'')));
 const alerts=[...document.querySelectorAll('[role="alert"]')].filter(e=>e.getClientRects().length).map(e=>e.innerText);
 const last=replies.at(-1);
 const users=[...document.querySelectorAll('[data-testid="send_message"]')];
 const dialogs=[...document.querySelectorAll('[role="dialog"]')].filter(e=>e.getClientRects().length).map(e=>e.innerText);
 return {pathname:location.pathname,model:document.querySelector('[data-testid="chat_input_action_model"]')?.innerText,
  reply_text:last?.innerText??'',reply_cards:cards.length,ready_cards:ready.length,stop_controls:stops.length,
  rich_media:!!last?.querySelector('img,video,audio,iframe,object,embed,canvas'),
  service_error:alerts.some(t=>/请求失败|服务器错误|服务器繁忙|频繁|稍后再试|验证码|真人验证|登录/.test(t)),
  user_messages:users.length,user_prompt_text:users.at(-1)?.innerText??'',
  login_required:!!document.querySelector('input[type="password"]')||dialogs.some(t=>/登录|扫码|手机号|安全验证|滑块|验证码/.test(t))};
}
async function restoreVisible(){
 const window=await cdp.call('Browser.getWindowForTarget',{targetId:tab.id});
 if(window.bounds.windowState==='minimized')await cdp.call('Browser.setWindowBounds',{windowId:window.windowId,bounds:{windowState:'normal'}});
 await cdp.call('Page.bringToFront');
}
async function captureHorizontalOverflow(frames){
 const targets=await evaluate(()=>{
  const reply=document.querySelector('[data-testid="receive_message"]');
  if(!reply)throw Error('Original reply absent');
  const elements=[...reply.querySelectorAll('*')].filter(e=>e.clientWidth>100&&e.scrollWidth>e.clientWidth+4&&/auto|scroll/.test(getComputedStyle(e).overflowX));
  window.__llmHorizontalCapture=elements;
  return elements.map((e,index)=>({index,original_left:e.scrollLeft}));
 });
 try{
  for(const target of targets){
   const position=await evaluate(data=>{
    const e=window.__llmHorizontalCapture?.[data.index];if(!e)throw Error('Overflow element changed');
    e.scrollIntoView({block:'center',inline:'nearest'});
    e.scrollLeft=e.scrollWidth-e.clientWidth;
    return {index:data.index,left:e.scrollLeft,maximum:e.scrollWidth-e.clientWidth,width:e.clientWidth};
   },target);
   await new Promise(r=>setTimeout(r,250));
   const picture=await cdp.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
   const raw=Buffer.from(picture.data,'base64'),filename='screen-'+String(frames.length+1).padStart(3,'0')+'.png';
   await writeFile(path.join(run,filename),raw,{flag:'wx',mode:0o600});
   frames.push({filename,sha256:bytesSha(raw),source:'real_official_webpage',session_id:conversation.session_id,coverage:'horizontal_overflow',horizontal:position});
   await evaluate(data=>{const e=window.__llmHorizontalCapture?.[data.index];if(e)e.scrollLeft=data.original_left;},target);
  }
 }finally{await evaluate(()=>{delete window.__llmHorizontalCapture;}).catch(()=>{});}
 return targets.length;
}
try{
 await cdp.call('Runtime.enable');
 // Background Chrome tabs can expose stale/empty innerText even after the
 // editor DOM has changed. Restore our own tab before verifying or typing.
 await restoreVisible();
 if(conversation&&new URL(tab.url).pathname!=='/chat/'+conversation.session_id){
  await cdp.call('Page.navigate',{url:'https://www.doubao.com/chat/'+conversation.session_id});
  await new Promise(r=>setTimeout(r,1500));
 }
 if(action==='collect'){
  const generationFile=path.join(run,'generation.json');
  if(await exists(generationFile)){
   const original=await json(generationFile);if(original.request_sha256!==digest(contract))throw Error('Existing Seed generation has different input');
   console.log(JSON.stringify({state:original.state,session_id:original.session_id,already_generated:true}));
  }else{
   const dispatchFile=path.join(run,'send-intent.json');
   if(await exists(dispatchFile)){
    const intent=await json(dispatchFile);if(intent.request_sha256!==digest(contract))throw Error('Existing Seed send intent differs');
    if(!conversation)throw Error('An earlier send may have succeeded; inspect its original page, do not send again');
   }else{
    await ensureCurrentInput(requestFile,'seed');
    await evaluate(openNewDoubaoTask,{},false);
    let fresh=false;
    for(let index=0;index<60;index++){
     fresh=await evaluate(readFreshDoubaoTask,{},false);
     if(fresh.fresh)break;await new Promise(r=>setTimeout(r,500));
    }
    if(!fresh.fresh)throw Error('Fresh isolated UI conversation not ready; no prompt sent');
    await evaluate(focusNewDoubaoEditor,{prompt:contract.prompt},false).then(async value=>{if(!value.already_entered)await cdp.call('Input.insertText',{text:contract.prompt});});
    for(const stage of ['model','effort','high']){
     const action=await evaluate(highEffortAction,{prompt:contract.prompt,stage},false);
     if(action.done)break;
     for(const type of ['mouseMoved','mousePressed','mouseReleased'])await cdp.call('Input.dispatchMouseEvent',{
      type,x:action.x,y:action.y,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});
     await new Promise(r=>setTimeout(r,400));
    }
    const editorPoint=await evaluate(highEffortAction,{prompt:contract.prompt,stage:'editor'},false);
    for(const type of ['mouseMoved','mousePressed','mouseReleased'])await cdp.call('Input.dispatchMouseEvent',{
     type,x:editorPoint.x,y:editorPoint.y,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});
    const verified=await evaluate(data=>{const editor=[...document.querySelectorAll('[contenteditable="true"]')].find(e=>e.getClientRects().length);const model=document.querySelector('[data-testid="chat_input_action_model"]')?.innerText;
     if(!/^\/chat\/?$/.test(location.pathname)||editor?.innerText!==data.prompt||document.querySelectorAll('[data-testid="receive_message"]').length)throw Error('Fresh prompt does not match frozen bytes');
     if(!model?.includes('2.1 Pro')||!model.split('\n').some(t=>t.trim()==='高'))throw Error('Select actual Seed 2.1 Pro High before sending');
     return {input_verified:true,model,prompt_readback:editor.innerText};},{prompt:contract.prompt},false);
    await save('input-verified.json',{...verified,prompt_bytes_sha256:contract.prompt_bytes_sha256,request_sha256:digest(contract)},{exclusive:true});
    await save('send-intent.json',{request_sha256:digest(contract),prompt_bytes_sha256:contract.prompt_bytes_sha256,state:'one_send_no_auto_retry',at:new Date().toISOString()},{exclusive:true});
    const clicked=await evaluate(data=>{const editor=[...document.querySelectorAll('[contenteditable="true"]')].find(e=>e.getClientRects().length);
     if(!/^\/chat\/?$/.test(location.pathname)||editor?.innerText!==data.prompt)throw Error('Prompt changed before send');
     const model=document.querySelector('[data-testid="chat_input_action_model"]')?.innerText;
     if(!model?.includes('2.1 Pro')||!model.split('\n').some(t=>t.trim()==='高'))throw Error('Selected model changed before send');
     const readback=editor.innerText;const send=document.querySelector('[data-testid="chat_input_send_button"]');if(!send||send.disabled)throw Error('Official send unavailable');send.click();return {clicked:true,model,prompt_readback:readback};},{prompt:contract.prompt},false);
    await save('send-click.json',{...clicked,request_sha256:digest(contract)},{exclusive:true});
   }
   let previous='',stable=0,finished;
   while(true){
    const current=await evaluate(state,{},!!conversation);
    if(current.login_required||current.service_error)throw Error('Official page reports login, verification or service issue; preserve original request');
    if(current.user_messages>1||current.ready_cards>1&&current.stop_controls===0)throw Error('Official conversation contains multiple messages; inspect originals instead of combining or sending again');
    if(current.user_prompt_text&&!current.user_prompt_text.replace(/\s+/g,'').includes(contract.prompt.replace(/\s+/g,'')))throw Error('Visible user question differs from this frozen prompt; preserve original send intent');
    if(!conversation&&/^\/chat\/\d+$/.test(current.pathname)){
     conversation={session_id:current.pathname.split('/').at(-1),request_sha256:digest(contract)};await save('conversation.json',conversation,{exclusive:true});
    }
    const available=conversation&&current.ready_cards===1&&current.reply_cards===1&&current.stop_controls===0&&(current.reply_text.trim()||current.rich_media);
    stable=available&&current.reply_text===previous?stable+1:0;previous=current.reply_text;
    console.log(JSON.stringify({stage:'waiting_for_official_seed',session_id:conversation?.session_id,reply_characters:current.reply_text.length,stop_controls:current.stop_controls,stable_observations:stable}));
    if(available&&stable>=1){finished=current;break;}
    await new Promise(r=>setTimeout(r,3000));
   }
   await restoreVisible();
   let exported;
   try{
    const point=await evaluate(()=>{
     const replies=[...document.querySelectorAll('[data-testid="receive_message"]')];const cards=[...new Set(replies.map(e=>e.closest('[data-testid="union_message"]')).filter(Boolean))];
     if(cards.length!==1)throw Error('Need unique original reply');const copy=cards[0].querySelector('[data-testid="message_action_copy"]');if(!copy||copy.disabled)throw Error('Official copy unavailable');copy.scrollIntoView({block:'nearest'});
     const trace={captured:null,route:null,writeCalls:0};const oldText=navigator.clipboard.writeText,oldItems=navigator.clipboard.write;
     navigator.clipboard.writeText=function(text){trace.writeCalls++;trace.captured=String(text);trace.route='clipboard.writeText';return oldText.call(this,text);};
     navigator.clipboard.write=async function(items){trace.writeCalls++;for(const item of items)if(item.types.includes('text/plain')){trace.captured=await(await item.getType('text/plain')).text();trace.route='clipboard.write.text/plain';}return oldItems.call(this,items);};
     trace.restore=()=>{navigator.clipboard.writeText=oldText;navigator.clipboard.write=oldItems;delete window.__llmOriginalCopy;};window.__llmOriginalCopy=trace;
     const r=copy.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};
    });
    for(const type of ['mouseMoved','mousePressed','mouseReleased'])await cdp.call('Input.dispatchMouseEvent',{type,x:point.x,y:point.y,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});
    for(let index=0;index<30;index++){
     exported=await evaluate(()=>{const t=window.__llmOriginalCopy;return {captured:t.captured,route:t.route,writeCalls:t.writeCalls};});
     if(exported.captured)break;await new Promise(r=>setTimeout(r,100));
    }
   }finally{await evaluate(()=>window.__llmOriginalCopy?.restore()).catch(()=>{});}
   if(!exported?.captured)throw Error('Official copy did not return original Markdown; no reconstruction allowed');
   const original={...exported,source:'official_reply_copy_action',previous_clipboard_read:false,session_id:conversation.session_id};
   await save('official-copy.json',original,{exclusive:true});
   const raw=Buffer.from(original.captured,'utf8');await writeFile(path.join(run,'reply.md'),raw,{flag:'wx',mode:0o600});
   const copyRaw=await readFile(path.join(run,'official-copy.json'));
   const generation={schema_version:1,state:finished.rich_media?'original_saved_rich_media_requires_review':'generated_pending_screenshot',source_kind:'official_client_automation',
    request_sha256:digest(contract),prompt_bytes_sha256:contract.prompt_bytes_sha256,session_id:conversation.session_id,
    actual_model:'doubao-seed-2.1-pro',actual_effort:'high',input_verified_before_send:true,
    completion_evidence:'Official copy available, no stop control, stable final reply',reply_sha256:bytesSha(raw),official_copy_sha256:bytesSha(copyRaw),
    visible_model:finished.model,rich_media_detected:finished.rich_media,screenshot_verified:false};
   await save('generation.json',generation,{exclusive:true});console.log(JSON.stringify(generation,null,2));
  }
 }else{
  const generation=await json(path.join(run,'generation.json'));
  if(generation.request_sha256!==digest(contract)||!conversation||generation.session_id!==conversation.session_id)throw Error('Seed original generation binding changed');
  if(await exists(path.join(run,'capture.json'))){
   const saved=await json(path.join(run,'capture.json'));
   if(saved.request_sha256!==digest(contract)||saved.generation_sha256!==digest(generation)||saved.session_id!==conversation.session_id)throw Error('Existing capture differs from original generation');
   if(!saved.horizontal_coverage_recorded){
    await restoreVisible();
    const count=await captureHorizontalOverflow(saved.frames);
    saved.horizontal_coverage_recorded=true;saved.horizontal_overflow_elements=count;
    await save('capture.json',saved);
   }
   console.log(JSON.stringify({already_captured:true,capture_file:path.join(run,'capture.json'),frames:saved.frames.map(f=>path.join(run,f.filename))}));
  }
  else{
   await restoreVisible();
   const metrics=await evaluate(()=>{
    const message=document.querySelector('[data-testid="receive_message"]');if(!message)throw Error('Original reply absent');
    let container=message.parentElement;while(container&&!(container.scrollHeight>container.clientHeight+4&&/auto|scroll/.test(getComputedStyle(container).overflowY)))container=container.parentElement;
    container=container||document.scrollingElement;if(!container||container.clientHeight<100)throw Error('No real message scroll viewport');
    window.__llmCaptureViewport=container;return {height:container.clientHeight,maximum:container.scrollHeight-container.clientHeight};
   });
   const frames=[];let wanted=0,index=0;
   try{
    while(true){
     const scroll=await evaluate(data=>{const c=window.__llmCaptureViewport;if(!c)throw Error('Scroll viewport changed');c.scrollTop=data.top;return {top:c.scrollTop,height:c.clientHeight,maximum:c.scrollHeight-c.clientHeight};},{top:wanted});
     await new Promise(r=>setTimeout(r,250));
     const current=await evaluate(state);if(current.stop_controls||current.service_error)throw Error('Original reply state changed before screenshot');
     const after=await evaluate(()=>({top:window.__llmCaptureViewport.scrollTop,height:window.__llmCaptureViewport.clientHeight,maximum:window.__llmCaptureViewport.scrollHeight-window.__llmCaptureViewport.clientHeight}));
     if(Math.abs(after.top-scroll.top)>3)throw Error('Page moved during capture; preserve partial screenshots before retrying capture');
     const picture=await cdp.call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
     const raw=Buffer.from(picture.data,'base64'),filename='screen-'+String(++index).padStart(3,'0')+'.png';
     await writeFile(path.join(run,filename),raw,{flag:'wx',mode:0o600});frames.push({filename,sha256:bytesSha(raw),source:'real_official_webpage',session_id:conversation.session_id,scroll:after});
     if(after.top>=after.maximum-2)break;
     wanted=Math.min(after.maximum,after.top+Math.floor(after.height*0.75));
     if(wanted<=after.top)throw Error('Real page cannot advance; complete coverage not established');
    }
   }finally{await evaluate(()=>{delete window.__llmCaptureViewport;}).catch(()=>{});}
   const count=await captureHorizontalOverflow(frames);
   await save('capture.json',{request_sha256:digest(contract),generation_sha256:digest(generation),session_id:conversation.session_id,source:'real_official_webpage',frames,scroll_coverage_recorded:true,horizontal_coverage_recorded:true,horizontal_overflow_elements:count},{exclusive:true});
   console.log(JSON.stringify({frames:frames.map(f=>path.join(run,f.filename)),screenshot_pixels_modified:false}));
  }
 }
}finally{cdp.close();}
