# 私有题目与经验库迁移

源码 clone 不包含私人题库、失败经验、题目1262原件、浏览器登录或模型认证。这些资料不能加入公开 GitHub 分支。只开发模块时无需先迁移题目；恢复1262或复用历史经验时必须取得原件，不能新建空库代替。

## 服务器原位置

| 资料 | 原位置 |
| --- | --- |
| 共享题库及已复核失败经验 | /srv/llm-authoring-lab-v2/local/question-memory.sqlite3 |
| 浏览器父工作区 | /srv/llm-authoring-browser-lab |
| 当前1262尝试 | 上述父目录/tasks/1262-plants |
| 同题历史失败与旧冻结 | 上述父目录/tasks/1262、tasks/1262-photo |
| 原现场开发记录 | /srv/llm-authoring-staging/20261025-browser-workflow-design/integration |
| 最新自动化源码 | 同级workflow；已快照到本开发分支 |

## 私有传输与核验顺序

1. 通过用户控制的私人下载渠道取得需要的题目目录和 SQLite 一致性备份，不放 GitHub。SQLite 使用 backup API 获取一致性快照，不能只复制正在写入的主文件而漏掉 WAL。同时保留逐文件 SHA-256 清单。
2. 先校验归档 SHA，提取到本机独立私有目录，再逐文件对清单；保留原 task/revisions/responses/evaluations/browser/evidence/delivery/WORKLOG 及 Git历史。认证文件、Cookie、真实握手 token、Chrome profile 均不搬入仓库；模型与网页在本机正常登录。
3. 原题里的绝对路径和输入绑定哈希保持原件。给本地运行新增路径映射/导入记录，区分可重建的入口与不可修改的原件。不能全目录搜索替换 /srv/，否则可能破坏回执绑定和历史证据。
4. 旧共享配置包含服务器多个父目录。离线电脑不能把这些路径当作已存在的共享组，也不能声称继续与服务器实时共享。先保留服务器原配置，按 memory_scope.py约束为本机明确建立作用域并验证库非空、quick_check通过及索引/已复核经验可读取。
5. 当前解析器对已启用共享的父目录要求所有成员及一致配置。若本机只保留一个父目录，必须实现并测试显式迁移入口，保留原库及迁移收据后再变更本机作用域，不能删除 shared-memory.json绕过错误或悄悄创建替代空库。
6. 本地与服务器使用复制的 SQLite 后是两个独立快照。转为本地开发期间先约定单写入端，后续双向合并需基于ID和版本实现，不用旧副本覆盖更新的库。
7. 恢复1262前只读打开同一平台题目，核对已填文字、6张图、最新输入和当前检查；未知结果不重发。不要要求用户重做已有 Seed。

只导入代码时，提示本地 Codex“私人题库尚未迁移”，让它先做移植开发；不要以“新父目录库为空”继续出题。交接摘要提供进度方向，实际判分必须读私有冻结原件。

## 本次已准备的私有快照

服务器目录：`/srv/llm-authoring-staging/20261025-browser-workflow-design/local-handoff-20261026/`。其中 authoring-private-state.tar.gz、SHA256SUMS、manifest.json、verification.json 供一次性私有下载与核验；不在Git内。快照包含三个1262尝试目录、父入口元数据和一致性SQLite备份；它保留历史绝对路径而不冒充已完成本地导入。下载后仍须按上面的步骤适配入口与题库作用域。
