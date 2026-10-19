---
name: llm-authoring-workflow
description: 完成开放难题第五期完整出题与五模型排序。选领域/子方向和题型，读题库及失败经验，题面与Insight固定先查难度标签；冻结后先Seed，再询问是否进行后两项质检并收GPT/Claude Markdown。选择需要才在三模型门槛后并行质检，选择不需要则跳过两项进入Arena；收两份随机模型MD、排序交付六份MD。认可失败先修标准、再征求换回复、最后改题；错误意见给证据异议。模型回复手动、截图用户另交。
---

# 完整出题与五模型排序

每次开始或恢复先用memory-context/failure-context读取当前记忆。默认同父目录；若已配置local/shared-memory.json，按返回的database与member_workspaces读写同一题库和失败经验，不自行复制或新建空库。共享后保留现有候选、资料和冻结证据；未冻结设计复核过期才刷新比较，不重置任务。详情见工具仓docs/LOCAL_MEMORY.md。

先读当前题目AGENTS.md、TASK.json、REQUEST.json、WORKLOG.md，以及工具仓rules/authoring.md。路径和命令见TOOLKIT.md。首次仅有工具仓时按README创建工作区，不索取模型API配置。共用平台配置已附带；需要时只给已有Cookie文件让用户填写登录态。设计与交付表达读references/writing.md：自然prompt；灵活Insight突出决定因素；原子考点；作者字段纯文本；五份模型原Markdown保持，发送文字逐字等于prompt。

1. lab begin/status先选计算机科学、商科或生活娱乐，再选子方向、题型，已有明确选择直接记录。生活娱乐按references/lifestyle.md分层选或确认当前范围；商科按资料库选范围。场景、事实和依据由助手构造并研究，使用references/design.md读共享题库和认可失败经验。旧“生活爱好类”只作兼容，冻结与原证据不改。
2. 按references/writing.md先把prompt收束为一个核心问题和完整问句，原因/依据融入其中，自查后再写Insight并固定按references/platform-checks.md检查题目难度与标签；合理返修复检，错误意见保留证据异议。通过后补齐考点、完成含single_core_question的设计复核/预留/冻结。已有冻结题从缺失步骤接续，保持原题面。
3. 按references/collect.md先收Seed完整Markdown并判断。Seed未全部决定性达成后，**创建GPT/Claude填写文件前必须读references/optional-model-checks.md，询问用户是否进行考点与达成性质检，等待实际答复并记录选择**；同题已有选择直接沿用。再给两份填写链接，原样导入，统一完成三模型判断与备注。
4. lab check确认three_model_gate=true：Seed未全部决定性达成，且GPT/Claude至少一个全部达成。选择需要才按references/platform-checks.md用qa-run models并行后两项，正常请求等至完成；选择不需要则去除这两个步骤，按有效题目检查及本地三模型门槛直接进入Arena。门槛失败不能通过选择跳过放行；初次失败保留负结果并换新prompt。认可考点失败按references/repair.md先修Insight/考点统一重评、再征求回复替换、最后改prompt；失败原因复核后共享。错误质检告知不认同并给可复制表单备注。
5. 按references/arena-rank.md先发Arena题面和两份填写链接。只有三项实际通过才可按原规则离线优化通过建议、免复检；跳过不声称通过。收Arena两份MD、统一五模型考点评估和具名排序，按references/evaluate-deliver.md交付提交信息.md与五份模型原MD并给链接，不生成ZIP，更新WORKLOG和Git检查点。

保留原件、失败历史和私有选择；未得到完整回复或型号不能确认是证据不足。完整交付需要五份原文、同版判断、合规型号、具名排序与具体简洁理由、纯文本作者字段和manifest。用户提交截图，工具不独立核验真实网页或甲方验收。
