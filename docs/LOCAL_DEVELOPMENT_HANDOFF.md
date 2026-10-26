# 本地自动化开发接续

更新：2026-10-26，Asia/Shanghai。开发分支：`dev/local-browser-automation`。基线为 `2420fb8bc7c574bacaf1abd8525ae067fed67b66`，来自同仓库 main；此分支保存之后的浏览器自动化开发快照，不合并到 main。

## 接到任务先做什么

1. 读根目录 AGENTS.md、本文件、[实际验证记录](AUTOMATION_VALIDATION.md)和[浏览器步骤](BROWSER_PILOT.md)，再读当前题目的 TASK.json、REQUEST.json、WORKLOG.md、browser/binding.json。出题还须完整阅读 Skill 指定的 Insight 研究和检查单。
2. 用户现在要求转到 Windows 本地开发：Codex、Chrome、GPT/Claude 客户端及文件均由本机持有，目标是取消服务器与 PC 之间的 SSH 隧道和远程采集依赖。**这个目标尚未实现；本分支是移植起点。**
3. 首先核对本机 Python、Node、Git、Chrome、Codex、Claude Code 的实际版本和可用参数；先跑离线测试，再逐项移植。读取已有登录配置的位置，不输出内容，不复制到仓库。
4. 没有明确恢复题目时只做开发。题目 1262 已暂停，无在途请求；完整接续依赖私有原件，单独 clone 源码不含题库或题目证据。

可直接给本地 Codex：

```text
请先读 AGENTS.md 和 docs/LOCAL_DEVELOPMENT_HANDOFF.md，再核对本机环境和现有代码。
在本分支继续把浏览器出题自动化移植为 Windows 本地运行，取消对 aliyun-dev、SSH 隧道和服务器固定路径的运行依赖。
先完成离线验证与配置/路径移植，再逐项联调真实客户端；保留现有出题门槛和原件完整性。
先报告已有实测、移植缺口及第一步改动，不重新发送题目1262的Seed，不自动提交或领题。
```

## 仓库入口与已保存模块

| 部分 | 代码/文档 | 用途与边界 |
| --- | --- | --- |
| 任务与门槛 | llm_authoring/official.py、manual.py、authoring.py、cli.py | 冻结输入、先 Seed、三模型门槛、原件导入及评分绑定 |
| 网页质检 | browser_automation/run-browser-checks.mjs、qa-observer.mjs；llm_authoring/browser_checks.py | 点击真实按钮、记录请求、验证输入/回执；不是直连质检 API |
| 页面绑定与连接 | browser_automation/browser-session.mjs、doctor.mjs | 精确 task/item 绑定、CDP 操作白名单、只读诊断 |
| 当前页面结果恢复 | native-check-state.mjs、capture-current-check.mjs；llm_authoring/browser_page.py | 暂只支持题目检查；真实页面结果与网络证据分开保存 |
| 豆包 | doubao-client.mjs、doubao-new-task.mjs | 官网原生成、官方复制、真实长页及横向溢出截图 |
| GPT | gpt-client.py、show-gpt-session.py | 独立 Codex 会话、原事件/上下文验证、恢复同一回答展示 |
| Claude/控制台 | model-worker.mjs、start-model-worker.ps1 | 原生 Claude Code、CMD 黑底、窗口登记/截图/翻页；当前仍依赖远端 |
| 填表 | fill-frozen-points.mjs、model-form-fields.mjs、fill-model-fields.mjs；llm_authoring/browser_form.py | 原文、备注、选择及冻结考点的受保护填写与回读 |
| 上传先例 | tools/pilot-reference/1262-seed-upload/ | 成功上传六张原图的单题参考脚本；未通用化，不能直接运行 |
| 出题规范 | skills/llm-authoring-workflow/ | 保留研究、表达规则、质检选项、返修、Arena、具名排序规则 |
| 共享记忆 | memory.py、memory_scope.py、lessons.py | 跨题查重与复核后的失败经验；数据库是私有运行数据 |

目录中的 Python/Node 测试是合成测试；不会为测试调用付费模型。Node 使用内置测试框架和全局 WebSocket，建议沿用已实测的 Node 24 系列；实际版本应记录。Python 依赖见 requirements.lock。

## 本地移植必须处理的差异

当前有意保留原实现，避免在发布交接时混入未经本机验证的重写。请按下表逐项改造并测试，不能只替换字符串后宣称可运行。

| 当前耦合 | 本地改造与完成条件 |
| --- | --- |
| scripts/setup.py 拒绝 win32；workspace.py 生成 .venv/bin/python 和 Bash 入口 | 支持本机 venv/Scripts/python.exe 与可靠的 PowerShell/CMD 启动入口，含带空格路径及 UTF-8 往返测试 |
| CDP 固定服务器 19226；PC Chrome 原端口 9226 | 可配置的回环 endpoint，直接连接本机独立 Chrome；保留回环限制、唯一绑定及操作白名单 |
| doctor/model-worker 固定私有握手路径与 19227；脚本创建 SSH -R、scp | 移除远程上传/隧道依赖；可用本机进程适配或仅回环服务，明确启动、停止及重连生命周期 |
| ensure-current-input.mjs、doubao-client、model-worker 限制 /srv/... | 从本题/父工作区配置解析真实目录，保留普通文件、路径边界、当前输入和门槛验证 |
| GPT 可执行文件、auth 路径、PARENT 固定 Linux；show 使用 os.execve | 发现本机官方 Codex，使用独立 CODEX_HOME/空目录，保留真实型号、High、prompt-only、无工具证明和同会话恢复 |
| PowerShell 中 GPT 展示仍 ssh 到服务器，含短题测试的旧会话特判 | 改为本机 GPT 生成/登记/恢复，取消测试会话特判；Claude 保留新原生隔离会话和黑底 CMD |
| POSIX mode、chmod、/tmp 和文件锁假设 | Windows 权限/ACL、临时目录及并发锁有实际验证；不能只删除隐私和防重入检查 |
| 旧 shared-memory.json 是服务器绝对路径与三个成员 | 迁移私有主库后建立合法本地作用域；配置失效不是空库，不重新初始化覆盖；见私有迁移说明 |

