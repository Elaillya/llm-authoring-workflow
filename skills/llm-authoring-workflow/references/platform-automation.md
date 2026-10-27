# 做题平台自动化操作流程（ego-lite）

自动化分支执行平台填写、修改、暂存、质检、结果读取或截图上传前，完整阅读本流程。候选设计、预算与专业返修按 [automation.md](automation.md)；浏览器启动和 pi-web 截图按 [automation-playbook.md](automation-playbook.md)。本流程不改变本地三模型门槛、原文保留或 Arena 交接边界。

默认路径：**稳定字段标识 + 批量文本脚本 + ego 标准控件操作**。平台通过网页操作，不复刻后台保存或质检 HTTP 接口。空间、题号、itemID、路径及材料取当前任务实际记录，不复用实测样本。

## 1. 核对目标与保存断点

读取当前任务TASK、WORKLOG，已有题目先lab status，确定当前版本及缺失步骤。找回已授权空间和平台标签页，用完整快照核对页面实际显示的业务题号、任务名称、题目ID、登录态和已有内容，以页面实际题目ID建立itemId目标；业务题号与平台itemID分别记录。URL的itemID可因站内切题而滞后，只作参考。有既有材料时与本地版本比较后接续，不直接覆盖。

将初始表单快照、空间ID、page label、实际itemID、版本保存到私有platform-web/rNNNN。后续每轮verifyTarget核对站点、做题页面及页面实际ID与已确认目标；URL差异仅返回提示，不阻止操作。实际ID与目标不符时核实是否切题，未加载则等待。控件缺失/重复先观察，查清运行中或未知请求后再操作。

完成判据：本地候选与平台目标对应、初始内容和断点已保存、未完成请求已查清。登录、验证码、控制权转移或身份不明时交给用户处理。

## 2. 填写题目阶段信息

前置：本地 prompt/Insight 已完成专业自查与唯一核心问句检查。

1. 用标准 `click()` 点题型标签；领域下拉展开后选择可见选项。单选 input 可能隐藏，点击标签；antd 下拉不当作原生 select，不直接调用 React fiber 的 onChange。
2. 用 [ego-platform.mjs](automation-recipes/ego-platform.mjs) 的 `fillTextBatch(page,itemId,values)` 一次填题面和 Insight；单字段编辑也可用 `page.fill()`。考点未定稿时不提前填写最终考点。
3. 回读文本、选中标签及字数/必填状态。`domMatches` 只代表即时 DOM 一致，不代表平台已经保存。网页将 CRLF/CR 转为 LF，比较时仅规范化换行；不 trim、不删除空格、不重新渲染 Markdown。本地原回复字节和哈希保持不变。
4. 平台自动暂存；阶段结束可点击精确匹配的“暂存”，观察保存反馈或“最近暂存时间”更新。首次接入、恢复、异常后或交接前，在没有运行中/未知请求时刷新一次核验预期字段。刚点击保存不能立即刷新，先确认保存完成；正常运行不每字段刷新。

完成判据：类型/领域准确，题面与 Insight 回读一致，保存完成。输入和模板不一致时先解决差异，再运行检查。

## 3. 运行题目难度与标签检查

按第 5 节保存输入和调用前状态，滚动到 `insight-agent-run-button` 后用标准 `click()` 触发一次检查，等待原请求。读取本次结论和完整详情；通过线为难度系数 ≥6，逐次记录系数、理由和调用次数。合理不通过按主流程修订复检；有依据的异议按第 7 节记录。服务异常与内容不通过分别处理。

完成判据：与本次输入对应的有效结论已归档并按主流程处理。随后本地完成考点、设计复核及冻结；调用次数增加本身不算检查完成。

## 4. 三模型门槛后填写考点与模型区块

前置：三份原文、同版判断与逐考点备注齐全，`lab check <当前评估>` 明确返回 `three_model_gate=true`。门槛前仅本地采集和评估，不向平台填写模型区块。

1. 批量填两类核心考点、豆包原文和备注；无非决定性考点填“无”。
2. 豆包达成下拉选“未达成”，回读选中标签；等待 GPT/Claude 文本框出现。
3. 一次批量填 GPT/Claude 原文和备注；标准下拉选择各自的本地判断，不为了展开页面改判。
4. 统一回读两类考点、六个模型文本框和三个判断标签，确认原文完整、版本对应及暂存完成。

完成判据：本阶段全部字段与本地材料一致，Seed 未达成、GPT/Claude 至少一个达成。换行规范化不能被误判为原文丢失；正文确有差异时只补失败字段，再统一核对。

## 5. 质检触发、等待与结果读取

