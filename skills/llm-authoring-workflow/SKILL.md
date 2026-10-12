---
name: llm-authoring-workflow
description: 完成开放难题第五期第一轮出题：开始时选题型，首次配置三个模型，自动构造并核实计算机科学场景，写Insight与考点，验证三模型、保存Markdown截图、作者自查、交付出题包；返修时依据冻结版本重评。
---

# 第一轮出题

先读当前题目 AGENTS.md、REQUEST.json、WORKLOG.md，以及工具仓的 `rules/authoring.md`。工具仓路径见当前题目 TOOLKIT.md；命令为该工作区 `bin/lab`。首次只有工具仓时按其 README 建立独立工作区。

1. 运行 `lab begin`。用户未给题型时先询问分析决策类、开放推荐类、How-to类三选一；用户选择后 `lab choose-type 类型`。缺模型配置时提示填写工具显示的私有 providers.json，列出Seed 2.1 Turbo、GPT-5.6 sol、Claude Opus 4.6。其他背景由助手生成，勿要求用户填问题或限制。
2. `begin`就绪后按 `references/design.md` 设计并冻结题目及作者自查。
3. 按 `references/collect.md` 获取同一题面的三模型原文与截图。
4. 按 `references/evaluate-deliver.md` 逐项判断、自查、导出交接。第一轮完成后结束，第二轮通过交接文件独立启动。

连续推进材料已具备的步骤。网络或模型身份问题保留证据；实际不能独立获得的必要信息才请求用户。每个检查点更新短 WORKLOG，绑定真实路径与当前版本。完成条件为三个完整真实回复、版本一致的决定性判断、区分度、自查、完整截图与第一轮交接字段齐全。
