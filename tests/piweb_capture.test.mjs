import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {captureConversation, prepareScreenshot, screenshotFilename} from '../skills/llm-authoring-workflow/references/automation-recipes/piweb-capture.mjs';
import {sha256} from '../skills/llm-authoring-workflow/references/automation-recipes/piweb-client.mjs';

async function fixture(t, options={}) {
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'piweb-capture-'));t.after(()=>fs.rm(root,{force:true,recursive:true}));
 let restored=false, calls=0;
 const page={url:async()=>options.wrong?'https://host/?session=other':'https://host/prefix?session=session',
   evaluate:async(fn,arg)=>{
     if('saved' in arg){restored=true;return;}
     if('userEntryId' in arg)return {scrollTop:47,scrollLeft:0};
     if('target' in arg)return {scroll_top:Math.min(arg.target,700),container:{left:20,top:10,width:600,client_height:500,content_height:1200},viewport:[800,700]};
     if('state' in arg)return !options.changed;
     throw Error('unexpected evaluation');
   },screenshot:async({path:file,scale})=>{calls++;assert.equal(scale,'css');if(options.fail)throw Error('screenshot failure');await fs.writeFile(file,'synthetic');}};
 const args={baseUrl:'https://host/prefix',sessionId:'session',userEntryId:'user',entryId:'answer',modelId:'test-model',outputDir:path.join(root,'capture')};
 return {page,args,restored:()=>restored,calls:()=>calls};
}
test('capture overlaps, reaches exact bottom, saves plan and restores state',async t=>{
 const f=await fixture(t), result=await captureConversation(f.page,f.args);
 assert.equal(result.segments,3);assert.ok(f.restored());
 const plan=JSON.parse(await fs.readFile(result.planFile,'utf8'));
 assert.deepEqual(plan.segments.map(x=>x.scroll_top),[0,420,700]);
 assert.deepEqual(plan.bar_strip.box,[20,510,620,700]);
 await assert.rejects(captureConversation(f.page,f.args),/EEXIST/);assert.equal(f.calls(),3);
});
test('capture failure or layout change restores page and leaves no completed plan',async t=>{
 for(const options of [{fail:true},{changed:true}]){
   const f=await fixture(t,options);await assert.rejects(captureConversation(f.page,f.args));assert.ok(f.restored());
   await assert.rejects(fs.access(path.join(f.args.outputDir,'plan.json')),/ENOENT/);
 }
});
test('wrong session and bounded capture never produce uploadable plan',async t=>{
 const wrong=await fixture(t,{wrong:true});await assert.rejects(captureConversation(wrong.page,wrong.args),/verified conversation/);assert.equal(wrong.calls(),0);
 const f=await fixture(t);await assert.rejects(captureConversation(f.page,{...f.args,maxSegments:1}),/window exceeded/);assert.ok(f.restored());
 await assert.rejects(fs.access(path.join(f.args.outputDir,'plan.json')),/ENOENT/);
});
test('screenshot composition reuses verified image and rejects a replaced reply',async t=>{
 const f=await fixture(t), archiveDirectory=path.join(path.dirname(f.args.outputDir),'archive');await fs.mkdir(archiveDirectory);
 await fs.writeFile(path.join(archiveDirectory,'reply.md'),'synthetic');await fs.writeFile(path.join(archiveDirectory,'session.json'),'{}');
 const manifest={...f.args,stopReason:'stop',version:'r0001',role:'seed',promptHash:'prompt-hash',replyHash:sha256('synthetic'),sessionHash:sha256('{}'),model:{modelId:'route-id',displayName:'Claude Opus 4.6'}};
 const resultFile=path.join(archiveDirectory,'result.json');await fs.writeFile(resultFile,JSON.stringify(manifest));
 let stitches=0;
 const run=async(exe,args)=>{stitches++;assert.equal(args[1],'--plan');const plan=JSON.parse(await fs.readFile(args[2],'utf8'));await fs.writeFile(plan.out,'merged-image');return {stdout:JSON.stringify({ok:true,out:plan.out})};};
 const args={archiveDirectory,outputDir:f.args.outputDir,pythonExecutable:path.resolve('python')};
 const first=await prepareScreenshot(f.page,args,{run});
 assert.equal(first.status,'needs_visual_review');assert.equal(path.basename(first.imageFile),'Claude Opus 4.6.png');
 assert.equal((await prepareScreenshot(f.page,args,{run})).reused,true);assert.equal(stitches,1);assert.equal(f.calls(),3);
 // Legacy receipts remain valid and get a named copy without recapture or rewriting evidence.
 const receiptFile=path.join(args.outputDir,'screenshot.json'), old=JSON.parse(await fs.readFile(receiptFile,'utf8'));
 old.imageFile=path.join(args.outputDir,'merged.png');await fs.rename(first.imageFile,old.imageFile);
 await fs.writeFile(receiptFile,JSON.stringify(old));const before=await fs.readFile(receiptFile,'utf8');
 const resumed=await prepareScreenshot(f.page,args,{run});assert.equal(path.basename(resumed.imageFile),'Claude Opus 4.6.png');
 assert.equal(await fs.readFile(receiptFile,'utf8'),before);assert.equal(stitches,1);assert.equal(f.calls(),3);
 await fs.writeFile(resumed.imageFile,'different-image');await assert.rejects(prepareScreenshot(f.page,args,{run}),/differs/);
 manifest.entryId='replacement';await fs.writeFile(resultFile,JSON.stringify(manifest));
 await assert.rejects(prepareScreenshot(f.page,args,{run}),/different reply/);
});

test('model screenshot names preserve display names and cannot escape their directory',()=>{
 for(const name of ['Seed 2.1 Turbo','GPT-5.6 sol','Claude Opus 4.6']) assert.equal(screenshotFilename(name),name+'.png');
 assert.equal(screenshotFilename('provider/model:实验?'),'provider_model_实验_.png');
 assert.equal(screenshotFilename('CON'),'_CON.png');
 assert.ok(!screenshotFilename('../route\\model').includes('/'));
 assert.throws(()=>screenshotFilename('   '),/display name/);
});
