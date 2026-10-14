# 三模型验证与出题检查点

运行lab evaluation-template evaluations/three-rNNNN.json，逐项填写全部决定性考点met/reason/quotes，满足需原文准确引用；缺证据保持null。已有同版本判断复用。

lab check evaluations/three-rNNNN.json验证Seed未全部决定性达成、GPT/Claude至少一个全部达成。作者自查复用同版本和依据哈希有效的文件；只有依据或题目改变时更新。辅助点不影响三模型出题门槛，进入五模型排序时统一补评。

有旧delivery检查点直接保留。需要中途保存时用lab checkpoint --evaluation evaluations/three-rNNNN.json --self-review evaluations/self-review-rNNNN.json --output delivery/v001。检查点只有三模型，不是最终完成；继续references/arena-rank.md。

新任务在检查点及Arena之前按platform-checks.md完成考点与达成性质检。合理反馈自主返修；错误意见登记本次输入/返回绑定的证据异议并向用户给出表单备注。该门禁由命令校验，不能只凭三模型区分度通过就进入Arena。

题面改变获取新回复，考点改变统一重评全部已获取模型。旧原件和交付始终保留。
