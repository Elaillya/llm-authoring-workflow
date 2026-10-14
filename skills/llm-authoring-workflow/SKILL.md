---
name: llm-authoring-workflow
description: 完成开放难题第五期完整出题与五模型排序。选领域/子方向和题型，查本地题库，题面与Insight先做平台难度标签检查，冻结后先收Seed再GPT/Claude Markdown，做考点及达成性质检并返修；错误结论保留证据、说明异议与填表备注。门禁通过后收Arena两份MD、评估排序并交付六份MD；模型回复不调用API，平台质检可自动调用。
---

# 完整出题与五模型排序

先读当前题目 AGENTS.md、TASK.json、REQUEST.json、WORKLOG.md 及工具仓 rules/authoring.md。路径见 TOOLKIT.md，命令为父工作区 bin/lab。首次仅有工具仓时按 README 准备环境并建工作区，不索取 API 配置。

1. 运行 lab begin 与 lab status，按next_question先询问计算机科学/商科，再询问菜单子方向，最后记录三种题型。计算机科学提供日常AI与学习、大学课程、研究生科研、真实生产四类；商科提供经核验资料支持的七类。已有选择直接记录，旧冻结题沿用原选题。具体菜单来自config/domains.json，不要求用户提供专业场景和关键事实。
2. 未冻结时按references/design.md读取题库和资料，写自然题面与Insight后，必须按references/platform-checks.md执行题目难度与标签检查；合理问题自主修订再检。通过后补齐考点，完成多样性复核、candidate-reserve和冻结。商科核实参考卡边界。已有冻结版本和原件从缺失步骤接续，全局Codex记忆不参与题库。
3. 按 references/collect.md 创建 Seed Markdown 填写文件，给出 prompt 和填写文件的可点击链接，等待用户填写。导入后按全部决定性点判断；未全部达成才创建 GPT 和 Claude 的文件。三模型完整原文和判断齐备后，按 references/evaluate-deliver.md 验证门槛及作者自查。
4. 三个模型及判断齐备后，必须按references/platform-checks.md依次执行考点质检、达成性质检；合理反馈自主返修并重检。错误意见登记证据异议，明确告诉用户不认同该不通过结论及如何填备注。三项检查有效且三模型门槛通过后，才按references/arena-rank.md进入Arena。缺失/过期Cookie给已创建的私有文件填写。模型网页截图由用户单独提交。
5. 用户填好后导入，统一判断全部考点，按真实名称排序并校验理由。交付提交信息.md和五份按模型名命名的原回复，各给可点击链接，更新 WORKLOG 和 Git 检查点，不生成 ZIP。

材料齐备时连续推进。完成条件是五份完整原 Markdown、同版考点判断、合规型号、具名排序及至少500字理由、完整提交字段及 manifest。原件和负结果保留。缺少回复或型号不能确认记为证据不足；禁止补写模型答案或伪造网页。用户提供的 Markdown 不代表工具独立核验了网页或甲方验收。
