# 完整提交与旧题接续接口

2.0.0 同一工作流完成出题及五模型排序。旧三模型handoff和delivery是历史检查点，保留原文；不需要交给另一个质检workflow。

workspace-update更新既有工作区侧栏说明和工具路径，自动查找当前冻结版本通过门槛的三模型评估并创建Arena填写文件。题面、考点、原文、判断、自查、私有配置和旧交付不改写。

Arena输入为arena-input/rNNNN/model-4.md与model-5.md。model_name记录真实完整型号，分隔线下是原Markdown。request.json由工具绑定冻结题目。导入同时检查两份输入，保留不可变原件及哈希；不要求截图。截图由用户单独提交甲方，页面模式/随机性不是工具已核验的事实。

完整导出handoff.json的kind为llm_complete_submission，schema_version=1，记录版本、题目哈希、seed/gpt/claude/arena_1/arena_2顺序、出题门槛和排序，next_workflow为platform_submission。fields.json包含题目、题型、Insight、两类考点、五个模型完整Markdown/达成性/理由、排序与排序理由。

固定显示顺序为模型1 Seed、模型2 GPT、模型3 Claude、模型4/5 Arena。evaluation.json评估全部核心考点；authoring-evaluation.json为前三个模型决定性点的兼容检查视图。ranking.json绑定完整evaluation哈希；全部决定性达成梯队优先，同梯队按全部满足数排序，相同并列。备注至少500字，结构为总结＋模型1至模型5具体考点情况。

旧delivery/v001保留，完整结果用v002等新目录。manifest.json覆盖五原文、判断、排序、三API截图及来源证据的文件哈希。软件导出完成不等于甲方平台验收完成。
