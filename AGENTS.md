# 完整出题与五模型排序

先读 README.md 与 skills/llm-authoring-workflow/SKILL.md。新用户准备依赖并创建工作区，不提示模型API配置；共用质检配置已随仓库提供，缺失时自动初始化，不再要求同项目用户提供HAR或service.json，只按需填写自己的Cookie。新题先问领域、子方向和题型。已有题目运行status，复用原件和有效结果。

设计、判断和交付时读Skill的references/writing.md：发送文字与prompt完全一致；Insight用灵活的纯文本突出真正的决定性因素，考点减少背景且每条只判断一件事；提交说明用纯文本，排序备注简洁解释考点差异，不设字数下限。模型原Markdown保持。

题目、Insight及考点由助手设计并核实来源。先读本地题库和专业资料，写自然prompt与Insight后，按Skill的references/platform-checks.md执行难度标签检查，合理问题自主修订复检，再完成考点、多样性复核与冻结。模型回复由用户填Markdown，先Seed，未全部达成再GPT/Claude。三模型原文、判断和备注齐备后先lab check并确认three_model_gate=true；只有Seed未全部决定性达成、且GPT或Claude至少一个全部达成，才用qa-run models并行质检考点和达成性。GPT/Claude都未达成则保留失败候选与原件，按本地题库记rejected、重新生成新prompt，后两项质检不调用。正常请求等待至完成，不设客户端时间上限；按Skill持续报告和等待原进程。错误意见有证据登记异议，明确告知不认同并提供可复制备注。门禁满足后先发Arena填写链接；三项实际通过的优化建议此后离线处理，保持题面、含义及判定，优化后不再质检。缺失/过期Cookie给已有私有文件；模型生成API仍禁用。截图用户单独提交，检查在主流程内完成。

具体专业规则以 rules/authoring.md 为准。维护代码按 docs/SPEC.md，运行 python -m unittest discover -s tests；使用合成材料验证，不调用付费模型。发布 Git 仅包含通用源码，禁止个人题目、原回复、密钥和运行环境进入公开仓库。
