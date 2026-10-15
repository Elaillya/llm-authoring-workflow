"""Exact new prompts and read-only compatibility for historical input manifests."""
from .core import require

LEGACY_FORMAT_INSTRUCTION='请使用 Markdown 格式回复，不要用最外层代码块包裹全文。'


def request_matches(recorded,expected,manual=False):
    legacy={key:value for key,value in expected.items() if key!='prompt_policy'}
    legacy.pop('prompt_file',None)
    if manual:legacy['format_instruction']=LEGACY_FORMAT_INSTRUCTION
    return recorded==expected or recorded==legacy


def prompt_text(request):
    if request.get('prompt_policy')=='prompt_only':
        require('format_instruction' not in request,'纯题面请求不能包含额外格式要求')
        return request['prompt']
    require('prompt_policy' not in request and request.get('format_instruction',LEGACY_FORMAT_INSTRUCTION)==LEGACY_FORMAT_INSTRUCTION,
            '未知的题面发送合同，保留原件并核对请求')
    return request['prompt']+'\n\n'+LEGACY_FORMAT_INSTRUCTION+'\n'


def validate_prompt_file(path,request):
    require(path.is_file() and not path.is_symlink() and path.read_bytes()==prompt_text(request).encode('utf-8'),
            '发送给模型的题面文件已改变或缺失，请恢复绑定题面')
    return path
