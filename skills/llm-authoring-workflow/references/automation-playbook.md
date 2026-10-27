# Arena 前浏览器操作手册（ego-lite）

默认使用 ego-lite。进入做题平台的填写、修改、质检、截图上传或中断恢复时，完整阅读 [平台操作流程](platform-automation.md)；这是平台步骤和完成判据的唯一执行说明。业务顺序、候选预算和返修规则见 [automation.md](automation.md)。

## 0. 浏览器启动与标签页接续

- 先读本机 ego-browser 技能并执行 `ego-browser skill`，按已安装版本的指南调用。ego 不是 Playwright，不复用旧 `ZCODE_PLUGIN_ROOT` bootstrap、`getByRole` 或内置浏览器标签页 API。
- 用户指定空间时，用 `listTaskSpaces()` 找出数字 ID。明确授权操作用户空间后使用 `claimTaskSpace(id)`；自己仍控制的空间用 `taskSpace(id)` 续接。没有指定空间时按指南只为本任务创建一个空间，不为错误恢复另建空间。
- `task.tabs()` 按 URL 与目标 itemID 找平台页、按用户提供的服务地址找 pi-web 页；无 label 的用户页面先 adopt，记录返回的 page label。跨轮次复用同一空间及标签；标签丢失先重新列举，不按数组位置取。
- 首次及页面改版用 snapshot 确定结构。常规轮次优先按字段批量读取小 JSON；截图用于模型证据或视觉核验，避免每一步同时抓全页快照与截图。
- Windows 每轮写一个新的 UTF-8 `.mjs` 完整脚本，通过 `ego-browser nodejs -e "await import('file:///绝对路径/round-01.mjs')"` 执行。中文放文件中，路径用绝对路径，不用 PowerShell 管道传代码。空间和 page label 持续存在，JS 变量不跨进程保留。
- 登录、验证码、用户接管或空间失活时按指南停止并交接，记录断点；不得另建空间绕过。需要用户处理中途问题使用 `task.handOff()`，不是完成任务。完成 Arena 交接时保留用户继续操作的平台结果页，调用一次 `task.finish({keep:[平台page.label]})`；用户原有页面保留。
- 本机 ego 不可用时先按安装技能诊断并报告。旧内置浏览器配方仅作历史参考；不在未知请求上切换执行渠道重发。

## 1. pi-web 采集与证据

### 1.1 HTTP 主路径

前置：按 automation.md 启动步骤取得本任务已确认的服务地址和答题目录；所有 HTTP 请求、会话链接及标签页匹配均使用该记录，示例端口与历史实测地址不作为默认值。

按 [piweb-http.md](automation-recipes/piweb-http.md) 的启动、发送、观察与归档步骤执行，这是 pi-web 采集/恢复的唯一执行说明。使用 `piweb-client.mjs`；界面显示型号为准，后端 ID 仅作路由关联。发送受理不等于完成，最终回复必须结合运行态、冻结题面与 entry ID 核验。默认单次 POST；两段式的真实发送验收完成后才切换。先 Seed，后按门槛 GPT/Claude。

### 1.2 浏览器回退

仅在明确尚未发送、服务可用但 HTTP 接口不适配时采用：按快照选答题目录 → 独立新会话 → 核对界面显示型号/high/仅聊天 → 原样填写冻结 prompt → 发送一次。随后回到 piweb-http 的只读完成判定和归档；接口不兼容可按已核实 JSONL 核对运行/最终消息，不能仅看 stopReason 是否存在。发送状态未知时只核对原会话，先保存断点。

### 1.3 截图

三模型门槛后按 piweb-http 第 4 节，用已归档的会话及消息 entry ID 打开真实聊天页，正常控件折叠思考，snapshot 核对内容。`piweb-capture.mjs` 一轮连续采集整视口 PNG、记录实际几何/覆盖区间并恢复临时样式；`stitch-screenshots.py` 验证覆盖、比例和平铺并附真实状态栏。退出码与 ok 成功后仍须目视检查首尾、接缝、完整正文、代码/表格/公式、显示型号及 high。

文件放任务 `platform-web/rNNNN/screenshots/<角色>/attempt-001/` 下，原段/计划/长图保留。最终长图按已核验模型显示名称命名，上传使用prepareScreenshot返回的imageFile，具体见[目录与命名](workspace-layout.md)。失败按配方处理，只重截不重取回复；确认成图完整后按平台流程第 6 节上传。ego 的聊天页 fullPage 不展开内部滚动区，不能代替长图。当前 DOM 适配与实测版本边界见 piweb-http。

## 2. 做题平台入口

按 [平台操作流程](platform-automation.md) 执行：核对目标 → 题目填写/暂存 → 难度标签检查 → 本地冻结、采集和三模型判断 → 门槛后填考点/模型 → 后两项质检 → 上传截图 → 最终回读/Arena 交接。

平台不点击最终“提交”，不勾选“确认后继续”，不更改固定作业判断。所有专业判定仍由主流程完成；浏览器成功执行不等于质检通过。

## 3. 配方选择

常规轮次优先阶段接口：`collectRole` → `piweb-import.py`；平台 `fillStage` → `startChecks/waitChecks`（先考点，agent处理结果/异议/异常后决定是否发达成性） → `uploadScreenshot`。截图用 `prepareScreenshot`，可放在后两项检查的观察窗口中，在独立 pi-web 页执行；完成一张后回读平台，不并发操作同一页。接口、参数与恢复见各站执行说明，原子操作保留作诊断回退。回执自动保存，WORKLOG 只写阶段、决定、异常和证据位置。

主路径使用 [ego-platform.mjs](automation-recipes/ego-platform.mjs) 的文本批量写入、回读、滚动与三项检查观察函数，控件操作使用 ego 标准 API；详见 [配方库](automation-recipes/README.md)。等待循环在浏览器脚本外层分段进行，不在一个 evaluate 中长时间等待。

页面定位失配时先读快照，必要时用标准 fill/click/press 补齐后回读；不要默认返回 React fiber 调用、文件注入或复刻平台 HTTP。旧平台 .js 的结果标题、换行比较与执行环境存在已知差异，保留作历史参考。
