# 完整提交与旧题接续接口

2.1.0 同一工作流完成出题及五模型排序，直接交付Markdown。旧三模型handoff和delivery是历史检查点，保留原文；不需要交给另一个质检workflow。

workspace-update更新既有工作区侧栏说明和工具路径，自动查找当前冻结版本通过门槛的三模型评估并创建Arena填写文件。题面、考点、原文、判断、自查、私有配置和旧交付不改写。

Arena输入为arena-input/rNNNN/model-4.md与model-5.md。model_name记录真实完整型号，分隔线下是原Markdown。request.json由工具绑定冻结题目。导入同时检查两份输入，保留不可变原件及哈希；不要求截图。截图由用户单独提交甲方，页面模式/随机性不是工具已核验的事实。

完整导出handoff.json的kind为llm_complete_submission，schema_version=1，记录版本、题目哈希、seed/gpt/claude/arena_1/arena_2顺序、出题门槛和排序，next_workflow为platform_submission。fields.json包含题目、题型、Insight、两类考点、五个模型完整Markdown/达成性/理由、排序与排序理由。

展示名称来自实际回复元数据，排序及备注全部使用型号。evaluation.json评估全部核心考点；authoring-evaluation.json为前三个模型决定性点的兼容检查视图。ranking.json绑定完整evaluation哈希；全部决定性达成梯队优先，同梯队按全部满足数排序，相同并列。备注至少500字，结构为总结＋五个具名模型的具体考点情况。旧版编号order仍可校验，新导出转换成真实名称，保留旧判断。

旧delivery/v001保留，完整结果用v002等新目录。manifest.json覆盖五原文、判断、排序、三API截图及来源证据的文件哈希。软件导出完成不等于甲方平台验收完成。

用户复制的文件为提交信息.md及models/下五份按实际模型名称命名的原Markdown；提交信息仅链接原文，不内嵌全文。JSON、API截图和evidence/保留来源与检查记录，不生成交付ZIP。export/checkpoint返回markdown及model_markdown路径，助手给出这些文件的可点击链接。

rename调整目录与TASK.json.display_id，保留TASK.json.task_id及冻结版本中的task_id，以免原评估与回复绑定失效。新候选仍沿用该内部task_id，提交编号取display_id。旧路径保留为工作区内别名，默认入口更新；升级只处理真实题目目录。每个题目有独立Git，新增题目不复制旧题内容。
