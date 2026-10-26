# 本地移植前的浏览器原型记录

最新接续以 [本地开发交接](LOCAL_DEVELOPMENT_HANDOFF.md) 和 [实际验证](AUTOMATION_VALIDATION.md) 为准。以下保留服务器原型步骤及按时间追加的历史记录；其中绝对路径/SSH入口不是Windows本地启动方法，过去“尚未验证/等待”的现场描述按时间阅读。

截至2026-10-26：1262当前为1262-plants/r0002，网页题目检查通过、Seed决定性1/2；Seed文字字段已实测填写，6张原图已实测上传。模型字段模块已有真实Seed验证，通用上传尚未实现；GPT/Claude、后两项和完整闭环仍待联调。当前无在途请求，用户暂停换电脑，后两项策略尚未选择。不重新发送Seed。

# 浏览器闭环开发分支

状态：正在实现；本次快照发布到独立开发分支，不部署到正式旧工作区。保留原有手动模式；只有 TASK.json 中 platform_check_mode=browser 的试验题启用下列入口。试验题 Seed 名称为 Seed 2.1 Pro，其余任务保持原合同。

已实现：采集端重连检查、精确平台 itemID 绑定、真实页面填写与回读、网页按钮质检的网络事件记录、并行结果分离、原请求输入校验，以及将结果导入原有冻结/门禁/异议机制。无需手工提供 Cookie，登录在本机专用 Chrome 中完成。这里的本地合成测试不代表真实页面全流程验收。

继续开发时先阅读 `browser_automation/`、`llm_authoring/browser_checks.py` 和该题 `browser/binding.json`；保留 task/revisions/responses/evaluations/delivery 原件。题目设计与判断仍遵循原 Skill 的研究报告、检查单、自然单一提问、原子考点及 Seed 先行规则。

题目检查步骤：

1. 用 `lab browser-prepare question --question drafts/question.json` 校验当前选择与输入，取得 spec 路径。缓存的有效结果直接沿用。
2. `node <工具目录>/browser_automation/run-browser-checks.mjs inspect <spec>` 核对绑定页面；`fill <spec>` 在页面填写并回读。只有空字段、相同文本或本题已归档的旧输入才允许填写。
3. `run <spec>` 点击真实网页按钮。先保存意图再点击，正常请求一直等到网络完成，没有总等待时限；每20秒输出进度。“暂无”不会触发重试。
4. `lab browser-import <spec所在目录> --question drafts/question.json` 验证事件哈希链、原实际输入、平台绑定与当前内容后导入。通过才能冻结；不通过保留真实反馈，按研究依据返修。输入改变后重新 prepare，旧结果不会放行。

冻结考点后，`node browser_automation/fill-frozen-points.mjs <本题目录>` 可把当前冻结的决定性及非决定性考点填入同一绑定网页，并回读留存收据。只改这两个文本字段：题面和Insight须与当前冻结一致，只允许空白、相同值或本题已归档的旧考点；未知的网页文字先保留。无非决定性点填“无”。此入口不发送模型、不点质检、不上传、不暂存或提交。2026-10-25已在1262 r0004实际填写验证，不代表模型字段与后续全流程已验收。

考点/达成性质检使用 `browser-prepare models --evaluation <evaluation>`。它在准备阶段校验三模型门槛及本题检查策略，通过后才准备两个计划；run 依次点击两个按钮使真实请求并行，按各自 requestID 保存。参数与原文变化会使旧结果失效。

已确认原请求完整结束但HTTP503/504等服务错误，或严格确认返回为空时，先用browser-import保留原异常回执，再用browser-prepare添加--retry-reason说明执行错误。工具为同一输入保存递增编号的每次回执，并引用上次原件；不会覆盖旧错误，也不会因换重试理由另发第二个未解决请求。身份失效先让用户恢复登录；内容不通过或尚未解释的非空反馈先修题或核对，不能靠重试刷通过。单次正常检查仍无总等待上限。

若当前网页已有题目检查结果，但该次网络请求不是本观察器发出或无法回取，不再重复点击。capture-current-check.mjs <spec>只读采集两次稳定输入、平台当前有效结果和两张真图；逐图核对后填dom-result/verification.json，再browser-import-page <spec目录> --question <候选JSON>。该入口暂仅支持题目检查，要求无过期提示、无运行状态、输入和调用次数在采集前后相同。原HTTP错误保持，页面证据另存并明确source=browser_dom_current_result，不填造HTTP状态、请求ID或原网络响应。页面恢复不替代三模型门槛或后两项检查。

断线时：先运行 `node <工具目录>/browser_automation/doctor.mjs`。结果未知的请求不能自动重发；保留 journal，检查原页面/请求结果后再决定恢复。进程异常退出留下的锁不自动删除，需核实原观察器已结束。单次 CDP 命令30秒传输超时不等于质检总时限。

三模型开发入口（已写代码及合成验证，真实整流程仍待联调）：

