# 三模型采集

已授权使用当前工作区私有配置做本题必要调用。先 `lab collect seed --allow-live` 与 `lab render seed`；随后 `lab seed-evaluation-template evaluations/seed-rNNNN.json`，按全部决定性考点填写met/reason/quotes，`lab seed-check evaluations/seed-rNNNN.json`。若Turbo全部达成，先修订有专业依据的候选并重新冻结，不消耗GPT/Claude调用。若Turbo未达成，再分别 `lab collect gpt --allow-live`、`lab collect claude --allow-live` 及对应render；CLI会核对当前版本的Turbo判断。请求不带Insight/考点，GPT中高reasoning、Claude中高thinking。保留实际请求与返回型号，版本不符先核供应商映射，不能改显示名称冒充。

候选记录在测试前冻结，是防止倒推标准的版本记录；全部验证和自查通过后导出的版本才是最终提交锁定。最终仍要三个模型完整原文与判断，GPT/Claude至少一个整体达成。

完整原Markdown、JSON/SSE、metadata、截图和渲染manifest保存于responses/。截图显示题面、模型版号、原文哈希和完整正文，API渲染来源明确；远程资源阻断。原文不得改写，格式问题独立记录。

总时限及空闲时限由私有配置控制；Responses终止事件到达即停止等待，不被心跳无限延长。中途响应及失败记录保留；缺完整回复不判为不满足。已有原响应优先 `lab recover ROLE attempts/<hash>/ROLE/aNNNN.json`，不重复扣费。确有已修正的失败原因才带 `--retry-reason`重试，未知in_flight先核上游结果。成功原文不覆盖。

回复过短先检查截断或服务异常，别为了制造区分挑选样本。三份完整正文和截图齐全再做最终三模型判定。