本节适用于三项检查。自动化分支按 [automation.md](automation.md) 的网页检查合同执行；手动分支是否执行后两项仍按 [optional-model-checks.md](optional-model-checks.md)。

### 发起前

在私有 `platform-web/rNNNN/checks/` 保存：阶段、版本、完整输入、确定性 JSON 的 SHA-256、调用前次数/运行状态/旧结果、开始时间。题目检查绑定类型/领域/prompt/Insight；考点检查绑定 prompt/Insight/两类考点/三份回复；达成性检查再绑定三模型判断及备注。页面增加依赖时扩展快照。

本地门槛通过且字段就绪后，先运行考点质检。agent核对当前输入和本次调用后决定是否继续：正常通过可继续；认可不通过先返修；有充分依据的异议按第7节完成备注后，或已确认服务异常且平台允许标异常/备注后跳过，也可继续达成性质检。继续不等于质检通过，原结论或异常如实保留。运行中、请求未知或输入变化先等待/核实，不能直接作为异常跳过。此为agent执行规则，程序只提供单项派发、读取和防重发，不校验通过结论、不要求额外放行文件或批准。每次点击后回读，期间保持输入不变，不刷新或关闭承载请求的页面。

### 点击与异常

先 `scrollToField(page,itemId,按钮字段)`，再 `page.click()`。嵌套滚动区域中，标准 click 实测可能已经触发服务却仍报不可见超时。捕获错误后先回读 loading、调用次数和结果：有触发证据就等待；没有证据也不能猜测“没发出”。只有确认未发送且阻碍解除才再点，无法确认则保存断点暂停。不要重放包含该点击的整轮脚本，也不要切浏览器或改走接口重发。

### 等待与完成

一次 `readChecks()` 同时读取三项。调用次数仅证明触发，不证明完成；disabled 与 loading 分开判断，实测 loading 时按钮也可能 `disabled=false`。

| 返回的观察状态 | 助手动作 |
|---|---|
| `running` | 原请求进行中；忽略残留结论、旧报错和重跑提示，继续等待，不再次点击 |
| `blocked` | 无 loading 但按钮禁用；检查缺失输入/页面状态，不据此断言请求正在运行 |
| `result_visible` | 无 loading、无重跑提示且有结论；绑定本次输入和触发证据后才接受为本次结果 |
| `stale_or_no_result` | 有重跑提示；结合输入哈希、曾观察到的运行状态和错误详情，区分输入修改失效与服务失败 |
| `not_run` / `unresolved` | 核对历史记录；已有请求但状态未知时暂停，不自动重新触发 |

观察可分 15–30 秒窗口；窗口到期只再次读状态，不给正常请求设总时限。每轮只打印阶段、运行状态、次数和结论；完成或状态异常时用 `readChecks(page,itemId,{details:true})` 读取全文并落盘。持续报告进度，单次阻塞等待不超过 60 秒。用户接管时停止后续操作，按浏览器指南交接。

完成判据：每项分别有当前输入对应的有效结果，或原请求已结束且有明确服务报错/无有效结果证据。完成后立刻归档完整回执，不能仅在 WORKLOG 写“通过”。结果不明继续等待/暂停；服务错误不刷至通过。

页面要求标记 Agent 结果时，正常返回有效结论选“正常”（包括内容不通过）；只有本次已确认的服务报错或无有效结果才选“异常”并写技术原因。标记控件未出现则记 `not_present`，不额外发起检查。

## 6. 截图上传与保存

按浏览器手册取得真实 pi-web 会话截图，问题、完整回复、型号及 high 齐全。每角色用标准 `page.setInputFiles('[data-field-id="<模型前缀>-screenshot-file-input"]',[绝对路径])` 上传；同角色多图可一次传路径数组，不用 base64 中转或主世界脚本注入。

等待上传 spinner 消失，同时确认正确区块有文件名/预览、“回复截图”变为“已完成”。接口返回或 input.files 非空只表示派发，不表示服务器已上传；前端清空 input.files 也不代表失败。报错先检查文件是否已出现，避免重复传。

本次误传文件需移除时，核对文件名并使用该预览的精确删除按钮，不依赖动态数字 ID，不清空其他附件。再次回读并确认暂存。正式流程不上传合成测试图或做题平台截图冒充模型会话证据。

完成判据：三个区块的完整证据与对应会话匹配，上传及保存完成。文件按模型前缀分配，不按第几个 file input 猜。

## 7. 反馈、修改与恢复

先归档旧回执、输入和调用次数，再修改检查相关字段。**实测修改会清空页面检查结论，恢复相同文字也不会恢复原回执。**正式运行避免来回改字段试探控件，先定稿再检查。