建议顺序：路径/环境配置与离线回归 → 本机 Chrome 只读绑定/表单回读 → 豆包原件与截图 → GPT 原生成/恢复 → Claude 原生成/恢复 → 通用原图上传 → 同题三模型门槛后的并行网页质检 → Arena 人工接续、排序和提交。不要在迁移连接时误点旧题、重发未知请求或套用旧提交授权。

现有 workspace-create 的默认值和 templates/AGENTS.md 仍服务手动模式。服务器浏览器父目录是单独初始化、设置 TASK 的 platform_check_mode=browser、response_mode=official_clients、model_contract 及页面绑定后启用的；不能把默认新建的手动题当作已启用自动化。本地移植需增加明确的浏览器开发 profile 与相应任务指引，保留手动模式兼容，并测试生成的入口实际可运行。

独立 Chrome 调试端口只监听本机。先让用户正常登录 AIDP、豆包；不要将浏览器 profile、Cookie、auth.json、握手 token 纳入代码。保持页面前台，最小化会影响真实截图；先恢复窗口并核对，不能用渲染图填补。

## 必须保留的业务行为

- 所有模型收到的文本逐字节等于冻结 prompt；不附加 Markdown 指令、Insight、考点、上下文或题库。
- 真实指定型号和推理强度有证据后才导入/评分。当前浏览器试验合同是 Seed 2.1 Pro High、GPT-5.6 sol High、Claude Opus 4.6 High。其他旧题仍按各自 TASK 合同。
- 用户明确 Seed 只使用 www.doubao.com，允许官网工作模式联网，不使用火山方舟替代。GPT、Claude 沿用无工具适配器。保留实际差异，不宣称三者工具完全一致。
- Seed 全部决定性点达成则淘汰候选，不收后两者；Seed 未全达成后，在创建 GPT/Claude 请求前询问并记录本题是否执行后两项质检。三份原文齐备且 GPT/Claude 至少一个全部达成才允许后两项检查；两者都不达成则改新 prompt，不浪费检查。
- 题目难度/标签固定进行。若用户选择执行后两项，三模型原文、逐点判断与备注完成后并行点击考点、达成性检查，按各自 requestID 追踪。正常请求无完成时间上限；传输超时、服务异常、内容不通过和未知结果必须区分。
- 未知请求先核对原页面和日志，不自动重发；503/504 已完整结束后保留原件并记录重试原因。错误质检保留原“不通过”和输入绑定的异议，不改称通过。认可问题按研究依据修复，同 prompt 原文统一重评，prompt 改变才重新采集。
- 三项实际通过的表达建议可先发 Arena 填写提示、再离线优化，另存记录且说明未复检；不得实质改变考点、判定门槛和采集中的 prompt。
- 保留自然的单一核心问题、明确的决定因素、原子考点、等价有效路径；不按 Seed 的回答事后加隐藏限制。冻结标准先于模型调用。
- 原 Markdown 可含链接、JSON 代码框和文字框架；富媒体不能删掉后冒充完整纯文本。型号/High/完整回答须来自真实官方客户端截图，表格还要核对横向覆盖；未实际看图不能勾选核验。
- Arena 仍由用户正常交互获取随机两模型原件和截图，不实现验证码绕过。五模型按核心考点具名排序，同分并列，交付六份 Markdown，不生成交付 ZIP。
- 正式提交、领题循环需本次实际授权及平台成功证据；历史题458的提交授权不能用于1262。代码发布不授权发送新模型问题或恢复题目。

## 题目1262接续提示

服务器最新尝试目录是 `/srv/llm-authoring-browser-lab/tasks/1262-plants`，父默认已指向该题；旧厨房 `tasks/1262`、摄影 `tasks/1262-photo` 都是历史失败证据，不能当当前候选。

当前植物 r0002：题目难度/标签网页检查真实通过，难度7；Seed 正式原文已核验，决定性点1/2达成，六张真实图及原文/判断已填入网页。只有 Seed 先行门槛通过，**尚不是最终合格题**。

没有 GPT/Claude 请求，没有后两项质检、Arena 或提交。用户上次暂停以便换电脑，尚未回答本题后两项质检“需要/不需要”；必须等待实际选择，不能把“稍等”记成某个选项。

原题、Insight、考点、原回复、截图和浏览器回执不进公开 Git。要接续同题，先按 [PRIVATE_STATE_TRANSFER.md](PRIVATE_STATE_TRANSFER.md) 取私有快照并逐文件验 SHA，再读真实任务文件。保留既有冻结 ID、哈希和评分；不要用本文摘要重建或重新生成 Seed。

## 开发及验证边界

离线回归可在未登录模型时运行：

```text
python -m unittest discover -s tests
node --test browser_automation/test-*.mjs
```

Windows CMD 不会展开 `test-*.mjs` 时，由 PowerShell 枚举测试路径并逐一传给 Node，或让 Codex 用 subprocess 的参数列表枚举，不能据此省略测试。

所有本机联调分开记录“合成验证/历史实测/本次真实结果/未验证”，并写进 [AUTOMATION_VALIDATION.md](AUTOMATION_VALIDATION.md)。保持服务端旧源码、旧题原件与旧交付，不 pull、reset 或清空它们。新分支按用户授权发布；以后合并 main 仍须用户指示。
