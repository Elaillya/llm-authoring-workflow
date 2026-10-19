# 选择、资料、自然题面与多样性

1. 先按 `begin.next_question` 逐项记录大方向、子方向与题型。新题大方向提供计算机科学、商科和生活娱乐。CS的四类及商科菜单见 `config/domains.json`；已有冻结题保留原领域与题型，不强迫重新选择。用户只选择范围，不承担场景/事实生成。
2. 每次开始或恢复先读begin.memory_context.failure_learning或failure-context中的认可经验及适用边界；待复核观察先按repair.md分析，不直接当规则。memory-context的database/scope/member_workspaces标明实际题库，已配置共享组时覆盖所有成员，不能据本父目录无sqlite文件就称题库为空。再读取 `begin.memory_context.topic_index` 或 `memory-context` 的全库题面、机制和评分目标索引，必要时 `memory-show <ID>` 看原题。综合已有记录选择实质不同的对象、目标、约束、推理主线和考点评分结构。多样性不等于把同一个问题换成不同名词、数字和口吻。
3. 商科运行 `business-references --subdirection <ID>`，以 `rules/business-reference.json` 的来源和机制卡定位原始资料。逐题核实条件、结论和当前事实，记录 `drafts/sources.md`，区分教材机制、构造场景和真实数据；资料索引及场景种子不是已验收题。CS按所选情境查适当的课程/技术/原始研究资料。生活娱乐按[lifestyle.md](lifestyle.md)分层选范围、分页读匹配机制与原始资料，缺口由助手先补查，不把个人偏好当唯一答案。
4. 按 `rules/natural-diverse.md` 和 `writing.md` 写自然题面：日常类普通人读得懂；课程题可用课程概念；科研/生产题可专业，但必须有现实目标与可观察证据。保持≤100字符、必要事实、明确方向，不泄露解题路线。Insight按实际推理选择段落或层次，必须点明决定性因素及其作用；考点精简背景，每条只判断一个具体事实、关系或行动，不复制通用句式。
5. 编辑 `drafts/question.json`：先完成匹配选择的prompt和Insight，按`platform-checks.md`做题目难度与标签检查，修订到通过后再补齐考点。填写有信息量的design_profile；商科绑定适用的business_mechanisms/business_references；生活类绑定lifestyle_mechanisms/lifestyle_references及必要的本题补充卡。根据专业依据定考点，不从模型回复倒推。
6. 先 `design-check drafts/question.json`，再 `design-review-template drafts/design-review.json --question drafts/question.json`。助手读全库索引，在semantic_screen确认全部已读ID和理由，补上文本召回漏掉的近题。逐项填写自然度与语义差异依据；相似则改题，高分不等于一定重复，低分不等于一定不同。详细字段与并发行为见工具仓 `docs/LOCAL_MEMORY.md`。
7. `candidate-reserve drafts/question.json` 先登记候选，随后 `freeze drafts/question.json`。如果其他窗口增加了题库或题目/来源变化，先重新复核。该复核由助手完成，不向用户额外索取批准。
8. 冻结后完成 `self-review-template evaluations/self-review-rNNNN.json` 和原有作者自查，再进入Seed。题面改变需新版本和回复；只改考点/Insight统一重评。放弃的完整候选按原因memory-record为rejected，不删除失败记录。
