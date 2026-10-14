---
name: llm-authoring-workflow
description: 完成开放难题第五期完整出题与五模型排序。先选计算机科学或商科及子方向、题型，查本地题库和适用资料，审核自然题面与Insight/考点差异后冻结候选，先收用户填写的Seed Markdown，判断未全部达成后收GPT/Claude Markdown，再收Arena两份Markdown、评估五模型和排序，交付六份MD；不调用API、不生成截图。
---

# 完整出题与五模型排序

先读当前题目 AGENTS.md、TASK.json、REQUEST.json、WORKLOG.md 及工具仓 rules/authoring.md。路径见 TOOLKIT.md，命令为父工作区 bin/lab。首次仅有工具仓时按 README 准备环境并建工作区，不索取 API 配置。

1. 运行 lab begin 与 lab status，按next_question先询问计算机科学/商科，再询问菜单子方向，最后记录三种题型。计算机科学提供日常AI与学习、大学课程、研究生科研、真实生产四类；商科提供经核验资料支持的七类。已有选择直接记录，旧冻结题沿用原选题。具体菜单来自config/domains.json，不要求用户提供专业场景和关键事实。
2. 未冻结时按references/design.md读取父工作区本地题库与专业资料，设计自然、实质不同的题面/Insight/考点，完成design-check、语义复核和candidate-reserve，再冻结。商科必须使用适用的参考卡并核对原始资料。已有冻结版本、原件和判断从缺失步骤接续。全局Codex记忆不参与本地题库。
3. 按 references/collect.md 创建 Seed Markdown 填写文件，给出 prompt 和填写文件的可点击链接，等待用户填写。导入后按全部决定性点判断；未全部达成才创建 GPT 和 Claude 的文件。三模型完整原文和判断齐备后，按 references/evaluate-deliver.md 验证门槛及作者自查。
4. 门槛通过后按 references/arena-rank.md 创建 Arena 两份 Markdown。用户填真实型号和原文。全部模型的官方网页截图由用户自己提交，不要求上传图片或额外配置。
5. 用户填好后导入，统一判断全部考点，按真实名称排序并校验理由。交付提交信息.md和五份按模型名命名的原回复，各给可点击链接，更新 WORKLOG 和 Git 检查点，不生成 ZIP。

材料齐备时连续推进。完成条件是五份完整原 Markdown、同版考点判断、合规型号、具名排序及至少500字理由、完整提交字段及 manifest。原件和负结果保留。缺少回复或型号不能确认记为证据不足；禁止补写模型答案或伪造网页。用户提供的 Markdown 不代表工具独立核验了网页或甲方验收。
