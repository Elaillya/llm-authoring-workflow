本版题目难度/标签固定检查；准备GPT/Claude填写文件前按optional-model-checks.md询问并记录后两项策略。本文的考点/达成性调用、返修和三项通过优化仅在用户选择required时执行。选择skipped时不发这两项，保留题目检查与三模型门槛，直接准备Arena；跳过不等于通过。

# 平台检查、返修与通过后优化

三个检查在主流程内完成，模型回复仍由用户提供Markdown。助手可以调用AIDP质检服务，模型生成API保持禁用。

## 私有配置与等待

本项目共用元配置已随工具仓config/aidp-service.json提供。父工作区local/aidp/保存本地service.json和cookie.txt，同父目录题目共享本地登录态。文件与目录采用系统默认权限并继承父目录访问规则，不强制600/700或为读取配置收紧权限。缺少本地service.json时，首次读取配置会自动导入共用值并创建Cookie文件；也可先`qa-setup --default`显式准备。**同项目首次使用不再索取service.json或HAR路径**；只在需要检查时让用户填写自己的Cookie。已有私有配置和Cookie保留。其他任务可用`--config <文件>`或`--har <脱敏HAR>`高级导入，不能用默认值覆盖已有不同配置。

task_id是项目任务上下文，plan_id选择检查，网页itemID不是当前请求的独立字段。共用配置Referer为站点根地址，不带原题itemID或会话参数；它的字段和初始化经过离线验证，净化Referer尚未实测线上调用，不能引用旧配置的成功记录声称已验证这一点。细节见工具仓docs/SHARED_PLATFORM_CONFIG.md。

需要检查时才请用户填写已创建的cookie.txt并给可点击链接；会话已有配置/登录态直接复用。401/403时给同一文件更新，保留失败记录；登录失效不代表题目不合格。

**正常请求一直等待至返回，没有客户端总时长或读取超时上限。**旧配置中的数字timeout_seconds兼容读入并规范化为null。使用后台命令保留session_id，每次工具等待不超过60秒并继续轮询同一进程，期间向用户简要报告。单次工具让出控制权不等于质检超时。不要因为“已等很久”终止进程、重复请求或把题目判失败。连接断开、身份认证、HTTP/业务错误等真实错误保留并按实际原因处理；结果未知不自动重发。

## prompt与Insight之后

1. 选择领域、子方向、题型，结合资料和题库写自然prompt与Insight。此时不强求已有考点。
2. `qa-run question --question drafts/question.json`，等待原进程完成，核对HTTP、业务状态及内层结论；HTTP200本身不代表通过。
3. 通过：接续考点设计、多样性复核和冻结，反馈中的可选表达建议先保留。不通过：核实问题，自主修订题面/Insight再检查；可核对的错误结论走异议分支。
4. 同一输入已有有效结果时复用；仅有实际修订或明确复核理由才发送。`--refresh`仅用于明确复核，不用于给措辞建议刷结果。

题目检查比较题面、领域、题型、Insight；补考点不使它失效。标签映射在私有service.json，不能为迎合标签擅改用户选择。

## 三个模型原文、判断和备注齐备之后

1. 保留Seed优先。导入三份完整原文，在同版考点下完成逐点met、reason、准确quotes及达成性备注，先运行`lab check <当前三模型评估>`并读取JSON中的`three_model_gate`，不能仅看退出码。只有Seed未全部决定性达成、且GPT或Claude至少一个全部达成才进入下一步。初次GPT和Claude都未达成，或Seed已全部达成时，当前候选不合格：保留题面/Insight/考点、原回复、判断及已发生检查，按本地题库记rejected并按repair.md复核失败经验，转向实质不同的新prompt，重新题目检查和Seed优先采集；不调用考点或达成性质检，不为命中而改判或放宽考点。已认可后期考点失败的同题面修复重评若门槛失效，先按repair.md询问回复替换，替换不可行再改prompt；后两项质检仍不得调用。
2. **仅上一步门槛通过且用户选择required时**，`qa-run models --evaluation evaluations/three-rNNNN.json`：**一次发起并行考点质检、达成性质检**，不要依次执行两个单项命令。两项取同一输入快照，分别落盘；一项返回不通过不阻止另一项返回。单项qa-run仅用于门槛仍通过时的实际缺失项或有明确依据的复核。统一入口在读取配置/Cookie、缓存或发送之前拦截不合格判断；models、criteria、attainment和--refresh均不能绕过。
3. 等两项结果齐备后统一看反馈，按repair.md先复核并记失败原因。认可考点问题时优先保持prompt修正Insight/考点并统一重评；合理修复仍不能满足门槛，先询问是否重新提供GPT或Claude完整回复，替换不可行再改prompt。按输入依赖重检：Insight变化先题目检查，新冻结版本统一重评；备注单独变化重检达成性，保留另一项有效结果及失败版本。禁止按模型答案倒推有利标准。
4. 若部分登录/服务错误，保留成功结果；排除实际错误后仅补缺失项。批次共用题目锁，防止重复发送；两项均完成或有证据异议且三模型门槛满足后，才准备Arena。

