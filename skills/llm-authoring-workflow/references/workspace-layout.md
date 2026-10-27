# 工作区与文件命名

新建题目、恢复任务、保存自动化证据时使用本文。用户指定其他父目录时尊重该路径；未另指定且要求放在仓库下时，统一使用工具仓的复数 `workspaces/`。

## 一个父工作区，多道题目目录

`workspaces/` 是共用题库和配置的父工作区；`question-<题号>/` 是每道题的工作目录，直接包含TASK.json、WORKLOG.md和题目材料。不要为每题再初始化一个父工作区，也不在新题下面嵌套tasks或task。目录前缀不改变实际题号；传入question-前缀时工具不重复添加。

```text
workspaces/
  .authoring-workspace.json
  Authoring.code-workspace
  bin/lab
  local/                           # 共用运行环境配置、Cookie、题库与失败经验
  question-<题号>/
    <题号>.code-workspace           # 以命令返回的workspace_file为准
    TASK.json / REQUEST.json / WORKLOG.md / TOOLKIT.md
    drafts/                        # 当前候选、来源与设计复核
    revisions/rNNNN/               # 冻结版本
    model-input/rNNNN/             # 模型填写入口
    responses/                     # 工具管理的原回复与替换归档
    evaluations/                   # 判断与失败复核
    piweb/rNNNN/<角色>/attempt-001/ # 采集意图、回执、完整回复与会话快照
    platform-web/rNNNN/             # 填写、质检、上传阶段回执
      screenshots/<角色>/attempt-001/
        <模型显示名称>.png          # 上传用完整长截图
        segment-000.png / plan.json / screenshot.json
    arena-input/
    delivery/vNNN/                 # 六份最终Markdown与manifest
```

目录按需生成，避免空目录和重复材料。角色用seed/gpt/claude；新候选用版本目录区分，同版获准重取或重截用attempt-002等新尝试目录区分。已有未知请求继续原尝试，不能通过新目录重发。工具返回的原文、冻结和替换路径优先，不手工搬移这些文件。

工作区、冻结版本、交付、备份及本地配置采用系统默认权限，沿用父目录访问规则；流程不额外设置创建者独占权限或强制600/700。发布临时材料仍须排他创建、完整写入后改名，但正式目录须保持正常权限继承。旧Windows工作区若受历史创建者独占ACL影响，可用工具仓scripts/repair_workspace_permissions.ps1检查并备份；明确修复时加-Apply，仅恢复匹配该旧模式的ACL继承，保留所有者及显式授权，跳过链接和带拒绝规则的对象。

## 创建与接续

1. 先检查目标父目录的.authoring-workspace.json与已有题目。已有该题时在原路径运行status接续。默认检索question-*、旧task及tasks/*；独立旧父工作区按其标记接续，不能当成新题重复创建。
2. 父工作区尚不存在：`python scripts/lab.py workspace-create workspaces --first-task <题号>`。自动化加`--no-platform-checks`，直接创建指定首题，不再生成question-001占位题。已有父工作区则运行`python scripts/lab.py --workspace <父工作区绝对路径> new <题号>`，自动化同样加该选项。
3. 后续操作明确使用返回的题目目录：`python scripts/lab.py --workspace <父工作区> --task <题目目录> status`。打开返回的workspace_file；不要把父目录的默认题目当作刚创建的新题。pi-web服务端cwd仍需按启动规则确认，它不自动等于本地题目目录。
4. 旧task、tasks/<题号>及其他父工作区保留原路径、数据库、回执与截图。扫描/更新支持新旧布局混用，workspace-update只更新指引，不迁移原件。跨父目录共享仍需显式配置；不因目录统一擅自合并私人题库。

## 截图名称

最终长图使用归档中已核验的模型显示名称加`.png`，例如`Seed 2.1 Turbo.png`、`GPT-5.6 sol.png`、`Claude Opus 4.6.png`；界面显示名称采用其他合法写法时保留实际名称，不使用上游路由ID替代。文件名非法字符替换为下划线，保留空格和中文。角色、版本、尝试号放目录中，图名不加题号或merged后缀；中间分段保留segment编号。

上传使用prepareScreenshot返回的imageFile。旧merged.png及回执保持；配方恢复时生成或核验同字节的模型名副本，复用原图，无需重新请求模型或重截。已有同名不同内容时停止核对，不能覆盖。图名正确不能替代对会话、回复、可见型号与high的完整性核验。
