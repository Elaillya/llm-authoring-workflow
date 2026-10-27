import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {observationWindow,observationInterval} from '../skills/llm-authoring-workflow/references/automation-recipes/observation-window.mjs';

test('window progress survives processes, failures and unchanged status do not reset',async t=>{
 const directory=await fs.mkdtemp(path.join(os.tmpdir(),'observe-'));t.after(()=>fs.rm(directory,{recursive:true,force:true}));
 let time=100000, notifications=0,calls=0;
 const options={directory,windowMs:1000,now:()=>time,sleep:async ms=>{time+=ms;},onChange:()=>{notifications++;}};
 await observationWindow(async()=>{calls++;return {status:'running'};},options);
 await observationWindow(async()=>{calls++;return {status:'running'};},options);
 assert.equal(notifications,1);assert.equal(calls,2);
 for(let i=0;i<2;i++)assert.equal((await observationWindow(async()=>({status:'read_error'}),options)).status,'read_error');
 assert.equal((await observationWindow(async()=>({status:'read_error'}),options)).status,'connection_error');
 assert.equal((await observationWindow(async()=>({status:'complete'}),options)).status,'complete');
 const controller=new AbortController();controller.abort();
 assert.equal((await observationWindow(()=>{throw Error('must not read');},{...options,signal:controller.signal})).status,'interrupted');
 assert.equal(observationInterval(0),1000);assert.equal(observationInterval(31000),3000);assert.equal(observationInterval(121000),5000);
});
