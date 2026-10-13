# Arena Markdown与五模型排序

1. 先lab check当前三模型评估。通过后lab arena-prepare --evaluation evaluations/three-rNNNN.json。工具创建arena-input/rNNNN/model-4.md、model-5.md和arena-prompt.md。向用户给出这三份文件的可点击链接，让用户在Search + Battle新会话获取随机两模型，填两份MD的model_name及原回复全文。截图用户自己提交，直接等待用户说已填好；不要要求创建文件、填额外配置或提供图片。
2. 用户填好后lab arena-import。缺内容、非Markdown、重复/禁用型号或题面不一致时，只指出对应文件需修正；原件不覆盖，不能从API制造随机Arena模型。
3. lab five-evaluation-template evaluations/five-rNNNN.json --authoring-evaluation evaluations/three-rNNNN.json。模板已带入前三个决定性判断；按同一冻结标准补Arena决定性点和五模型全部非决定性点。逐项met为布尔值，具体reason及准确quotes。缺证据不可写false。lab five-check evaluations/five-rNNNN.json。
4. lab ranking-template evaluations/ranking-rNNNN.json --evaluation evaluations/five-rNNNN.json生成与判断绑定的次序和备注草稿。全部决定性点达成梯队优先，同梯队按全部考点满足数，相同并列，绝不因模型品牌、文风或长度打破同分。润色summary及五个真实模型的具体考点说明，至少500字。保持工具生成的groups、order和display_names。lab ranking-check evaluations/ranking-rNNNN.json --evaluation evaluations/five-rNNNN.json。旧编号记录可直接校验和导出，工具将展示转换为真实名称。
5. lab export --evaluation evaluations/five-rNNNN.json --self-review evaluations/self-review-rNNNN.json --ranking evaluations/ranking-rNNNN.json --output delivery/v002（选未用版号）。提交信息.md汇总除回复全文以外的提交字段，models/下五份Markdown分别使用真实模型名。核对原文逐字节、全部判断、具名排序/理由、输入原件与manifest。全部官方网页截图由用户单独提交。更新WORKLOG与Git检查点，分别给出提交信息及五个模型文件的可点击链接；直接使用Markdown，不打ZIP或另建合并回复文件。

旧三模型材料逐字节保留。五模型模板和新交付是新增产物。旧handoff中的上下轮分工属于旧版历史，当前流程从已有证据继续到完整排序，不插入独立质检阶段。
