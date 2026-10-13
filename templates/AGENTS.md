# 完整出题与五模型排序

先读.agents/skills/llm-authoring-workflow/SKILL.md、REQUEST.json与WORKLOG.md。工具仓{{TOOL_ROOT}}，专业规则为其中rules/authoring.md。工作区命令{{WORKSPACE_ROOT}}/bin/lab，题目{{TASK_ID}}。

运行lab begin与lab status，新题才询问题型，首次缺配置才提示父工作区local/providers.json。默认计算机科学，问题、事实和限制由助手生成并核实来源。

已有题面、三模型证据或交付时保留原件并接续缺失步骤。三模型门槛通过后创建两份Arena Markdown填写文件，用户只填型号和完整回复，截图由用户自己提交。再统一评估五模型全部考点、排序并生成完整提交。具体步骤见Skill的references/arena-rank.md。

不设置独立质检阶段；既有作者自查复用。每个检查点更新WORKLOG，保留版本、负结果和原件。完成条件是完整五模型字段、排序与具体理由、新交付及哈希清单，不能止于旧三模型handoff。
