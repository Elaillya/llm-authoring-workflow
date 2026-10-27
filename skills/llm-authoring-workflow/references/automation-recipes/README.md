# 自动化配方库

默认路径为 ego-lite 混合操作：批量文本与结果读取用 `ego-platform.mjs`，选择/点击/上传用 ego 标准 API。先按 [浏览器手册](../automation-playbook.md) 启动，再按 [平台操作流程](../platform-automation.md) 执行各阶段和恢复规则。pi-web HTTP 采集与本地截图拼接保持。

## 当前主路径

| 文件/接口 | 用途 |
|---|---|
| [ego-platform.mjs](ego-platform.mjs) | 目标 itemID 校验、批量 textarea 写入/回读、滚动到字段、一次观察三项检查 |
| [platform-stages.mjs](platform-stages.mjs) | 常规入口：填写/暂存、单项质检派发/接续（先考点，后由agent判断达成性）、上传/预览/暂存；由调用者按既有门槛选择阶段 |
| ego `click/fill/press` | 题型/领域/达成下拉、少量文本编辑、质检按钮和备注控件 |
| ego `setInputFiles` | 直接上传本地截图，完成以平台预览与“已完成”为准 |
| [piweb-http.md](piweb-http.md) | 采集/恢复/截图的执行说明；界面型号验收、原生状态与会话核验 |
| [piweb-client.mjs](piweb-client.mjs) | 模型目录、发送意图/回执、只读观察与原文归档；默认单次发送 |
| [piweb-import.py](piweb-import.py) | 归档原文按字节导入，复用已有 lab 门槛与证据保护 |
| [piweb-capture.mjs](piweb-capture.mjs) | ego 一轮连续分段、布局检查、浮层恢复及拼接计划 |
| [stitch-screenshots.py](stitch-screenshots.py) | 整视口分段截图查重、裁边及按内容坐标拼接 |

`ego-platform.mjs` 是供 ego 的 Node 脚本导入的 ES 模块，不是整段丢入 evaluate 的旧配方。函数要求实际 page 和字符串 itemID，数据作为参数传入，不编辑公共源码里的 DATA。写入预检目标、只更新不同值；即时 DOM 一致仍需阶段回读和保存验证。详情及字段表以平台操作流程为准。

常规阶段优先用 `collectRole`、`prepareScreenshot` 和 `platform-stages.mjs`，参数直接来自已确认任务数据。底层 `ego-platform.mjs` 只观察/写读，阶段函数只在显式调用时派发对应操作，均不点击最终提交。机器回执自动生成，WORKLOG 留阶段摘要与目录；不要求重复抄录机器字段。页面匹配失败先 snapshot 确认，操作报错后先查状态，不自动重放未知请求。

## 旧平台配方：历史参考

`platform-fill-question-form.js`、`platform-fill-model-block.js`、`platform-upload-screenshot.js`、`platform-run-check.js`、`platform-check-result.js`、`platform-mark-agent-result.js` 保留旧内置浏览器实测记录，不作为新主路径或未知请求的自动回退。

已知差异：旧模型配方用原始字符串比较会因 CRLF→LF 误报；旧读取配方假设三项都叫“题目AI质检结论”，不能识别当前考点/达成性标题；React fiber 直调和 base64 主世界上传已由标准控件/文件 API 替代。旧环境的 evaluate 参数故障与 3 秒限制不能当作 ego 的通用限制。确需维护旧浏览器时先核实该环境与当前 DOM，不直接套用“历史通过”。

## 验证记录

- 2026-10-26：ego 实站完成字段填写/修改/刷新回读、三项触发与状态读取、截图上传/删除。题目和考点检查有有效通过回执；达成性本次上游失败，不能称三项通过。通用写入两字段修改/恢复约 0.066–0.140 秒，批量读三项约 0.004–0.015 秒；少量本机样本，不含服务等待，不是严格性能基准。
- 2026-10-24/25：旧内置浏览器六项平台配方及 pi-web HTTP 曾实站验证。该记录说明历史能力，不代表当前页面兼容或 ego 必须采用相同技术。
- 2026-10-24：旧 clip/fullPage 路径产生横向平铺伪影，改整视口截图后拼接与手工结果逐像素一致；拼接脚本能拦截已知伪影。2026-10-26 已用新模块重验短/长/代码表格三类现有会话，完整性仍需逐图目视核验。

公共目录只收通用逻辑与合成测试；账号、Cookie、itemID、个人题目/回复及执行脚本留在任务私有目录。