认可的内容问题按主流程和 [repair.md](repair.md) 修复：Insight/考点改变须统一重评原回复、重新确认门槛后才运行相应后两项；改 prompt 另建版本并从 Seed 采集。依赖输入变化或平台提示失效时，旧回执只作历史。三项真正通过后的离线表达优化仍按原主流程处理，不为恢复页面展示刷检查。

有依据的异议保留原不通过，明确告知用户并给可复制备注。只在对应检查区块定位实际出现的“正常/异常”标签及异议备注框，用标准 click/fill 填写并回读；未出现记 `not_present`，不通过增加调用次数使控件出现。

服务已明确报错/无有效结果时按平台规则标异常并记录技术原因，不计题目失败经验、不声称通过。平台允许异常备注后继续时按自动化合同如实记录，否则暂停。不能用浏览器执行成功代替专业检查通过。

中断恢复：找回原空间/page label/itemID → 比较当前字段与 WORKLOG 输入快照 → 运行中继续等，已完成归档，输入变更则标旧回执失效，触发未知不重放脚本。登录/验证码/用户接管先交接，不另建空间绕过。

## 8. 最终回读与交接

无运行中或未知请求后，核对题号/itemID、版本、题面/Insight/考点、三份回复、判断/备注、截图和三项实际状态。确认暂存；首次接入、异常恢复或有持久化疑虑时刷新一次核对，不额外发送“验证请求”。

`lab arena-prepare --evaluation <当前评估>` 通过且主流程允许交接后，发 Arena 填写链接和平台状态。保留平台页给用户继续，按 ego 指南结束空间任务；用户原有标签页保留。自动化不勾“确认后继续”、不点最终“提交”，固定作业判断保持原值。分别说明通过、异议、异常或未执行，不合称“三项通过”。

## 字段与脚本速查

当前标识来自实站 DOM，不是永久不变的后台 API 合同。缺失/重复/改版时先观察再调整映射。

| 内容 | `data-field-id` |
|---|---|
| 题型 / 领域 | `question-type-radio` / `question-domain-select` |
| 题面 / Insight | `question-input` / `insight-input` |
| 决定性 / 非决定性考点 | `insight-description-input` / `non-decisive-insight-description-input` |
| 模型前缀 | Seed=`doubao`，GPT=`gpt56`，Claude=`claude` |
| 模型回复 / 备注 | `<前缀>-markdown-input` / `<前缀>-achievement-note-input` |
| 模型判断 / 上传输入 | `<前缀>-achievement-select` / `<前缀>-screenshot-file-input` |
| 检查前缀 | 题目=`insight`，考点=`core-point`，达成性=`attainment` |
| 检查按钮 / 结果 / 失效提示 | `<前缀>-agent-run-button` / `<前缀>-agent-result` / `<前缀>-agent-rerun-warning` |

常规操作优先用下一节的阶段函数。`ego-platform.mjs` 提供 `verifyTarget`、`fillTextBatch`、`readTextFields`、`scrollToField`、`readChecks`、`readStage`（字段/选择/暂存时间）与 `readUpload`（对应角色预览/完成标记），均要求已核验的字符串 itemID。批量写入预检全部目标，只更新不同值；它不会自动质检/提交，也不决定专业门槛。以下为诊断/回退的私有执行片段，变量与绝对模块 URL 由本轮任务提供：

```js
const {verifyTarget, fillTextBatch, readTextFields, scrollToField, readChecks} =
  await import(moduleFileUrl);
await verifyTarget(page, itemId);
const expected = {'question-input': input.prompt, 'insight-input': input.insight};
console.log(await fillTextBatch(page, itemId, expected));
console.log(await readTextFields(page, itemId, Object.keys(expected)));
// 然后按第 2 节确认平台状态和保存；不是立即触发检查。
```

下拉：滚动到字段后 click 展开，首次观察选项；当前可见选项可用 `.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title="实际选项"]` 点击，再回读字段的 `.ant-select-selection-item`。必要时用标准 `press()` 键盘法补齐，不照搬旧环境固定的 ArrowDown 次数。

## 10. 阶段组合与只读恢复

导入 `platform-stages.mjs`，每次传入同一个已核对的 page、字符串 itemId、当前 version 和任务私有绝对目录 directory。一个目录表示一次输入固定的阶段；配方自动保存输入、操作意图和回执，WORKLOG 仅引用目录。参数改变时先归档旧结果并确认操作状态，不能靠新目录重发未知请求。旧任务没有阶段记录时沿用上文的真实断点核验，不为补记录重做检查或上传。

