# 三模型判断与交接

运行 `lab evaluation-template evaluations/three-rNNNN.json`，读取冻结考点与每份完整reply.md。填写reviewer，每个决定性点的met、reason、quotes；满足需要原文准确引用，不满足说明缺失或冲突。无法判定保持null并补证据。非决定性点留在题目内，第一轮不用其达成性控制出题门槛。

`lab check evaluations/three-rNNNN.json`计算全部决定性达成：Seed必须未全部达成，GPT或Claude至少一个全部达成。未过时保留结果，依据真实专业问题修订，不改变标准迎合差异。

复核当前自查、引用与整体判断的一致性、模型实际版本/推理模式、完整截图、来源说明。运行 `lab export --evaluation evaluations/three-rNNNN.json --self-review evaluations/self-review-rNNNN.json --output delivery/v001`。

核对出题提交.md/fields.json/三份原文/三张图与manifest。没有辅助点时字段为“无”。handoff.json标明第一轮结束且第二轮独立质检待进行。向用户给出交接包路径，更新WORKLOG和题目Git检查点。完成本轮，不继续其他模型或排序。

返修按原因调整，实质改题面重取回复、改考点统一重评。用v002等新目录交接；不认可质检意见时给可复核专业依据与未修改理由。
