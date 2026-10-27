// 配方 v1（验证日期 2026-10-25）：向指定模型区块上传一张 PNG 截图。
// 机制：截图字节由助手（Node 侧 tab.screenshot() 转 base64）填入 DATA.b64；脚本把数据经 <html> 属性中转，
// 注入主世界 <script> 写入该区块 file input 并派发 change（隔离世界不能写 input.files，evaluate 带参数失效）。
// 返回 dispatch 结果（before/after 表示 change 处理器已消费文件）；上传完成判据=随后读取区块出现文件名预览或"回复截图…已完成"。
(() => {
const DATA = {
  modelLabel: '豆包 turbo 2.1',     // 豆包 turbo 2.1 | GPT-5.6-sol（中/Medium及以上推理） | Claude opus 4.6（Medium及以上推理）
  filename: 'seed-01.png',
  b64: '<PNG base64，不带 data: 前缀>',
};
try {
  const host = document.querySelector('div[id^="garfish_app_for_vibe-coding"]');
  if (!host || !host.shadowRoot) return JSON.stringify({ok: false, error: 'shadow host not found'});
  const root = host.shadowRoot;
  // 定位模型区块（与 fill-model-block 相同：标题文本 → 同时含"Markdown 回复"与"回复截图"的容器）
  let section = null;
  root.querySelectorAll('*').forEach(el => {
    if (!section && el.children.length === 0 && (el.textContent || '').trim() === DATA.modelLabel) {
      let node = el;
      for (let i = 0; i < 10 && node; i++) {
        node = node.parentElement;
        const t = node ? (node.textContent || '') : '';
        if (t.includes('Markdown 回复') && t.includes('回复截图')) { section = node; break; }
        if (t.includes('出题内容')) break;
      }
    }
  });
  if (!section) return JSON.stringify({ok: false, error: 'model section not found: ' + DATA.modelLabel});
  const inputs = section.querySelectorAll('input[type="file"]');
  if (inputs.length === 0) return JSON.stringify({ok: false, error: 'file input not found in section'});
  inputs[0].scrollIntoView({block: 'center'});
  // 数据与目标经 DOM 属性交给主世界脚本
  const de = document.documentElement;
  de.setAttribute('data-u-b64', DATA.b64);
  de.setAttribute('data-u-name', DATA.filename);
  de.setAttribute('data-u-label', DATA.modelLabel);
  de.setAttribute('data-u-result', '');
  const MAIN = "(function(){ try {" +
    "var b64=document.documentElement.getAttribute('data-u-b64');" +
    "var name=document.documentElement.getAttribute('data-u-name');" +
    "var label=document.documentElement.getAttribute('data-u-label');" +
    "var host=document.querySelector('div[id^=\"garfish_app_for_vibe-coding\"]');" +
    "var root=host.shadowRoot;var section=null;" +
    "root.querySelectorAll('*').forEach(function(el){" +
    " if(!section&&el.children.length===0&&(el.textContent||'').trim()===label){" +
    "  var node=el;" +
    "  for(var i=0;i<10&&node;i++){node=node.parentElement;" +
    "   var t=node?(node.textContent||''):'';" +
    "   if(t.indexOf('Markdown 回复')>=0&&t.indexOf('回复截图')>=0){section=node;break;}" +
    "   if(t.indexOf('出题内容')>=0)break;" +
    "  }}});" +
    "if(!section){document.documentElement.setAttribute('data-u-result','main: section not found');return;}" +
    "var input=section.querySelectorAll('input[type=file]')[0];" +
    "if(!input){document.documentElement.setAttribute('data-u-result','main: no input');return;}" +
    "var bin=atob(b64);var bytes=new Uint8Array(bin.length);" +
    "for(var i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);" +
    "var file=new File([bytes],name,{type:'image/png'});" +
    "var dt=new DataTransfer();dt.items.add(file);" +
    "input.files=dt.files;var before=input.files.length;" +
    "input.dispatchEvent(new Event('change',{bubbles:true}));" +
    "var after=input.files.length;" +
    "document.documentElement.setAttribute('data-u-result','ok before='+before+' after='+after);" +
    "} catch(e){document.documentElement.setAttribute('data-u-result','main-err '+e);} })();";
  const s = document.createElement('script');
  s.textContent = MAIN;
  document.body.appendChild(s);
  s.remove();
  de.removeAttribute('data-u-b64');
  de.removeAttribute('data-u-name');
  de.removeAttribute('data-u-label');
  const result = de.getAttribute('data-u-result') || 'no result attribute';
  de.removeAttribute('data-u-result');
  return JSON.stringify({ok: String(result).startsWith('ok'), dispatch: result});
} catch (e) { return JSON.stringify({ok: false, error: String(e)}); } })()
