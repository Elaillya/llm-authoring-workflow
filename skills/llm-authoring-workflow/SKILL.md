---
name: llm-authoring-workflow
description: 完成开放难题第五期完整出题与五模型排序。选领域/子方向和题型，查本地题库，题面与Insight先平台检查，冻结后先Seed再GPT/Claude Markdown，齐备后并行考点及达成性质检，等待至完成；错误意见给证据异议备注。门禁满足后先发Arena链接，再离线优化通过建议免复检，收两份MD、排序交付六份MD；模型回复手动，平台质检可自动调用。
---

# 完整出题与五模型排序

先读当前题目 AGENTS.md、TASK.json、REQUEST.json、WORKLOG.md 及工具仓 rules/authoring.md。设计、判断和交付的表达按references/writing.md：发送文字严格等于prompt；Insight形式灵活但突出决定性因素，考点精简背景且独立可判定，作者字段用纯文本，排序理由简洁。路径见 TOOLKIT.md，命令为父工作区 bin/lab。首次仅有工具仓时按 README 准备环境并建工作区，不索取模型API配置。同项目质检配置已自带，缺失时自动导入，不要求用户提供HAR/service.json；需要质检时仅给已有Cookie文件让用户填写自己的登录态。

1. 运行 lab begin 与 lab status，按next_question先询问计算机科学/商科，再询问菜单子方向，最后记录三种题型。计算机科学提供日常AI与学习、大学课程、研究生科研、真实生产四类；商科提供经核验资料支持的七类。已有选择直接记录，旧冻结题沿用原选题。具体菜单来自config/domains.json，不要求用户提供专业场景和关键事实。
2. 未冻结时按references/design.md读取题库和资料，写自然题面与Insight后，必须按references/platform-checks.md执行题目难度与标签检查；合理问题自主修订再检。通过后补齐考点，完成多样性复核、candidate-reserve和冻结。商科核实参考卡边界。已有冻结版本和原件从缺失步骤接续，全局Codex记忆不参与题库。
3. 按 references/collect.md 创建 Seed Markdown 填写文件，给出 prompt 和填写文件的可点击链接，等待用户填写。导入后按全部决定性点判断；未全部达成才创建 GPT 和 Claude 的文件。三模型完整原文和判断齐备后，按 references/evaluate-deliver.md 验证门槛及作者自查。
4. 三个模型原文、判断及备注齐备后，按references/platform-checks.md用qa-run models并行考点及达成性质检；正常请求持续等待至完成，合理不通过返修复检。任何内容检查的错误意见按该引用登记证据异议，立即告知不认同并给出可复制备注。门禁与三模型门槛满足后按references/arena-rank.md先发Arena填写链接，再离线处理三项实际通过的表达建议，保持题面、专业含义和判定，优化后免复检。缺失/过期Cookie填已有私有文件；网页截图用户另交。
5. 用户填好后导入，统一判断全部考点，按真实名称排序并校验理由。交付提交信息.md和五份按模型名命名的原回复，各给可点击链接，更新 WORKLOG 和 Git 检查点，不生成 ZIP。

材料齐备时连续推进。完成条件是五份完整原 Markdown、同版考点判断、合规型号、具名排序及简洁具体的五模型考点理由、纯文本提交字段及 manifest。原件和负结果保留。缺少回复或型号不能确认记为证据不足；禁止补写模型答案或伪造网页。用户提供的 Markdown 不代表工具独立核验了网页或甲方验收。
