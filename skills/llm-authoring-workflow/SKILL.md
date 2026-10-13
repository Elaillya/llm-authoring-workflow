---
name: llm-authoring-workflow
description: 完成开放难题第五期完整出题与五模型排序，或从旧三模型检查点接续：新题先选题型并首次配置三模型，生成计算机科学场景与Insight/考点，三模型验证，创建Arena两份Markdown填入文件，五模型评估和排序，导出完整提交。
---

# 完整出题与五模型排序

先读当前题目AGENTS.md、REQUEST.json、WORKLOG.md及工具仓rules/authoring.md。工具路径见TOOLKIT.md，命令为工作区bin/lab。首次只有工具仓时按README创建工作区；更新已建工作区用workspace-update。

1. 运行lab begin与lab status。新题尚未选类型时询问分析决策类、开放推荐类、How-to类并choose-type；首次缺配置时提示填写私有providers.json。已有题型或配置直接复用，背景由助手生成。
2. 当前题目未冻结时按references/design.md设计并冻结；已有冻结版本、原件和判断时从缺失步骤继续，保留旧交付。
3. 只有缺失API证据时按references/collect.md获取三模型原文和图，Seed先筛查。按references/evaluate-deliver.md完成决定性判断及作者自查。已有完整证据不重新调用。
4. 三模型门槛通过后按references/arena-rank.md创建Arena两份MD、给用户可点击路径，等待填入。用户只填真实型号和原文，Arena图自行提交，不索要截图或额外清单。
5. 用户填好后导入，统一评估五模型全部考点、排序、校验500字理由、导出新的完整提交目录并更新WORKLOG。

材料齐备时连续推进。完成条件是五份完整真实Markdown、同一版本考点判断、合规的型号、排序与具体理由、前三个模型的原API截图以及完整提交字段与manifest。原件、负结果和历史版本保留；工具收到的Arena MD是用户提供，不能称为已独立核验页面或甲方验收。
