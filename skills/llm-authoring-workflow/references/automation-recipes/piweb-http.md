# pi-web 采集与截图配方（v2）

自动化分支首次采集、恢复、读取异常或截图时完整阅读本文。使用 `piweb-client.mjs` 处理原生 HTTP，`piweb-capture.mjs` 处理 ego 页面；专业判断、重取权限、三模型门槛仍由 automation.md 决定。运行记录放当前任务私有目录，不改公共源码中的参数。

## 1. 启动预检

1. 从本任务 WORKLOG 取得用户确认的完整服务地址及服务端答题项目目录。新任务先问，已有明确记录直接复用；没有默认地址、端口或目录。
2. 使用 Node ≥18（内置 fetch），截图另需 ego-browser 与带 Pillow 的 Python。先执行本机 `ego-browser skill`。公共文档不固定个人运行时路径。
3. `createPiWebClient({baseUrl, cwd, headers?, localJsonl?})` 必填前两项。地址支持路径前缀；认证头从私有文件读取，禁止将凭据写在 URL 或输出到日志。`localJsonl:true` 仅用于已确认服务与采集器共用文件系统的情况，远端保持 false。
4. 调用 `preflight()` 读取模型目录及运行列表。**型号以界面显示名称为准**：通过目录的 `name`（为空时 UI 使用 `id`）匹配 Seed/GPT/Claude；Seed 当前展示 `seed-2.1-turbo`。后端 ID 只是目录给出的路由参数，不限制其具体值，不用 assistant 的实际返回 model/responseModel ID 判定型号正确与否。截图时再次核对可见型号及 high。同名多 provider 时确认映射；缺少目标显示名/high 时停止。
5. 私有记录写入服务/浏览器版本、模型显示名、解析的路由与 provider、当前版本/角色及冻结 prompt 路径。读取接口形状变化时诊断当前版本，不自动升级服务。

完成：目标界面型号及 high 可用，答题目录明确，尚未发送。

## 常规入口：采集接续与导入

新任务优先 `collectRole(args, options)`；下文单步函数用于诊断和旧任务接续。每个版本/角色/获准尝试固定一个私有目录，同目录恢复自动判断发送、等待或归档断点；发现既有完整归档时离线校验后返回，不重复网络读取或生成。目录中的损坏记录必须先处理，不能换目录掩盖未知请求。

```js
const client = createPiWebClient({baseUrl, cwd}); // 均为本任务已确认值
await client.preflight();
const result = await client.collectRole({directory: attemptDir, promptFile, role, version},
  {windowMs: 25000, onChange: state => console.log(state)});
console.log({status: result.status, reason: result.reason});
```

`archived` 后运行 `python <配方目录>/piweb-import.py --workspace <任务目录> --attempt <尝试目录>`。该桥接复用 `prepare_model/import_model`，检查当前冻结题面、版本、角色、原文及快照哈希，按字节原子写入占位文件；中断后可重入。已有相同导入直接复用，不覆盖不同原文，也不替代授权替换流程。归档与导入保持分离，某一步失败无需重做采集。

补取/授权替换已有原文时，先取得 `model-replace-prepare` 返回的替换入口；归档后给本脚本追加 `--replacement-id <ID>`，会校验入口角色/版本并复用 model-replace-import 归档旧原文。普通导入仍拒绝覆盖不同原文。

同一个 client 复用模型目录；接口故障自动失效缓存，发现界面目录变化时 `readModels({refresh:true})`。Seed 先行，后续两个角色获准时可 `Promise.allSettled` 并行采集，逐项处理结果；本地导入逐角色串行。模型内部重试仍等待原会话，失败快照自动存为 `failure.json`。三模型门槛失败时按 automation.md 的每内容版本一次额度补取；采集器本身不判断达成或自动重抽。

## 2. 单次发送与恢复

默认 `startSingle` 保持已实测的单次 POST：新会话 + 选定模型 + high + `toolNames:[]` + 冻结 prompt。每个角色、版本、获准尝试使用一个固定私有目录；**先查已有目录和 WORKLOG，再决定是否首次调用**。换目录不能当作绕开未知发送的办法。

```js
// 普通 Node 脚本；变量均来自当前任务记录，使用绝对文件路径。
import {createPiWebClient} from '<配方目录的绝对路径>/piweb-client.mjs';
const client = createPiWebClient({baseUrl, cwd, headers, localJsonl});
const checked = await client.preflight();
const started = await client.startSingle({
  directory: attemptDir, promptFile, role: 'seed', version,
  provider: checked.models.seed.provider,
});
console.log({status: started.status, sessionId: started.sessionId});
```

