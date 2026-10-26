# 完整出题与五模型排序

跨父目录共享题库为显式本地配置，按docs/LOCAL_MEMORY.md及docs/SHARED_MEMORY_SPEC.md处理；未配置时仍独立。使用memory-context返回的实际范围，不复制私人数据库到源码仓；共享迁移不改题目原件。

先读 README.md 与 skills/llm-authoring-workflow/SKILL.md。新用户准备依赖并创建工作区，不提示模型API配置；共用质检配置已随仓库提供，缺失时自动初始化，不再要求同项目用户提供HAR或service.json，只按需填写自己的Cookie。新题先问计算机科学、商科或生活娱乐，再问子方向和题型；生活类按Skill的references/lifestyle.md逐层选范围，也可明确停在当前层由助手细分。已有题目运行status，复用原件和有效结果。

设计、判断和交付时读Skill的references/writing.md：发送文字与prompt完全一致；Insight用灵活的纯文本突出真正的决定性因素，考点减少背景且每条只判断一件事；提交说明用纯文本，排序备注简洁解释考点差异，不设字数下限。模型原Markdown保持。

新prompt设计和题目检查发送前，按writing.md把唯一核心任务收束为一个完整问句，原因/依据融入其中，不在句尾另问“为什么”。single_core_question必须说明语义确为单一任务，不能只数问号或换标点。已有冻结题面和原回复保持，以后改prompt另建版本并从Seed采集。

题目、Insight及考点由助手设计并核实来源。先读本地题库和专业资料，写自然prompt与Insight后，按Skill的references/platform-checks.md执行难度标签检查，合理问题自主修订复检，再完成考点、多样性复核与冻结。模型回复由用户填Markdown，先Seed，未全部达成后按Skill的references/optional-model-checks.md询问并记录后两项质检策略，再收GPT/Claude。三模型原文、判断和备注齐备后先lab check并确认three_model_gate=true；只有Seed未全部决定性达成、且GPT或Claude至少一个全部达成，且用户选择需要后两项检查，才用qa-run models并行质检考点和达成性。初次GPT/Claude都未达成则保留失败候选与原件，按本地题库记rejected、重新生成新prompt，后两项质检不调用。正常请求等待至完成，不设客户端时间上限；按Skill持续报告和等待原进程。错误意见有证据登记异议，明确告知不认同并提供可复制备注。门禁满足后先发Arena填写链接；三项实际通过的优化建议此后离线处理，保持题面、含义及判定，优化后不再质检。缺失/过期Cookie给已有私有文件；模型生成API仍禁用。截图用户单独提交，检查在主流程内完成。

具体专业规则以 rules/authoring.md 为准。维护代码按 docs/SPEC.md，运行 python -m unittest discover -s tests；使用合成材料验证，不调用付费模型。发布 Git 仅包含通用源码，禁止个人题目、原回复、密钥和运行环境进入公开仓库。

认可考点质检不通过时按Skill的references/repair.md修复：优先保持prompt修Insight/考点、统一重评；仍不能满足门槛先询问用户是否重新提供GPT/Claude原文，替换不可行才改prompt。设计前读failure-context；模型门槛失败及平台实际不通过自动记观察，由助手复核原因、改进和范围后在当前题库范围内共享（默认同父目录，显式共享组为其全部成员），错误/未确认意见与服务故障不作为可靠经验。原回复替换须本次明确同意并归档，不自动反复抽取。

后两项质检策略以Skill的references/optional-model-checks.md为准：题目难度与标签检查固定；Seed未全部达成后、准备GPT/Claude填写文件前询问本题是否做考点/达成性质检，等待明确答复并用choose-model-checks记录。选择需要才并行两项；选择不需要则主流程去掉两项调用，仍需有效题目检查和three_model_gate才进入Arena与五模型排序。跳过标注未执行，不能声称通过；历史记录保持。

## Insight与考点研究必读（3.6.2）

开始/恢复、构造题面、确定或修改Insight与核心考点、判断模型、返修及排序交付时，必须按Skill的references/insight-rubric-checklist.md对应阶段，阅读并应用references/insight-rubric-study.md完整研究报告和检查单。尤其Insight先解释决定因素怎样改变本题决策；核心考点核对目标覆盖、单一可判关系、最低证据、等价路径与必需/可选边界。新候选设计复核的insight_rubric_alignment须给出本题具体依据；旧冻结不追溯失效。报告未验证出高概率通过API的模板，不能机械照抄、为Seed失分加条件、把无法质检当通过或反复刷检查。
