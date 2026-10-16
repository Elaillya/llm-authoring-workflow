# 题目本地记忆与设计复核

本功能保存在每个父工作区的 `local/question-memory.sqlite3`，与Codex全局记忆无关。不同题目的窗口共享这一份库；不同父工作区各自独立。源码仓库不收录这份私人数据库。

## 使用顺序

新题先选择大方向、子方向和题型。`begin` 返回全库机制索引及部分完整记录；设计前阅读，必要时 `memory-context --limit 20`、`memory-show <entry_id>` 查看原题。初次 `memory-sync` 只读取正常任务目录中的冻结版本，导入题面、Insight和考点；不读模型回复、截图、密钥或归档，也不改历史冻结文件。损坏绑定会报错，不将漏读记为已覆盖。

填写 `drafts/question.json` 的 `design_profile`：

- scenario：具体人群与发生问题的情境。
- goal：答案要支持什么行动或判断。
- constraints：真正影响方案的限制。
- mechanism_tags：本题具体判断机制，不能只填“数据分析”“综合考虑”。
- point_targets：要评估的实质关系或行动，不能只填D1/D2等编号。
- reasoning_path：推理主线，记录先后或因果关系。

商科还选择参考库中适用的 `business_mechanisms` 和 `business_references`，在 `drafts/sources.md` 记录原始链接、适用条件、题设事实及边界。选择资料ID不等于资料已经足以支持本题。

1. `design-check drafts/question.json` 比较全库其他题的题面、Insight正文、整组考点和画像标签，返回分维度分数及近邻原文。
2. `design-review-template drafts/design-review.json --question drafts/question.json` 生成助手填写的复核。逐条检查自然表达、场景、Insight、考点和资料适用性；给具体理由。`semantic_screen` 要读完全库机制索引后填写全部已读ID；低文字分数不代表语义不重复。发现文本召回漏掉的近题，放入 `additional_similar_ids`，并在comparisons增加比较。
3. 每个比较写实质差异。全部高相似项均须逐条比较，不受普通近邻的展示条数限制。高相似项至少说明两个不同维度，其中涉及目标、约束、机制或评分要求。若解释不成立，就重新选题，不能只换名词、数字、语序或同义表达。此步骤由助手完成，不增加用户审批。
4. `candidate-reserve drafts/question.json` 在完整冻结前占用候选，其他窗口会看到它。`freeze drafts/question.json` 再检查当前复核并记录冻结版本；默认复核路径是 `drafts/design-review.json`。
5. 放弃的完整候选可 `memory-record drafts/question.json --status rejected --note "具体失败原因"`。保留失败原因和原候选，避免下一次又采用同一机制。完成交付后可将该版本记为delivered。

准备新复核时使用新文件名或由助手明确编辑旧文件，保留旧版记录；新文件名可通过 `candidate-reserve --review <文件>` 使用。冻结默认文件应保存当前有效复核。

## 比较什么

- 题面：同一角色、任务目标和关键约束，是否只是换了实体或数值？
- Insight：是否又在套同一条因果链/瓶颈解释/优先级判断？
- 考点：是否仍在要求同一组关系和步骤，只把对象名字替换了？
- 表达：是否过多沿用同一个开场、反问、对比句或“先验收再执行”等行文骨架？

固定的机制/优先级/结论字段、D1/D2编号和共同术语不算重复。相同底层规律可以出现在不同专业情境中，但需要能说明目标、约束、推理或评分要求的实质不同；不能仅用换背景来解释。

## 分数与边界

文本分数是归一化字符序列及三元片段相似度，画像使用标签交集。0.35起召回，0.8起标高相似；这些是待实用反馈校准的工程阈值，不是专业语义判定。跨题归一化完全相同的prompt、足够长的Insight或整组考点会阻止冻结。

自动文本比较不理解全部同义改写。助手需检查全库机制索引并打开可能相近的原题，承担语义判断；记录里的复核理由不是数学上的语义保证。不调用外部嵌入或模型API。

SQLite写事务串行化窗口间的预留/冻结；复核绑定候选、来源笔记、商科或生活资料库、生活本题补充资料和其他题的记忆快照。有其他窗口新增/改变题库记录时，旧复核失效，重新生成比较。相同任务的修订不作为跨题重复；完全相同的既有冻结版本可幂等读取。重复预留同一冻结、交付或历史版本，不将其状态降回草稿。

冻结内容先在本次临时目录写完整，再发布版本目录。写入失败只清理本次临时内容；若完整版本已写入但CURRENT指针写入失败，保留完整版本供恢复，不阻断其他题目读取。真实历史损坏仍需核对原件，不能静默跳过。

旧3.0请求与冻结版本继续读取，不强迫重设计。尚未冻结的旧任务需要新选题入口时，可显式 `selection-upgrade`，再重新选大方向与子方向；升级不会自动搬动题目或修改已冻结记录。

生活爱好候选还绑定lifestyle_mechanisms/lifestyle_references。匹配卡、来源阅读范围、空白主题补查和私有补充资料结构见[LIFESTYLE_REFERENCES.md](LIFESTYLE_REFERENCES.md)；ID与哈希只保证可追踪和复核失效条件，不证明来源确实支持题设。

3.4.0新增同库失败观察及追加复核历史，设计前读取memory_context.failure_learning。认可经验与待复核观察分开，原题库快照合同保持；记录、纠正和隐私范围见[FAILURE_LEARNING.md](FAILURE_LEARNING.md)。
