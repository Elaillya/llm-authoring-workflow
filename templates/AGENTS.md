# 完整出题与五模型排序

先读.agents/skills/llm-authoring-workflow/SKILL.md、TASK.json、REQUEST.json与WORKLOG.md。工具仓{{TOOL_ROOT}}，专业规则为其中rules/authoring.md。工作区命令{{WORKSPACE_ROOT}}/bin/lab，题目{{TASK_ID}}。

运行lab begin与lab status，新题先询问专业领域并用lab choose-domain记录，再询问题型；不提示或使用模型API配置。问题、事实和限制由助手按所选领域生成并核实来源。已有冻结题目继续原领域与题型，保留成果。

冻结候选后按Skill创建Seed填写文件并等待用户提供完整Markdown，导入和判断Seed；其未达成全部决定性点才创建GPT/Claude文件并等待用户填好。禁止collect/recover/render，禁止补写模型回复或伪造官方页面。

已有题面、三模型证据或交付时保留原件并接续缺失步骤。三模型门槛通过后创建两份Arena Markdown填写文件，用户只填型号和完整回复，所有官方网页截图由用户自己提交。再统一评估五模型全部考点、排序并生成完整提交。具体步骤见Skill的references/arena-rank.md。

不设置独立质检阶段；既有作者自查复用。每个检查点更新WORKLOG，保留版本、负结果和原件。完成条件是完整五模型字段、排序与具体理由、新交付及哈希清单，不能止于旧三模型handoff。

交付为提交信息.md和五份按模型名称命名的原回复Markdown，分别给出可点击链接。排序和备注直接使用真实模型名称，交付过程不生成ZIP。改名时按工具仓docs/HANDOFF.md保留冻结ID与原件。
