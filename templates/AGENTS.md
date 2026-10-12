# 第一轮出题

先读 `.agents/skills/llm-authoring-workflow/SKILL.md`、`REQUEST.json` 与 `WORKLOG.md`。工具仓 `{{TOOL_ROOT}}`；规则为其中 `rules/authoring.md`。工作区工具：`{{WORKSPACE_ROOT}}/bin/lab`。题目ID：{{TASK_ID}}。

运行 `lab begin`。每道题先请用户从分析决策类、开放推荐类、How-to类中选择；首次缺配置时提示填写父工作区 `local/providers.json` 的三个模型。使用私有文件保存密钥。

默认计算机科学。用户选择题型后，问题、事实、限制由助手生成并通过官方文档、论文或源码核实；材料为空也能开始。用构造场景表达工程需求，来源与假设分开记录。

本流程完成三模型验证、作者自查和出题交接即结束。需要模型服务修复或不可独立取得的事实时再请求必要输入。每个检查点更新简短 WORKLOG，保留版本、负结果和原件。