函数读取冻结文件的原始 UTF-8，不 trim、不附加换行或指令。`create-intent.json` 以排他方式写入并落盘后才发送；回执保存为 `create-receipt.json`，并核对配置关联。`accepted` 只代表受理，不代表完成。重复或并发调用同一目录会拒绝第二次发送。

两段式 `createSession(args)` → 保存 ID → `sendPrompt(attemptDir)` 已实现，合成断线测试通过；0.12.2 已实测空会话可读、high/仅聊天保持。**真实发送全过程未验收，暂不替换默认 startSingle。**后续正常授权出题可验证此路径；创建和发送分开调用，发送前验证空会话与配置，发送意图排他落盘。空会话不可读取或运行时不在时停止，不自动重建。

任何 POST 超时、断线、回执丢失或 HTTP 错误，均保留意图、已有 ID 和原件，先运行只读观察。没有回执或 running 列表没有 ID 不能证明没发出。已知 ID 从原会话恢复；未知 ID 根据私有时间/题面记录人工核对已有会话，不猜测、不补写虚假回执、不自动重发。`send-intent.json` 存在时重复发送也会被拒绝。本地记录不是服务端幂等保证；技术失败及补取次数按本题合同决定。

## 3. 等待、读取与归档

```js
const observed = await client.watchAttempt(attemptDir, {
  windowMs: 25000, intervalMs: 1500,
  onChange: state => console.log(state),
});
// 跨轮次继续调用 watchAttempt；窗口结束不取消生成，更不再次 startSingle。
if (observed.status === 'complete') {
  const result = await client.archiveAttempt(attemptDir);
  console.log({status: 'archived', replyFile: result.replyFile});
}
```

观察窗口约 15–30 秒（单次网络读取另有有限超时），正常生成无总时限。运行中只轮询轻量 `/api/agent/running`；准备认定结束时读取会话及详细运行态，再复查运行列表。外层 `running:true` 可仅表示进程存活；必须结合 isPromptRunning、isStreaming、压缩/bash、队列等状态。内部重试也等待原请求。

| 状态 | 下一步 |
|---|---|
| running | 继续原会话只读观察；观察窗口结束不取消生成 |
| read_error / connection_error | 临时读取失败在窗口内退避，连续三次失败返回 connection_error；保留断点，恢复连接后观察原会话 |
| auth_required | 401/403，恢复本服务登录/认证后只读接续 |
| local_error / protocol_error / service_error | 分别检查私有记录完整性、接口结构、非暂时 HTTP 错误；立即报告具体原因，不伪装成生成等待 |
| awaiting_input | 查明待输入原因，保存断点并交接 |
| complete | 归档及本地 Markdown 校验后导入 |
| failed | 归档本次 API 快照/结束原因，按本题技术失败规则处理 |
| unknown / ambiguous / mismatch | 保存快照及断点，核对原会话；暂停导入与发送 |
| prepared | 已创建但尚无发送意图；仅在两段式获准试用且核对后单独 sendPrompt |

成功要求：当前分支完整、恰好一个与冻结 prompt 完全相同的用户回合、high/仅聊天、同一选定配置，最终 assistant `stopReason=stop` 且正文非空。前置 error 保留，但只导出最终正常回复；error/aborted/length/toolUse/空正文分别判失败。多回合、多份成功回复、缺失 entry ID/历史截断或未知结束值停下核对，绝不把“有 stopReason”当完成。配置关联校验用于防止会话被切换，与模型后端实际返回 ID 无关。

`archiveAttempt` 保存 `reply.md`、`session.json`（API 原件，含失败尝试）、`result.json`（题面/正文/快照哈希、版本、角色、显示名及配置关联、用户/回复 entry ID、结束原因等）。已存在归档先核验哈希再复用，缺文件或改写时停止，不覆盖。JSONL 可访问且已开启 localJsonl 时按接口 filePath 对照用户和最终消息，禁止猜转义目录；不可访问如实记 unavailable。失败或未知观察的 `detail` 由调用脚本另存私有 `observation-<序号>.json`，不要打印整篇回复或认证配置。

从归档到本地原文优先用本页常规入口的 `piweb-import.py`。旧任务仍可按字节复制再运行原 `lab model-import`；已有不同回复遵守替换授权与归档规则，helper 不替代 lab 门禁。

