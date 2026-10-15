# 完整出题工具接口规范

- 新题先选择计算机科学、商科或生活爱好类，再选择config/domains.json的子方向及三种题型之一；助手负责场景、事实、限制和专业资料核实。没有用户材料不阻塞。领域不得从 cs_ 等 ID 或相邻题目推断。
- 候选题面≤100字符；Insight用非空纯文本突出决定性因素及其作用，组织形式灵活，兼容旧三字段对象；考点减少背景且每条独立可判定；至少一个决定性考点，非决定性考点可选，没有时交付“无”。先冻结再获取回答，禁止倒推标准。
- 3.0.0 所有模型回复手动填入工具预先创建的 Markdown。新用户不需要 API 配置，不自动调用 Seed/GPT/Claude，collect/recover/render 命令拒绝执行。所有官方网页截图由用户另行提交；不渲染模拟网页，不要求在工作区上传截图。
- 新 TASK.response_mode=official_manual。model-prepare seed 创建 model-input/rNNNN/prompt.md 与 Seed 2.1 Turbo.md。用户只替换占位内容，不填模型元数据；名称由角色固定。model-import 保存完整原始字节、来源为用户提供、版本绑定和哈希，格式损坏、占位或空文不可导入。
- 先导入 Seed，按全部决定性点判断。model-prepare 和 model-import gpt/claude 必须各自验证当前冻结版本的 Seed 判断；未判定、过期、Seed全部达成都阻断。未全部达成后才创建 GPT-5.6 sol.md 与 Claude Opus 4.6.md。五份发送文字逐字节等于冻结prompt，不追加格式指令或换行，不发送 Insight/考点。GPT/Claude 要求中高推理，官方页面不能确认规定型号时缺材料，不替代型号。
- 准备重复执行不覆盖已填写内容；导入同一原件幂等，已有不同回复不可覆盖。原始输入缺失或被修改、哈希不符、版本错配时不能进入评估。题面不变而考点或Insight修订时复用回复、统一重评，题面改变重新获取。
- 三模型门槛为 Seed 未全部达成且 GPT 或 Claude 至少一个全部达成，三份完整原文均须保存。逐点 met 为布尔值、reason 具体，满足必须有准确原文 quotes；缺证据不是 false。作者自查保留，不插入独立质检阶段。
- 后两项质检发送前必须在本地通过同版三模型门槛：Seed未全部决定性达成且GPT或Claude至少一个全部达成。完整但不合格的判断直接转candidate_rejected，保留负结果并重新选题，不读Cookie、不发请求、不新增尝试；models、单项及--refresh共用拦截，缓存不能绕过。详见THREE_MODEL_QA_GATE_SPEC.md。
- 新任务默认platform_checks_required：prompt/Insight先难度标签检查，三模型原文、判断及备注齐备后并行检查考点与达成性，正常请求等待到完成、没有客户端上限；合理不通过返修。三项实际通过后先发Arena链接，再记录不改变含义及判定的表达优化，最终交付使用优化文字并说明未复检。错误内容意见给证据异议和可复制备注，保留原结论。Cookie私有。协议见PLATFORM_SPEC.md；本轮变更以QA_REFINEMENTS_SPEC.md为准，执行分支见Skill的references/platform-checks.md。
- 平台门禁及三模型门槛通过后创建Arena填写文件；准备、导入和导出均重新校验，导入需当前evaluation。Arena仍只收用户原Markdown及实际型号，截图另交。旧任务续作不强迫补检查；workspace-update不自动修改旧TASK合同。
- 五模型统一判断全部决定性与非决定性点。排序先按全部决定性达成性分梯队，同梯队按全部考点满足数降序，相同并列；没有品牌、文风或长度权重。排序和备注使用真实型号；简洁说明五模型具体考点差异及原因，不设字数下限，并绑定评估哈希。
- 完整交付保留六个文件：提交信息.md用普通标签与纯文本段落呈现题目、题型、Insight、两类考点、达成性/备注及排序/理由；五份回复在models/按真实型号命名，原始字节一致，主文件给出回复路径。没有截图、ZIP、合并回复文件或附加用户清单。JSON、evidence及manifest保留作内部记录。
- 旧API回复/截图及JSON/SSE仅兼容校验读取和导出，不能用于新官方截图要求，不再从入口采集。升级保留题目、原件、负结果、判断和旧交付。已有父目录配置和运行环境保留；重置需明确用户授权、完整归档与校验，只处理指定任务。
- 公共Git仅包含通用源码、Skill、规则、模板和合成测试，不含个人题目/回复/密钥/运行环境；正常推送Elaillya/llm-authoring-workflow并核实账号与远端提交。测试应覆盖手动全流程、Seed门槛绕过、数据完整性/幂等、跨版本重评、旧题读取、无配置首用及无截图六MD交付，禁止付费调用。
- 3.1.1经用户明确确认并授权公开共同任务与检查模板元配置，config/aidp-service.json不含登录或会话信息；缺少本地配置时自动初始化，已有配置/Cookie原件保留，支持qa-setup --default。无需同项目用户导出HAR；仅填写自己的Cookie。净化Referer线上验证边界见SHARED_PLATFORM_CONFIG.md。

本轮表达规则与兼容边界见PLAIN_TEXT_SPEC.md及Skill的references/writing.md；覆盖此前固定三段、统一格式指令和500字下限。

## 3.1.0-dev 设计前置检查

新策略selection_schema=2；画像与子方向随冻结保存，本地题库SQLite位于父目录local，跨窗口事务预留、快照绑定、词法召回加全库语义筛查；自然表达按受众核实，不机械禁用专业词。商科20来源/18机制卡是参考索引，非已验收题目或专家判断替代品。具体实施范围与未部署约束见NEXT_SPEC.md，操作接口见LOCAL_MEMORY.md。旧冻结记录与3.0请求读取兼容。
