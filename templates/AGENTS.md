# 完整出题与五模型排序

先读.agents/skills/llm-authoring-workflow/SKILL.md、TASK.json、REQUEST.json与WORKLOG.md。工具仓{{TOOL_ROOT}}，专业规则为其中rules/authoring.md。工作区命令{{WORKSPACE_ROOT}}/bin/lab，题目{{TASK_ID}}。

同项目质检配置已自带；本地缺失时工具自动导入或qa-setup --default，不再要求用户提供HAR/service.json。需要时给已创建Cookie文件让用户填自己的登录态。已有私有配置及Cookie保持。

设计、判断和交付按Skill的references/writing.md：五模型提问严格等于冻结prompt，不追加格式指令；Insight灵活组织但必须突出真正决定性因素；考点少写背景、一条判断一件事，保留必要边界。Insight、考点、达成性与排序说明用纯文本；排序备注简洁说明差异和原因，不设500字下限。五份模型原Markdown保持不变。

运行lab begin与lab status，新题先询问计算机科学、商科还是生活爱好类，用lab choose-domain记录；再按begin菜单询问子方向并choose-subdirection，最后询问题型；不提示或使用模型API配置。问题、事实和限制由助手生成并核实来源。设计前读取父目录本地题库；按Skill的references/design.md完成自然表达、场景、Insight和考点差异检查及预留后冻结。商科使用对应参考库并核实本题适用性；生活爱好按Skill的references/lifestyle.md分层选范围，读取匹配卡与来源，缺口由助手先补查。已有冻结题目继续原领域与题型，保留成果。

冻结候选后按Skill创建Seed填写文件并等待用户提供完整Markdown，导入和判断Seed；其未达成全部决定性点才创建GPT/Claude文件并等待用户填好。禁止collect/recover/render，禁止补写模型回复或伪造官方页面。

已有题面、三模型证据或交付时保留原件并接续。新任务按Skill的references/platform-checks.md：prompt与Insight后先做难度标签检查，修订复检再冻结；三模型原文、判断及备注齐备后先lab check，必须读取three_model_gate=true才用qa-run models并行做考点和达成性质检；Seed须未全部决定性达成，GPT或Claude至少一个全部达成。初次两者都未达成则保留负结果、记rejected并重新选题生成新prompt；认可后期考点失败后的修复分支见references/repair.md，不调用后两项质检，不能放宽标准或改判来过门槛。正常请求等待到完成，不设客户端等待上限；持续报告并等待原进程。合理不通过自主返修；错误意见登记证据异议，立即告知不认同并给出可复制备注。门禁与三模型门槛满足后先发Arena填写链接，三项实际通过的优化建议此后离线处理，保持题面、专业含义与判定，优化后不再调用质检。缺失/过期Cookie填已创建父目录私有文件。模型生成API仍禁用，平台质检允许调用；截图用户另交。旧任务按原合同续作。

不设置独立质检阶段；既有作者自查复用。每个检查点更新WORKLOG，保留版本、负结果和原件。完成条件是完整五模型字段、排序与具体理由、新交付及哈希清单，不能止于旧三模型handoff。

交付为提交信息.md和五份按模型名称命名的原回复Markdown，分别给出可点击链接。排序和备注直接使用真实模型名称，交付过程不生成ZIP。改名时按工具仓docs/HANDOFF.md保留冻结ID与原件。

认可考点质检不通过时按Skill的references/repair.md修复：优先保持prompt修Insight/考点、统一重评；仍不能满足门槛先询问用户是否重新提供GPT/Claude原文，替换不可行才改prompt。设计前读failure-context；模型门槛失败及平台实际不通过自动记观察，由助手复核原因、改进和范围后在同父目录共享，错误/未确认意见与服务故障不作为可靠经验。原回复替换须本次明确同意并归档，不自动反复抽取。
