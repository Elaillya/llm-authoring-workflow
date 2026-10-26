import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeCheckPreflight} from './native-check-state.mjs';
function fixture({decision='暂无',dirty=false,busy=false,disabled=false}={}){
 const button={disabled,classList:{contains:()=>busy}};
 const section={querySelector:()=>dirty?{getClientRects:()=>[{}]}:null};
 return {querySelector:s=>s.includes('-run-button')?button:s.includes('-section')?section:{innerText:'题目AI质检结论\n'+decision+'\n题目AI质检详情\n原始结果'}};
}
const input={ids:['insight-agent-run-button']};
test('fresh passed and failed native results cannot be called again',()=>{
 for(const decision of ['通过','不通过'])assert.throws(()=>nativeCheckPreflight(fixture({decision}),input),/capture and import/);
});
test('a dirty old result may be checked for genuinely changed inputs',()=>{
 assert.deepEqual(nativeCheckPreflight(fixture({decision:'通过',dirty:true}),input),{buttons_ready:true});
});
test('busy or disabled native controls cannot launch another check',()=>{
 for(const config of [{busy:true},{disabled:true}])assert.throws(()=>nativeCheckPreflight(fixture(config),input),/already running/);
});
test('an empty native result can proceed only through the outer journal guards',()=>{
 assert.deepEqual(nativeCheckPreflight(fixture(),input),{buttons_ready:true});
});
test('nonempty unrecognized conclusions require reading instead of retrying',()=>{
 assert.throws(()=>nativeCheckPreflight(fixture({decision:'需人工核对'}),input),/capture and import/);
});
