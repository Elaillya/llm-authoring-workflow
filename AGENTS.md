# 完整出题与五模型排序

开始或接续出题时，先读 README.md 与 skills/llm-authoring-workflow/SKILL.md。新用户用 scripts/lab.py workspace-create 建工作区并准备依赖，首次提示三个模型配置，每道新题先询问专业领域再询问题型。已有题目运行 status，复用原领域、冻结版本和原件，接续缺失步骤。

范围为题目、Insight、决定性与可选非决定性考点、三模型验证、Arena两份Markdown、五模型考点评估和排序、完整交付。Arena填写文件由工具创建，用户只填型号和原文，截图由用户自行提交甲方。具体专业规则以 rules/authoring.md 为准。

升级已有工作区用 workspace-update，保留题目和私有配置。维护代码按 docs/SPEC.md，运行 python -m unittest discover -s tests；软件验证使用合成材料，真实模型调用留给出题任务。发布源码仅包含通用工具文件。
