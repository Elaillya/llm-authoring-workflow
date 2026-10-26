import test from 'node:test';
import assert from 'node:assert/strict';
import {openNewDoubaoTask,readFreshDoubaoTask,focusNewDoubaoEditor,highEffortAction} from './doubao-new-task.mjs';

test('new-task testid can be a noninteractive wrapper; activate its genuine control',()=>{
  const calls=[];
  const button={getAttribute:()=>null,getClientRects:()=>[{}],click:()=>calls.push('button')};
  const wrapper={getAttribute:()=>null,querySelector:s=>{assert.equal(s,'button,[role="button"],a');return button;},
    matches:()=>false,click:()=>calls.push('wrapper')};
  const old=globalThis.document;
  try{
    globalThis.document={querySelector:s=>{assert.equal(s,'[data-testid="create_office_task_button"]');return wrapper;}};
    assert.deepEqual(openNewDoubaoTask(),{clicked_new_task:true});
    assert.deepEqual(calls,['button']);
  }finally{globalThis.document=old;}
});

test('the actual fresh route can omit its final slash; existing sessions remain excluded',()=>{
  const oldDoc=globalThis.document,oldLocation=globalThis.location;
  try{
    let messages=[];
    globalThis.document={querySelectorAll:s=>s==='[contenteditable="true"]'?[{getClientRects:()=>[{}]}]:messages};
    for(const pathname of ['/chat','/chat/']){
      globalThis.location={pathname};assert.equal(readFreshDoubaoTask().fresh,true);
    }
    globalThis.location={pathname:'/chat/38449054668742402'};assert.equal(readFreshDoubaoTask().fresh,false);
    globalThis.location={pathname:'/chat'};messages=[{}];assert.equal(readFreshDoubaoTask().fresh,false);
  }finally{globalThis.document=oldDoc;globalThis.location=oldLocation;}
});

test('empty ProseMirror paragraph newline is not a user draft, actual different text is preserved',()=>{
  const old=globalThis.document;let focused=0;
  const editor={innerText:'\n',textContent:'',getClientRects:()=>[{}],focus:()=>focused++};
  try{
    globalThis.document={querySelectorAll:()=>[editor]};
    assert.deepEqual(focusNewDoubaoEditor({prompt:'原题'}),{already_entered:false});
    assert.equal(focused,1);
    editor.innerText='用户未发草稿';editor.textContent='用户未发草稿';
    assert.throws(()=>focusNewDoubaoEditor({prompt:'原题'}),/Existing user draft differs/);
    assert.equal(focused,1);
    editor.innerText='原题';editor.textContent='原题';
    assert.deepEqual(focusNewDoubaoEditor({prompt:'原题'}),{already_entered:true});
  }finally{globalThis.document=old;}
});

test('effort selection accepts only the exact fresh authorized Pro draft and native unique High option',()=>{
 const oldDoc=globalThis.document,oldLoc=globalThis.location;
 const visible={getClientRects:()=>[{}],getAttribute:()=>null,getBoundingClientRect:()=>({x:10,y:20,width:40,height:10})};
 const editor={...visible,innerText:'原题'},model={...visible,innerText:'豆包 2.1 Pro\n中'};
 let messages=[],options=[{...visible,innerText:'推理强度\n中'},{...visible,innerText:'高'},{...visible,innerText:'中'}];
 try{
  globalThis.location={origin:'https://www.doubao.com',pathname:'/chat'};
  globalThis.document={querySelector:()=>model,querySelectorAll:s=>s==='[contenteditable="true"]'?[editor]:s.includes('receive_message')?messages:options};
  assert.throws(()=>highEffortAction({prompt:'原题',stage:'editor'}),/High effort/);
  for(const stage of ['model','effort','high'])assert.deepEqual(highEffortAction({prompt:'原题',stage}),{done:false,x:30,y:25});
  assert.throws(()=>highEffortAction({prompt:'其他题',stage:'high'}),/differs/);
  messages=[{}];assert.throws(()=>highEffortAction({prompt:'原题',stage:'high'}),/Fresh/);messages=[];
  location.pathname='/chat/123';assert.throws(()=>highEffortAction({prompt:'原题',stage:'high'}),/Fresh/);location.pathname='/chat';
  location.origin='https://other.example';assert.throws(()=>highEffortAction({prompt:'原题',stage:'high'}),/Fresh/);location.origin='https://www.doubao.com';
  model.innerText='豆包 2.1 Lite\n高';assert.throws(()=>highEffortAction({prompt:'原题',stage:'high'}),/Pro/);
  model.innerText='豆包 2.1 Pro\n高';assert.deepEqual(highEffortAction({prompt:'原题',stage:'model'}),{done:true});
  assert.deepEqual(highEffortAction({prompt:'原题',stage:'editor'}),{done:false,x:30,y:25});
  model.innerText='豆包 2.1 Pro\n中';options.push({...visible,innerText:'高'});assert.throws(()=>highEffortAction({prompt:'原题',stage:'high'}),/Unique/);
 }finally{globalThis.document=oldDoc;globalThis.location=oldLoc;}
});
