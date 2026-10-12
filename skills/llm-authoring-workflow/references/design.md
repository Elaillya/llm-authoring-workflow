# 选题与自查

确认 REQUEST.json 已记录用户选择。计算机科学场景、关键事实与限制由助手生成。先核实官方文档、论文、源码中的机制，写 drafts/sources.md，区分有依据的机制与构造场景设定；不虚构用户经历和同行认同。

编辑 drafts/question.json：题型与选择一致、题面≤100字符、Insight分机制/优先级/结论、author_notes包含来源/设定/适用边界、points包含具体决定性标准及可选辅助标准。按 rules/authoring.md 检查本题型，朗读题面检查自然表达和必要条件。

运行 `lab freeze drafts/question.json`，然后 `lab self-review-template evaluations/self-review-rNNNN.json`。逐项填写 passed与reason，reviewer记录实际作者/AI自查者。自查说明应指出本题具体事实和机制；不以“已自查”代替理由。

查看回复后修订题面创建新冻结版本并重新采集；只改考点统一重评三模型，同时更新自查。保留仍成立的内容和原来的负结果。
