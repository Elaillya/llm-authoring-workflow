# 完整出题与五模型排序

先读 README.md 与 skills/llm-authoring-workflow/SKILL.md。新用户准备依赖并创建工作区，不提示模型API配置。新题先问领域、子方向和题型。平台质检按需使用私有Cookie，已有题目运行status，复用原件和有效结果。

题目、Insight及考点由助手设计并核实来源。先读本地题库和专业资料，写自然prompt与Insight后，必须按Skill的references/platform-checks.md执行难度标签检查，合理问题自主修订复检，通过后完成考点、多样性复核与冻结。模型回复仍由用户填Markdown，先Seed，未全部达成再GPT/Claude。三模型原文与判断齐备后依次做考点和达成性质检；错误意见有证据登记异议、明确告知用户不认同并给出填表备注。平台门禁与三模型门槛通过后才进入Arena。缺失或过期Cookie给已创建的私有文件填写；模型生成API仍禁用。所有截图由用户单独提交。该检查在主流程内完成，不另设专家质检工作流。

具体专业规则以 rules/authoring.md 为准。维护代码按 docs/SPEC.md，运行 python -m unittest discover -s tests；使用合成材料验证，不调用付费模型。发布 Git 仅包含通用源码，禁止个人题目、原回复、密钥和运行环境进入公开仓库。
