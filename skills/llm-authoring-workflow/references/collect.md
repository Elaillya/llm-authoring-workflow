# 三模型手动 Markdown

不运行 collect、recover、render，不读取或提示 API 密钥，不自动调用模型，不渲染模拟官方页面。每条命令在当前题目目录执行，lab 指父工作区 bin/lab；也可显式 --task 指定该题。

1. 候选已冻结后运行 `lab model-prepare seed`。创建 model-input/rNNNN/prompt.md 与 Seed 2.1 Turbo.md，只创建 Seed 的文件。给用户两个可点击链接，让用户将 prompt 发送到对应型号官方网页的新会话，并将完整回答原 Markdown 替换占位文字保存。所有截图由用户单独提交。
2. 用户说填好后运行 `lab model-import seed`，再 `lab seed-evaluation-template evaluations/seed-rNNNN.json`，逐项填 met/reason/quotes；满足必须有原文准确引用，缺证据保持 null。运行 `lab seed-check evaluations/seed-rNNNN.json`。
3. 若 Seed 全部决定性达成，保留真实结果，按专业依据修订候选并冻结新版本；新题面重新提供 Seed 回复，不提前要求 GPT/Claude。若 Seed 未全部达成，运行 `lab model-prepare gpt` 和 `lab model-prepare claude`，分别创建同目录的 GPT-5.6 sol.md 与 Claude Opus 4.6.md，给出可点击链接，等待用户填好。若判断保存在其他路径，prepare/import 均显式传 --seed-evaluation；默认使用当前版本标准 seed-rNNNN.json。
4. 用户填好后分别 `lab model-import gpt`、`lab model-import claude`。prepare 和 import 都验证当前版本 Seed 判断，不能用旧版本或未判定结果越过门槛。GPT/Claude 使用项目要求的中高推理模式，全部发送严格等于冻结prompt的文字，不追加格式要求，不携带 Insight 或考点。网页不能确认规定型号时停在缺材料处，不能换型号或修改名称冒充。

输入文件仅为原回复正文，不另加标题、出处声明或包装；原回答已有代码块等格式完整保留。工具保留用户原始字节、metadata 和冻结题面绑定。未填、截断、格式损坏均不作为未达成；请用户修正对应文件。导入幂等，已保存原件不可覆盖。只改 Insight 或考点而题面不变时，复用完整原回复并统一重评；题面改变时使用新输入版本。历史 API 原件仅兼容读取，不重新采集。旧版带格式指令的输入按writing.md保留真实合同，不能改写采集历史。
