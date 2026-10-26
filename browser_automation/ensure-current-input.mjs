import path from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';

const exec = promisify(execFile);
export async function ensureCurrentInput(file,role,runner=exec) {
  const absolute=path.resolve(file);
  const match=absolute.match(/^\/srv\/llm-authoring-browser-lab\/tasks\/([A-Za-z0-9][A-Za-z0-9._-]{0,127})\/client-input\/[a-f0-9]{64}\/(seed|gpt|claude)\/request\.json$/);
  if(!match||match[2]!==role)throw Error('Unexpected current client request path');
  const task='/srv/llm-authoring-browser-lab/tasks/'+match[1];
  const {stdout}=await runner('/srv/llm-authoring-browser-lab/bin/lab',['--task',task,'client-prepare',role],{maxBuffer:1048576});
  const prepared=JSON.parse(stdout);
  if(path.resolve(prepared.request)!==absolute)throw Error('The active prompt changed; preserve this historical request and prepare the current one');
  return prepared;
}
