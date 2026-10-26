# Windows 本地自动化接续入口

开始开发、迁移环境、恢复浏览器联调或解释本分支能力时，先读 docs/LOCAL_DEVELOPMENT_HANDOFF.md 和 docs/AUTOMATION_VALIDATION.md。本分支是服务器浏览器原型的保存与移植起点，Windows 本地独立运行尚待实现；先检查硬编码路径和远程连接，不直接启动旧SSH采集脚本。

接续1262或使用历史题库前读 docs/PRIVATE_STATE_TRANSFER.md，取得并验证私有原件；源码clone没有这些资料，配置/权限错误不能当空库。1262已暂停，不自动恢复模型或质检。本次发布授权仅用于独立开发分支，不修改main或服务器旧题；题目提交须另有当前授权。

# 浏览器出题闭环开发

修改代码先读 docs/BROWSER_PILOT.md、相关测试及该题 TASK.json。现有手动模式按 docs/LEGACY_AGENT_RULES.md；platform_check_mode=browser 的独立试验题使用网页质检入口，禁止退回直接调用质检API。

出题阶段先读 skills/llm-authoring-workflow/SKILL.md，完整阅读其 Insight 研究报告和写作检查单。保留自然单一提问、真正决定因素、原子考点、Seed先行及三模型门槛；记录用户实际菜单路径。题库按 memory-context/failure-context 返回的共享范围使用，不建替代空库。

浏览器分支使用官方真实客户端产生原回复及截图，发送内容严格等于冻结prompt；原文、实际型号和推理强度均有证据才评分。未接入的客户端步骤先实现并验证适配器，不能改成API渲染截图或把自动采集冒充用户提供。

正常网页质检等待真实请求完成，考点与达成性并行且按requestID分别记录。断线/暂无/服务错误与专业不通过分开；结果未知先核对原页面，不重复发送。输入变化使旧结果失效。异议保留服务器结论与具体证据。

只在此开发副本及明确指定的试验工作区实施；正式旧题、旧源码和交付保持。按docs/BROWSER_PILOT.md区分合成测试、真实短题联调与完整流程验收，未验证不写通过。Arena当前人工交互接续。发布GitHub须遵从用户后续指令，源码不含题目、原回复、截图、登录态或私有配置。

验证使用 Python unittest 和 browser_automation 下的合成 Node 测试；测试不调用付费模型。实际联调限于用户指定题目和已授权客户端，持续记录原文、失败与请求回执。

未来新题只从menu/domain-tree当前启用主题中选择；new_questions_enabled=false的子方向及后代停止新出题，不通过父级或自由命名绕过。完整topic_index保留历史ID，既有同prompt题目仍可读取、重评和返修；更换prompt不再属于历史兼容范围。
