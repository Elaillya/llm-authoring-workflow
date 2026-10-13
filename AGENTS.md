# 完整出题与五模型排序

先读 README.md 与 skills/llm-authoring-workflow/SKILL.md。新用户准备依赖并用 scripts/lab.py workspace-create 创建工作区，不提示 API 配置。每道新题先询问领域再询问题型。已有题目运行 status，复用已冻结内容和原件。

题目、Insight、决定性与可选非决定性考点由助手设计并核实来源。全部回复由用户填入预先创建的 Markdown。先收 Seed 并判定；未达成全部决定性点才收 GPT/Claude。三模型门槛通过后继续 Arena、五模型评估和排序，不设置独立质检阶段。所有网页截图由用户单独提交甲方。

具体专业规则以 rules/authoring.md 为准。维护代码按 docs/SPEC.md，运行 python -m unittest discover -s tests；使用合成材料验证，不调用付费模型。发布 Git 仅包含通用源码，禁止个人题目、原回复、密钥和运行环境进入公开仓库。