| 函数 | 输入与完成判据 |
|---|---|
| `fillStage(page,{itemId,version,directory,values,selections})` | values 按 data-field-id 给字符串；selections 给界面可见标签。按依赖顺序选择、批量写入、统一回读后暂存；字段一致且暂存时间变化返回 saved |
| `startChecks(page,{itemId,version,directory,keys})` | keys 为 insight / core-point / attainment；自动保存依赖输入并分别派发一次。输入相同且次数增加一或明确运行证据才关联本次结果 |
| `observeChecks(page,{itemId,directory})` | 批量只读当前状态；complete 表示本次检查已返回，结论仍需区分通过/不通过。输入变化、旧结果或无法关联不能标完成 |
| `waitChecks(page,args,{windowMs,onWindow})` | 最多 30 秒观察窗口，默认 15 秒；onWindow 可在独立 pi-web 页准备一张截图，然后回读平台。正常检查没有总时限 |
| `uploadScreenshot(page,{itemId,version,directory,prefix,imageFile})` | prefix 为 doubao/gpt56/claude；绝对图片路径。等检查结束，上传一次、确认新增预览/完成标记和暂存后返回 uploaded |
| `feedbackStage(page,{itemId,version,directory,key,label,note})` | 应用agent已确定的正常/异常及备注，限对应区块，暂存回读；不判定专业结论 |
| `receiveCheck(page,{itemId,version,directory,key,priorDirectory,userStatement})` | 接收用户已完成的一次重跑，只读关联前次输入/次数，unknown不补造派发 |
| `verifyStage(page,{itemId,values,selections,checkboxIds})` | 最终统一只读；复选框ID来自实际观察，不自动勾选或修改 |

读取状态、save_unconfirmed、反馈与人工接续参数、等待安排及自动证据导出见[接续规则](automation-recovery.md)。三模型平台字段用lab platform-fields生成，按依赖分批填写。等待器跨窗口保留进度，不重复输出未变化的完整结果。

`fillStage` 的题型标签使用“分析决策”“开放推荐”“How-to”等当前界面文字。先填豆包并选未达成，等后续区块实际出现，再第二阶段填 GPT/Claude；不要一次传尚不存在的字段。示例中的 values/selections 已由本地确认内容生成，不需要用户重复填写配置：

```js
const {fillStage,startChecks,waitChecks,uploadScreenshot} = await import(stagesModuleUrl);
const filled = await fillStage(page,{itemId,version,directory:fillDir,values,selections});
if (filled.status !== 'saved') throw Error('Inspect fill/save result before continuing');
// 以下只在本地三模型门槛成立、输入已齐且本题需要后两项时执行。
const criteriaArgs = {itemId,version,directory:criteriaDir,keys:['core-point']};
console.log(await startChecks(page,criteriaArgs));
// 之后按需 waitChecks(page,criteriaArgs)，让agent核对结果、处理反馈。
// 跨轮次agent已判断本次考点处理允许继续时，单独执行下一段：
const attainmentArgs = {itemId,version,directory:attainmentDir,keys:['attainment']};
console.log(await startChecks(page,attainmentArgs));
// 两段分轮执行，不把整块脚本一次重放；未知请求先只读恢复。
```

旧任务若使用已移除的 `advanceModelChecks`，继续复用原组目录中的 criteria/、attainment/ 子目录及其意图/回执，改用单项 startChecks/observeChecks/waitChecks 接续；已有记录不重置，不为换接口重新触发检查。

保存/上传派发返回异常后，只观察已有意图对应的字段、预览及暂存；暂存时间未变化或同名附件来源不明时不假定成功。unknown、mismatch、needs_attention 或抛错先诊断具体原因；检查运行中不写字段、不上传、不刷新。阶段函数保护操作完整性，不新增专业评分门禁，不自动选异常/异议，不点击最终提交。

## 实测依据与边界

2026-10-26 ego 实站覆盖题型/领域、十个文本框、修改暂存刷新回读、三项真实检查触发/读取、截图上传/删除。题目与考点检查有有效通过回执，达成性本次上游失败，不声称三项通过。目标校验和观察状态分类以合成材料回归；不为文档维护再调用线上检查。

本机少量样本：标准两文本框约 1.11 秒，旧配方约 0.083 秒，通用两字段修改/恢复约 0.066–0.140 秒，文件输入派发约 0.172 秒，批量读三项约 0.004–0.015 秒。字段长度和位置不同，数字不含服务等待，不是严格性能基准。收益主要来自减少浏览器往返、长快照和重试。

旧平台 `.js` 配方只保留历史参考，其 React 内部调用、文件注入和旧结果标题假设不再作为主路径；新流程使用 ego 模块与标准 API。公开维护只保留通用逻辑和合成测试，私人题目、原回复、itemID、账号、Cookie及本机运行路径留在私有任务目录。