同输入intent已落盘但result缺失时，视为尚在运行或中断后结果未知。继续等待原进程；若进程已结束，先核对原尝试、已保存返回与平台状态。即使--refresh也不会自动重发，不能仅删除锁就假定服务未执行。`qa-status --evaluation <当前评估>`用于核对已保存结果，进度等待仍针对原执行会话。

## 不认同质检时立即给备注

三项内容检查的实际“不通过”均可登记有证据异议；登录、服务错误、未知结果和旧版本不能豁免。先分清合理意见、信息不足、自己解释不清与可定位的质检错误。实际不通过自动进入本地失败观察；仅认可的原因成为共享经验，详见工具仓docs/FAILURE_LEARNING.md。

1. 生成模板：三模型阶段用`qa-disagreement-template criteria|attainment <新异议JSON> --evaluation <当前评估>`；题目检查用`qa-disagreement-template question <新异议JSON> --question <当前候选JSON>`。
2. 助手填写reviewer、reason、evidence、form_notes。至少一条feedback引用和一条input引用须逐字来自本次反馈与输入；模型引文的input.field使用实际请求字段。写清专业依据及分歧，引用片段本身不代表已证明质检错。
3. `qa-disagree <异议JSON> --evaluation <当前评估>`；题目检查改用`--question <当前候选JSON>`。保留服务“不通过”，本地记disputed，不冒充通过，不新增用户审批。
4. **立即**告知：“不认同该不通过结论”，附具体原因、准确依据、可直接复制的form_notes，以及生成的表单备注.md链接。给出复制文字本身，不能仅给内部JSON或一句“忽略即可”。优先建议填平台质检异议/返修说明栏；若页面没有该栏，先核实可用位置。修改了实际质检输入就按依赖更新，不能冒用旧结果。

例：仅当本次提交已把Claude判为全部达成，反馈也逐点判达成且没有定位其他实际分歧时，可写：“不认同本次不通过结论：提交判断与反馈所列Claude判断一致，现有反馈未指出实际差异。保留同版考点及逐点原文依据，请复核具体不一致项。”使用时补上本题考点和准确引文；未展开的模型不能推断已被认可。

## 三项通过后的建议：先发Arena，再优化，免复检

仅当三项状态均为实际passed且三模型门槛满足，才使用这个分支；disputed不冒充三项通过。

1. `arena-prepare --evaluation <当前三模型评估>`，**先在侧栏发出**arena-prompt.md、model-4.md、model-5.md的可点击链接及填写说明，让用户开始获取两份回复。
2. 有通过后的建议时，`qa-polish-template evaluations/polish-rNNNN.json --evaluation <当前三模型评估>`。助手在后台处理，用户无需补内容。记录arena_notice为刚才实际发出的通知；reviews逐项说明题面、Insight含义、考点标准、原文、结论及引用保持。
3. changes记录每个字段的field、before、after、stage、feedback_quote及reason。纯文本Insight使用field=insight；旧三字段对象仍使用insight.mechanism/priority/conclusion。其他允许字段为points.<ID>.criterion、author_notes、reasons.<seed|gpt|claude>.<决定性考点ID>。准确引用本次通过反馈，说明为何专业含义和判定不变；按writing.md保留决定性因素，考点减少背景且单点可判定，不趁表达优化实质拆改冻结标准。同一份记录为完整优化集合，追加新版时保留仍采用的此前改写。
4. `qa-polish <优化JSON> --evaluation <当前三模型评估>`只保存离线记录，**不调用质检**。冻结题面、原文、真假判断、引用、考点ID和分类保持。实质修改题面/含义/标准的建议记录为后续候选，不覆盖正在收集的版本。没有可采用建议直接等Arena，不强行优化。
5. 继续等两份Arena Markdown。最终export自动使用优化文字，并把依据放evidence/platform/postpass-polish.json；提交信息说明“通过对应优化前输入，优化后未复检”，不宣称新措辞已获平台通过。优化不新增第七份交付Markdown，也不使原通过失效。

## Arena与交付

用户填好后`arena-import --evaluation <当前三模型评估>`，再统一评估、具名排序及export。准备、导入和导出都会核对原证据门禁，不为交付表达优化再发送平台请求。异议备注进入提交信息.md，原请求与反馈留内部JSON，不含Cookie。仍交付一份提交信息和五份模型原Markdown。

旧任务保持原合同；升级说明不会清空旧题或迫使旧冻结任务重走检查。更新时保留题目、原文、判断和交付，先备份侧栏说明。

## 发送前与反馈后的必要研究参考

题目检查发送前，按[完整研究报告](insight-rubric-study.md)和[检查单](insight-rubric-checklist.md)确认Insight的决定性机制与本题决策相连。后两项质检发送前，检查目标覆盖、公开最低证据、等价路径及同版三模型判断；仍按用户真实选择与three_model_gate执行，不增加调用。

返回后核对总评、分项和实际输入：具体缺项/推理错误认可则修，只有“缺少Insight”标签或高分不能独自证明根因或通过。无法质检、HTTP/业务错误、空结果、用户网页报告和disputed各自保留；没有明确内容问题时不猜一种写作病因。相同历史输入有不同结论不等于已证明后台bug。建议可选，不机械加成决定性要求，不为刷出通过重复发送同输入。正常请求的无上限等待与并行两项策略保持。
