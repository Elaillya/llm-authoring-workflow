// Bounded reads with progress across CLI processes. This module never retries a dispatch.
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {setTimeout as delay} from 'node:timers/promises';

export function observationInterval(ageMs,baseMs=1000,failures=0) {
  const normal=ageMs>=120000?5000:ageMs>=30000?3000:baseMs;
  return Math.min(5000,normal*2**failures);
}

export async function observationWindow(observe,{directory,windowMs=15000,intervalMs=1000,
  onChange=()=>{},signal,now=Date.now,sleep=delay,startedAt}={}) {
  if(!path.isAbsolute(directory) || !(windowMs>0 && windowMs<=30000) || !(intervalMs>0))throw Error('Use a private directory and a window up to 30 seconds');
  const file=path.join(directory,'observation-progress.json');
  let progress;
  try{progress=JSON.parse(await fs.readFile(file,'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
  progress??={startedAt:startedAt || new Date(now()).toISOString(),failures:0,last:null};
  const began=Date.parse(progress.startedAt);
  if(!Number.isFinite(began))throw Error('Invalid observation start time');
  const end=now()+windowMs;
  let result;
  do {
    if(signal?.aborted){result={status:'interrupted'};break;}
    result=await observe();
    progress.failures=result.status==='read_error'?progress.failures+1:0;
    if(progress.failures>=3)result={status:'connection_error',reason:'Three consecutive read failures; restore the connection before continuing'};
    const key=JSON.stringify([result.status,result.reason??'',result.results?.map(r=>[r.key,r.status,r.conclusion])]);
    if(key!==progress.last){await onChange(result);progress.last=key;}
    if(!['running','read_error'].includes(result.status))break;
    if(signal?.aborted){result={status:'interrupted'};break;}
    const remaining=end-now();
    if(remaining<=0)break;
    await sleep(Math.min(observationInterval(now()-began,intervalMs,progress.failures),remaining));
  } while(now()<end);
  await fs.mkdir(directory,{recursive:true});
  const temp=path.join(directory,`.observation-${randomUUID()}.json`);
  try{await fs.writeFile(temp,JSON.stringify(progress),{flag:'wx'});await fs.rename(temp,file);}
  finally{await fs.rm(temp,{force:true});}
  return result;
}