旧任务没有新发送记录时使用 `observeSession({sessionId,prompt,model})` 只读核对，其中 prompt 来自旧冻结文件，model 来自已核实的选定配置。已有有效原件不迁移、不为补新记录重取回答；保留旧 WORKLOG 与新观察证据即可。

## 4. ego 分段截图

目录按[工作区与文件命名](../workspace-layout.md)中的版本/角色/尝试分层。最终图名为归档中的模型显示名称加`.png`，例如`GPT-5.6 sol.png`，由配方生成；路由ID不用于命名。旧merged.png恢复时保留原件并提供同字节的模型名副本。上传始终用返回的imageFile，不自行拼接固定文件名。

常规入口为 `prepareScreenshot(page,{archiveDirectory,outputDir,pythonExecutable})`，Python 路径为带 Pillow 的实际可执行文件绝对路径。它按归档绑定会话/回复/版本，组合下述分段与拼接；已有完整 plan 可继续拼接，已有回执且长图哈希一致则复用。返回 `needs_visual_review` 后目视核验，再上传；这不是新增用户审批。原段不完整、已有成图却缺少成功回执或输入变化时保留旧目录，核对后另开截图尝试，不能覆盖。下述单步函数仍用于诊断和旧任务。

截图可以与后两项网页质检的等待重叠：平台页保持输入不变，每个观察窗口在独立 pi-web 页准备一张，随后回读平台状态。上传等检查结束；回复替换后旧截图失效，仅 Insight/考点评估改变而回复未变可复用已核验图，不强制重截。

仅在三模型门槛后执行。复用已授权空间/页面，用 `sessionUrl(baseUrl, sessionId)` 打开会话；先 snapshot 核实当前 DOM，正常控件折叠思考，核对问题、最终回复、可见型号与 high。截图不会发起生成。

```js
// 在 ego 的 UTF-8 .mjs 脚本中导入，变量来自已归档 result.json。
const {captureConversation} = await import('<配方模块的 file:///绝对URL>/piweb-capture.mjs');
const captured = await captureConversation(page, {
  baseUrl, sessionId, userEntryId, entryId, modelId,
  modelLabel: displayName, // 来自原生模型目录/已核对界面；不是上游实际模型 ID
  outputDir: screenshotAttemptDir, // 绝对路径，独立的新截图目录
});
console.log(captured);
```

一轮脚本连续设置 scrollTop、等待两帧、回读实际位置、整视口 CSS 比例截图，保留约 80px 重叠并到真实底部；逐段记录 progress.json，成功才写 plan.json。核对前后布局不变及横向内容没有截断。临时样式只隐藏已验证的回底按钮和滚动条，finally 恢复样式与滚动位置。KaTeX 隐藏的无障碍 MathML 副本不当正文溢出，实际可见公式仍检查。

每轮最多 30 秒/默认 80 段。超限、截图失败、布局变化或横向溢出时保留原始段，**没有完成 plan 就不拼接上传**。用正常 UI 处理布局后在新的截图目录重新采集，不重取模型回复；超长会话可按原标准分段方式人工接续并核验全部覆盖。不得只因已有 PNG 就宣称截图完成。

```text
python <配方目录>/stitch-screenshots.py --plan <绝对截图目录>/plan.json
```

拼接器验证首尾、顺序、覆盖缺口、尺寸、DPR 比例、小数坐标和横向平铺，附末段真实型号/high 状态栏。成功需进程退出 0 且 JSON `ok=true`；失败退出 1，已有输出不覆盖。按全图及接缝检查问题、完整正文、公式/代码/表格、型号、高档位与浮层；目视通过后按平台流程标准文件上传。原段、进度、计划与最终图一并保留。

## 5. 验证与兼容边界

2026-10-26，pi-web 0.12.2 / pi 1.2.0、ego lite 0.6.1.11：新客户端只读核对已有短/长/代码表格会话，正文与 JSONL 一致；新截图模块生成三张完整图并目视检查，长回复 4 段样本采集约 1.8 秒（含布局检查，不含导航和拼接）。空会话创建已验证，未发送测试问题。发送/响应丢失通过合成测试，不能称真实生成全过程已验收。

DOM 适配器目前针对上述中文 UI；语言或结构变化时先 snapshot，按已观察的元素调整，不猜 selector。聊天页 fullPage 没有展开内部滚动区，原生 HTML 导出包含不同内容/状态，二者均不作当前主证据路径。接口不兼容可读取已核实 JSONL，截图不兼容可使用标准分段；回退只处理读取/截图。浏览器发送回退须明确尚未发送且服务可用，仅 HTTP 接口不适配；服务停机先恢复服务。
