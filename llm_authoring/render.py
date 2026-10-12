"""Honest offline API-response screenshots, bound to the untouched Markdown."""
import html
import os
import re
from pathlib import Path
import struct
import uuid
from .core import require, read_response, active_question, now, sha, write_json


def make_html(text, meta, prompt, font):
    from markdown_it import MarkdownIt
    md=MarkdownIt('commonmark',{'html':False,'linkify':False}).enable('table')
    def code_text(value):
        # Some minimal Linux monospace fallback fonts contain empty CJK glyphs.
        # Explicit CJK runs keep ASCII monospace and make Chinese code legible.
        return re.sub(r'[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef]+',
                      lambda match:'<span class="cjk-code">'+match.group()+'</span>',html.escape(value))
    def fence(tokens,index,options,env):
        token=tokens[index];language=token.info.strip().split()[0] if token.info.strip() else ''
        attribute=' class="language-'+html.escape(language,quote=True)+'"' if language else ''
        return '<pre><code'+attribute+'>'+code_text(token.content)+'</code></pre>\n'
    md.renderer.rules['fence']=fence
    md.renderer.rules['code_block']=fence
    md.renderer.rules['code_inline']=lambda tokens,index,options,env:'<code>'+code_text(tokens[index].content)+'</code>'
    # Image URLs may contain private tracking endpoints. Preserve text without loading them.
    md.renderer.rules['image']=lambda tokens,index,options,env: '<span class="image-note">[外部图片未加载：'+html.escape(tokens[index].content)+']</span>'
    body=md.render(text)
    pairs=[('显示名称',meta['display_name']),('请求模型',meta.get('model','')),('API 返回模型',meta.get('returned_model','')),
           ('采集时间 UTC',meta.get('captured_at','')),('原始 Markdown SHA-256',meta['reply_sha256'])]
    details=''.join('<div><strong>'+html.escape(k)+'：</strong>'+html.escape(str(v))+'</div>' for k,v in pairs)
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; font-src file:; img-src 'none'; script-src 'none'">
<title>API Markdown 渲染截图</title><style>
@font-face {font-family:Chinese;src:url("'''+font.as_uri()+'''");font-display:block}
* {box-sizing:border-box} body {margin:0;background:#eef1f5;color:#172033;font:18px/1.85 Chinese, sans-serif}
main {width:1200px;margin:28px auto;background:white;padding:38px 46px;border:1px solid #d5dbe4;border-radius:12px}
.source {font-size:16px;background:#fff3d4;border-left:5px solid #bf7b00;padding:18px;margin-bottom:24px}
.meta {font-size:14px;overflow-wrap:anywhere;border-bottom:1px solid #d5dbe4;padding-bottom:24px;color:#506078}
.prompt {background:#f5f7fb;padding:18px;margin:24px 0;white-space:pre-wrap;overflow-wrap:anywhere}
article {overflow-wrap:anywhere} h1,h2,h3,h4 {line-height:1.45;margin-top:1.4em} h1 {font-size:30px} h2 {font-size:25px} h3 {font-size:21px}
pre {background:#f5f7fb;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.65 monospace} code {font-size:16px} .cjk-code {font-family:Chinese}
table {width:100%;table-layout:fixed;border-collapse:collapse;font-size:16px} th,td {border:1px solid #ced5e0;padding:10px;text-align:left;overflow-wrap:anywhere}
blockquote {border-left:4px solid #ccd5e5;margin-left:0;padding-left:20px} a {color:#245eb5} .image-note {color:#657387}
footer {border-top:1px solid #d5dbe4;margin-top:30px;padding-top:14px;font-size:14px;color:#647085}
</style></head><body><main><div class="source"><strong>API Markdown 渲染截图</strong><br>
由保存的 API 回复原文生成；这不是模型官网、Arena 或其他平台的原页面截图。外部图片不加载。</div>
<div class="meta">'''+details+'''</div><div class="prompt"><strong>题目：</strong>'''+html.escape(prompt)+'''</div>
<article>'''+body+'''</article><footer id="end">完整回复结束 · 原文哈希见页首</footer></main></body></html>'''


def render_response(root, role, assets, browsers):
    require(role in ('seed','gpt','claude'),'Arena 使用原页面截图，不生成替代图')
    item=read_response(root,role);meta=item['meta'];directory=item['directory']
    require(meta.get('source_kind')=='api','渲染只接受 API 原文')
    font=Path(assets).resolve()/'NotoSansCJKsc-Regular.otf'
    require(font.is_file(),'缺少项目中文字体')
    if meta.get('screenshot_kind')=='api_rendered' and (directory/'render-manifest.json').exists():
        from .core import read_json
        manifest=read_json(directory/'render-manifest.json')
        require(manifest['reply_sha256']==meta['reply_sha256'] and sha(directory/meta['screenshot'])==meta['screenshot_sha256'],'已存在截图与原文不匹配')
        return manifest
    final_target=directory/'reply.png';final_html=directory/'reply.html'
    require(not final_target.exists() and not final_html.exists(),'已有未登记渲染文件，先核对，不自动覆盖')
    temporary=directory/('.render-'+uuid.uuid4().hex);temporary.mkdir()
    target=temporary/'reply.png';htmlfile=temporary/'reply.html'
    markup=make_html(item['text'],meta,active_question(root)['question']['prompt'],font)
    htmlfile.write_text(markup,encoding='utf-8')
    os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(Path(browsers).resolve())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        # Chromium's root requirement; answer HTML is escaped and requests are blocked.
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox'] if os.geteuid()==0 else [])
        try:
            context=browser.new_context(viewport={'width':1280,'height':900},device_scale_factor=1,java_script_enabled=False)
            context.set_default_timeout(90000)
            def route(req):
                if req.request.url in (font.as_uri(),htmlfile.resolve().as_uri()):req.continue_()
                else: req.abort()
            context.route('**/*',route)
            page=context.new_page();page.goto(htmlfile.resolve().as_uri(),wait_until='domcontentloaded')
            require(page.evaluate('async () => {return await Promise.race([(async () => {await document.fonts.load("18px Chinese", "中文"); await document.fonts.ready; return document.fonts.check("18px Chinese");})(),new Promise(resolve => setTimeout(() => resolve(false),90000))]);}'),'中文字体未加载')
            height=page.evaluate('Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)')
            require(height<=60000,'回复过长，单图超出安全渲染尺寸；需另行评审分图方式，不能截尾')
            require(page.locator('#end').inner_text().startswith('完整回复结束'),'截图正文末尾未出现')
            page.screenshot(path=str(target),full_page=True,animations='disabled')
            width,png_height=struct.unpack('>II',target.read_bytes()[16:24])
            require(width==1280 and png_height>=height,'截图尺寸不覆盖完整回复')
        finally: browser.close()
    manifest={'kind':'api_rendered','reply_sha256':meta['reply_sha256'],'png_sha256':sha(target),'html_sha256':sha(htmlfile),
              'font_sha256':sha(font),'rendered_at':now(),'width':width,'height':png_height,'full_page':True,'external_resources':'blocked'}
    require(not final_target.exists() and not final_html.exists(),'渲染期间出现其他写入，停止发布以保留原件')
    htmlfile.rename(final_html);target.rename(final_target);temporary.rmdir()
    write_json(directory/'render-manifest.json',manifest)
    meta.update({'screenshot_kind':'api_rendered','screenshot':'reply.png','screenshot_sha256':sha(final_target),'evidence_status':'verified'})
    write_json(directory/'metadata.json',meta)
    return manifest
