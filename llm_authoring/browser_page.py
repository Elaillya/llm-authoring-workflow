"""Stable native-page result evidence, explicitly distinct from network receipts."""
from pathlib import Path
import json,shutil,tempfile
from .core import read_json,write_json,require,hash_json,sha,validate_image,now
from . import platform_checks as qa

SOURCE='browser_dom_current_result'


def parse(stage,transport):
    require(stage=='question','页面恢复暂仅支持题目检查')
    text=transport.get('raw_dom_result','');lines=text.split('\n')
    valid=len(lines)>=4 and lines[0]=='题目AI质检结论' and lines[1] in ('通过','不通过') \
        and lines[2]=='题目AI质检详情' and '\n'.join(lines[3:]).strip()
    if not valid:return {'state':'needs_review','server_conclusion':None,'feedback':''}
    return {'state':'passed' if lines[1]=='通过' else 'failed','server_conclusion':lines[1],
            'feedback':'\n'.join(lines[3:]).strip()}


def verify(directory,stage,request,transport):
    directory=Path(directory);require(stage=='question' and transport.get('source')==SOURCE,'页面证据类型不匹配')
    require('http_status' not in transport and 'network_request_id' not in transport,
            '页面证据不能冒充已观察到HTTP状态或网络请求ID')
    hashes=transport.get('artifact_sha256',{})
    require(set(hashes)=={'capture.json','verification.json','before.json','after.json','check-001.png','check-002.png'},'页面证据文件不完整')
    for name,expected in hashes.items():
        file=directory/name;require(file.is_file() and not file.is_symlink() and sha(file)==expected,'页面证据原件被改写：'+name)
    capture=read_json(directory/'capture.json');review=read_json(directory/'verification.json')
    require(capture['source']=='genuine_current_platform_page' and capture['stage']=='question'
            and capture['network_request_observed'] is False,'页面恢复来源标记不明确')
    require(capture['platform_binding']==transport['platform_binding'],'页面恢复绑定被改写')
    require(capture['spec_sha256']==transport['spec_sha256'],'页面采集不属于该输入描述')
    b=transport['platform_binding'];expected_binding=request['binding']
    require(b['task_id']==expected_binding['platform_task_id'] and b['item_id']==expected_binding['platform_item_id']
            and b['template_id']==expected_binding['platform_template_id'] and b['template_type']=='1000','页面结果不属于该平台题目')
    require(review.get('capture_sha256')==hash_json(capture) and isinstance(review.get('reviewer'),str) and review['reviewer'].strip()
            and review.get('inputs_and_fresh_result_verified') is True
            and review.get('screenshots_reviewed')==['check-001.png','check-002.png'],'先逐张核对真实页面截图与输入')
    require(set(capture['files'])=={'before.json','after.json','check-001.png','check-002.png'},'页面采集清单不完整')
    for name,expected in capture['files'].items():require(name in hashes and hashes[name]==expected,'页面截图清单与原件不一致')
    for name in ('check-001.png','check-002.png'):validate_image(directory/name)
    before=read_json(directory/'before.json');after=read_json(directory/'after.json')
    expected={k:v for k,v in request['payload']['params'].items() if k!='from_agentic'}
    for snapshot in (before,after):
        require(snapshot['inputs']==expected and snapshot['dirty'] is False and snapshot['busy'] is False
                and type(snapshot['call_count']) is int and snapshot['call_count']>0,'页面输入已变化、结果过期或仍在运行')
        loc=snapshot['location_binding']
        require(loc['task_id']==b['task_id'] and loc['item_id']==b['item_id']
                and loc['template_id'] in (None,b['template_id']) and loc['template_type'] in (None,'1000'),'截图页面绑定不匹配')
    require(all(before[k]==after[k] for k in ('location_binding','inputs','dirty','busy','result_text','call_count'))
            and after['result_text']==transport['raw_dom_result'],'页面在采集过程中发生变化')
    require(parse(stage,transport)['state'] in ('passed','failed'),'页面未返回有效专业结论')


def import_result(root,directory,q):
    from . import browser_checks as browser
    root=Path(root).resolve();directory=Path(directory).absolute();spec=read_json(directory/'spec.json')
    require(directory==root/'browser-checks'/hash_json(spec) and directory.resolve()==directory
            and spec['binding']==browser.binding(root) and set(spec['records'])=={'question'},'页面回执不属于当前题目')
    with qa.check_lock(root):
        current=browser.descriptions(root,('question',),q)
        require(current==spec['records'] and spec['expected']=={'question':current['question']['payload']},'题面或Insight已变化，旧页面结果不适用')
        source=directory/'dom-result';require(source.is_dir() and not source.is_symlink(),'页面原件缺失')
        require(read_json(source/'capture.json')['spec_sha256']==hash_json(spec),'页面原件属于其他输入描述')
        names=['capture.json','verification.json','before.json','after.json','check-001.png','check-002.png']
        transport={'source':SOURCE,'platform_binding':spec['binding'],'spec_sha256':hash_json(spec),
                   'raw_dom_result':read_json(source/'after.json')['result_text'],
                   'artifact_sha256':{n:sha(source/n) for n in names},
                   'binding_strength':'stable_current_form_inputs_and_native_fresh_result',
                   'limits':'未观察该次HTTP状态、网络请求ID或原请求正文；以两次稳定页面回读和真实截图留证。'}
        request=current['question'];verify(source,'question',request,transport)
        base=qa.records_directory(root);prefix='question-browser-'+hash_json(request);attempts=sorted(base.glob(prefix+'*'))
        for saved in attempts:
            prior,old=qa.verified_record(saved,'question')
            if prior==request and old['transport']==transport:return {'question':qa.latest(root,request)}
        numbers=[int(p.name[len(prefix)+1:].split('-')[0]) for p in attempts if p.name.startswith(prefix+'-')]
        destination=base/(prefix+'-'+str(max(numbers,default=0)+1).zfill(6));require(not destination.exists(),'页面回执目录已存在')
        staging=Path(tempfile.mkdtemp(prefix='.page-evidence-',dir=base))
        try:
            for name in names:shutil.copyfile(source/name,staging/name)
            record={'schema_version':1,'binding':request['binding'],'request_sha256':hash_json(request),
                    'response_sha256':hash_json(transport),'transport':transport,'parsed':parse('question',transport),'observed_at':now()}
            write_json(staging/'request.json',request);write_json(staging/'result.json',record)
            qa.verified_record(staging,'question');staging.rename(destination)
        finally:
            if staging.exists():shutil.rmtree(staging)
        result=qa.latest(root,request)
        from .lessons import observe_platform
        observe_platform(root,'question',result,q)
        return {'question':result,'provenance':SOURCE,'network_receipt_observed':False}
