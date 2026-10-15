# 完整提交与旧题接续

3.0.0 默认使用用户提供的官方网页 Markdown。新题先询问领域和题型，不需要 API 配置。冻结候选后 model-prepare seed 创建题面与 Seed 填写文件；model-import seed 保存原文。当前版本 Seed 判断未达成全部决定性点后，才允许 model-prepare/model-import gpt、claude。文件在 model-input/rNNNN/，按模型名字命名，仅粘贴回复正文，不要求用户创建文件或额外清单。

request 绑定题目 ID、版本、完整题目/题面/考点哈希；GPT/Claude 还绑定先行 Seed 判断和原文。原始输入及 metadata 不覆盖。评估绑定当前冻结版本及回复哈希，题面改变重新获取回答，题面不变而 Insight/考点改变统一重评已存原文。

三模型门槛通过后，arena-prepare 创建 arena-input/rNNNN/model-4.md、model-5.md、arena-prompt.md。两份文件头部填写实际 model_name，后面填原 Markdown；工具检查完整性与型号限制。所有网页截图由用户直接提交甲方，工具不渲染图片，不独立声称网页型号/模式/随机性核验。

五模型排序全部决定性达成梯队优先，同梯队按全部核心考点满足数比较，相同并列。决定性和非决定性点均判断；没有非决定性点填“无”。排序与备注使用实际名称，理由简洁写明考点达成差异及原因，不设字数下限；旧编号形式可兼容读取并转换展示。

完整交付为提交信息.md及models/下五份按模型名命名的原回复，主文件不内嵌回答。JSON、evidence 和 manifest 作为辅助记录；不生成 ZIP。handoff.kind=llm_complete_submission，next_workflow=platform_submission；软件导出不代表甲方验收。

workspace-update 仅更新侧栏说明和工具入口，保留已有题目、评估、回复、自查、交付、Git历史、私有配置与运行环境。旧 API 原件可继续校验与导出，历史 API 渲染图不能作为官方网页截图，collect/recover/render 入口已停用。TASK.response_mode=official_manual 的新题只接受手动原件。

新任务 REQUEST.domain/domain_confirmed/question_type 为空或未确认，必须由用户选择；旧冻结题目沿用冻结领域。rename 只改显示名和目录，冻结 ID 与旧入口保留。重置现有任务需用户明确指定；先将整个目录（含未提交和忽略文件、Git历史）归档并校验，再建立空白同名任务；其他任务保持原件。

## 3.1.0 工作流入口

新建任务默认platform_checks_required：prompt/Insight先难度标签检查，三模型原文、判断及备注齐备后并行考点/达成性质检，正常请求等待至完成；合理不通过返修、错误意见证据异议并给备注。门禁满足后先发Arena链接，三项实际通过的表达建议此后离线优化免复检。导入须--evaluation当前判断；Cookie填已有私有文件，模型生成API禁用。分支见Skill的references/platform-checks.md，2026-10-15变更见QA_REFINEMENTS_SPEC.md。更新先备份侧栏说明，保留已有任务合同及题目证据。

3.1.0的新题二选一计算机科学/商科，再选子方向和题型。冻结前读取工作区私有题库、完成自然与差异复核；新用户不需要配置API。接口与迁移边界见LOCAL_MEMORY.md；业务资料见BUSINESS_REFERENCES.md及rules/business-reference.json。现有已冻题的原件不要求补画像或重取回复。