1. 先核验 `model-worker.mjs capabilities` 为 worker_protocol=2；本机更新启动时运行17项自检。旧短题采集端协议1不能替代通用端，启动脚本本身不发送问题。
2. 冻结后 `lab client-prepare seed` 创建只含冻结prompt的请求，`node browser_automation/doubao-client.mjs collect <request.json>` 通过豆包正常新任务发送，完成后使用官方复制按钮导出原Markdown；`capture <request.json>` 连续滚动真实页面保存截图，并为横向溢出的表格追加向右滚动的原图。仅发一次，未知结果不重新发送。
3. `lab client-review-template seed` 列出全部截图；助手逐张查看并对照原文末尾、型号与High，核对纵向和横向覆盖后填写verification.json，再 `client-import seed`。滚动记录或截图数量本身不证明完整，特别长的表格仍须逐行核查。它是证据核验记录，不要求用户填写；未看图不能置true。先做seed-check并保存当前seed-rNNNN.json。Seed全部达成则保留失败候选，重新设计题面。
4. Seed未全达成并记录本题后两项检查策略后，`client-prepare gpt/claude`。GPT由工作区运行环境中的Python执行 `browser_automation/gpt-client.py --task <本题>`，使用独立CODEX_HOME、空目录、官方独立运行选项及指定型号/High，保存原事件与实际上下文。Claude通过 `model-worker.mjs claude-start <request.json>` 启动本机Safe mode新会话，`claude-status <request.json>` 读取同一原结果。首次信任新隔离目录时由用户在正常客户端确认。
5. GPT原生成完成后 `gpt-register <request.json>` 登记原会话；两个客户端用 `display <request.json>` 在CMD黑底恢复，`capture <request.json>` 保存真实窗口。长回复使用 `navigate <request.json> open_transcript|page_up|page_down`，仅作用于本采集端登记的窗口。恢复和翻页不发送新问题。逐张看图再 `client-review-template` 和 `client-import`。

每次新增模型调用都复核当前冻结输入与Seed门槛，原始输入、原回复、实际配置、截图与原先Seed判断分别绑定。Insight/考点修订可对同prompt的原回复统一重评，不能反过来改写原件。截图、日志与MD复制后逐文件核哈希，作为官方客户端证据保存，来源不写为用户手工提供或API渲染。正文允许链接、JSON代码框及文字框架，富媒体/HTML/附件原样保留并标需处理，不删掉后假装完整纯文本。

现场进度（2026-10-25）：协议2及17项Windows启动自检通过。1262厨房尝试完成8次网页题目检查、7份不同冻结prompt的唯一Seed官网原生成、49张逐张查看的原图；七版全达成而淘汰，本轮强化三版难度8、8、7，均4/4。按用户要求将life_cooking_workflow从未来新题菜单、树及校验移除，保留完整历史ID和同prompt返修。用户改选摄影，独立新尝试目录1262-photo，沿用平台绑定但不复用旧回复或检查结果。305项Python与27项Node回归通过。豆包新建任务会回中，采集端新增仅在精确未发草稿内选High并回读，型号不自动替换；现场菜单收起错误发生在发送前，已改用允许的鼠标操作并成功唯一发出r0007。

还未在1262验证：GPT/Claude新题采集及长控制台回复覆盖、三模型门槛后的并行网页检查、通用上传/排序/正式提交、完整Arena接续。旧短题记录不代替这些验收。实际观察到豆包工作入口自动联网调研。用户最新明确：Seed只使用www.doubao.com官方网页，允许联网，选择2.1 Pro，保留既定High；GPT/Claude保持现有原生无工具适配器。不得改用火山方舟或把普通“专家”别名冒充已核验的2.1 Pro High，也不得把工作任务称为已关闭联网的纯模型回复。TASK.json和browser/model-tool-policy.json记录当前实际口径及其变更，不追加上下文到冻结prompt。

第一题闭环确认后再实现和启用领题循环。Arena当前仍使用用户正常交互与复制导出，不执行自动查询或验证码绕过。旧截图完整性复核若发现遗漏，追加同会话原图并保留更正记录；不要覆盖原图或改写历史核验。

本地门槛和实际网页门槛分别回读；本地跳过、异议或服务异常不等于网页检查通过或Arena字段已经启用。按照实际页面处理备注、正常/异常及确认框，保留原服务器结论。输入变化按网页真实失效规则处理，不能把旧豁免当作新输入通过。

验证：Python完整回归及新增浏览器收据测试；Node合成测试覆盖大请求正文回取、长期暂无、并行完成倒序、身份/服务错误、输入变化、断线与原件改写。真实联调用指定题目逐步核验，不复用旧题提交授权或 screenshot fileID。


## 摄影联调接续（2026-10-26）

厨房停用入口与历史兼容保持。摄影r0001作者灰卡条件歧义已排除资格判断，原文4图保留；补明r0002网页第13次原生结果通过、难度7，以独立browser_dom_current_result保存，不编造HTTP，原504网络错误保留。官网Seed Pro High r0002四点4/4、5图核验，淘汰。

摄影r0003改为LED排练动态摄影。真实网页难度8、题型与基础项通过，领域不通过；作者对应用领域与知识基础的混同登记输入绑定异议，明确disputed不是passed。三条标准已在模型调用前冻结，官网唯一Pro High原会话38449271436943874生成中，尚未判断、无GPT/Claude调用。

browser-model-prepare ROLE --evaluation FILE为验证完整原件与当前判据后的填表计划；fill-model-fields.mjs SPEC只填写原Markdown、具名逐点备注与达成选择，先核对题面、Insight、两类考点、领域与题型。不同的已有回复/备注/选择保留不覆盖；文件、截图、原回复、当前冻结或判断变化会阻止旧计划。当前仅合成验证，尚无真实模型字段填写/上传验证，不自动点检查、确认或提交。

本次完整回归325项Python、37项Node通过。新模块仅部署隔离开发工具，不更新旧v3或公共仓库。
