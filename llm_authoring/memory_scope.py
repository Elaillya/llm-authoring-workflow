"""Explicit local opt-in for several parents to use one SQLite library."""
from pathlib import Path
from .core import read_json, require

CONFIG_NAME='shared-memory.json'


def _workspace(path):
    require(isinstance(path,str) and Path(path).is_absolute(),'共享题库成员须为绝对路径')
    root=Path(path)
    require(root.is_dir() and str(root.resolve())==path,'共享题库成员须为真实规范目录，不能经符号链接')
    local=root/'local';marker=root/'.authoring-workspace.json'
    require(local.is_dir() and not local.is_symlink(),'共享题库成员缺少普通local目录')
    require(marker.is_file() and not marker.is_symlink() and read_json(marker).get('workflow')=='llm-authoring',
            '共享题库成员不是有效出题父工作区')
    return root


def _config(root):
    file=root/'local'/CONFIG_NAME
    require(file.is_file() and not file.is_symlink(),'共享题库配置缺失或不是普通文件；保留原库，不退回空库')
    return read_json(file)


def resolve(workspace):
    root=Path(workspace).resolve();file=root/'local'/CONFIG_NAME
    if not file.exists() and not file.is_symlink():
        marker=root/'.authoring-workspace.json'
        require(not (marker.exists() and read_json(marker).get('shared_memory_required')),
                '本父工作区已启用共享题库，配置缺失；恢复配置，不退回空库')
        return {'owner':root,'members':(root,),'shared':False}
    config=_config(root)
    require(isinstance(config,dict) and config.get('schema_version')==1,'共享题库配置版本不合法')
    members=config.get('members');owner=config.get('owner_workspace')
    require(isinstance(members,list) and len(members)>=2 and all(isinstance(p,str) for p in members),
            '共享题库至少需要两个明确成员')
    require(len(set(members))==len(members) and owner in members and str(root) in members,
            '共享题库所有者或当前父工作区不在成员中，或成员重复')
    roots=tuple(_workspace(p) for p in members)
    for peer in roots:
        require(read_json(peer/'.authoring-workspace.json').get('shared_memory_required') is True,
                '共享成员尚未持久标记shared_memory_required；先完成启用，不退回空库')
        require(_config(peer)==config,'共享题库各成员配置不一致；先完成配置，不退回空库')
    database=Path(owner)/'local/question-memory.sqlite3'
    require(database.is_file() and not database.is_symlink(),'共享题库主库缺失；从备份核对恢复，不自动新建空库')
    return {'owner':Path(owner),'members':roots,'shared':True}


def describe(workspace):
    scope=resolve(workspace)
    return {'scope':'shared_workspace_group' if scope['shared'] else 'workspace_local_only',
            'database':str(scope['owner']/'local/question-memory.sqlite3'),
            'member_workspaces':[str(p) for p in scope['members']]}


def lesson_scope(workspace):
    return 'shared_workspace_group' if resolve(workspace)['shared'] else 'same_parent_workspace_only'
