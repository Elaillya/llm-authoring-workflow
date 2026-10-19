# 本地失败观察、认可经验与修复

同一父工作区的各题默认共享local/question-memory.sqlite3；显式共享组按[LOCAL_MEMORY.md](LOCAL_MEMORY.md)使用所有者的同一库。原题库entries/events和重复检查快照保持；failure_observations、failure_reviews保存观察及追加复核。未配置共享组时首次按需建立，不清空旧库；共享组主库缺失时报错。数据不进入Codex全局记忆或GitHub，不做跨库复制；已配置成员直接读写同一份库。

## 什么会被记录

- lab seed-check：Seed已满足全部决定性点。
- lab check及平台后两项入口门槛拦截：Seed全达成和/或GPT、Claude都未全部达成。
- qa-run返回实际“内容不通过”：question、criteria、attainment，包含初期还没填points的题目检查。

自动记录绑定题目身份、题面/Insight、评估哈希或平台请求/结果哈希和实际反馈。相同来源重复读取不重复创建事件，旧内容不覆盖。模型能力结论只限本题本次回复；真正原因需助手分析，不能由一次未命中推断整类题或模型的普遍能力。通过、登录失效、HTTP/服务错误、返回不明不是不合格题经验。

纯验证函数check_seed/check_three与status不因读取证据自动生成失败事件。工具更新不会擅自扫描旧题并给历史不通过批量盖“认可”；旧失败需要时可对原同版输入复用已保存检查或运行原评估检查命令，再逐条复核。不会因此自动重新请求平台或模型。

## 复核后才能作为可靠经验共享

```bash
bin/lab failure-context --limit 12
bin/lab failure-show <event_id>
bin/lab failure-review-template <event_id> evaluations/failure-review-<新名字>.json
# 助手填好文件后：
bin/lab failure-review evaluations/failure-review-<新名字>.json
```

verdict支持accepted/disputed/unresolved。认可时必须写具体cause、可执行prevention、applicability及准确evidence_quotes，由助手负责专业复核；来源/网络错误不能编成经验。复核历史追加保留，最新决定生效；同一复核重复写入幂等。不认同的意见退出可靠经验，平台qa-disagree会同步标为disputed；即使上一次登记中断，已有平台异议的事件也不再作为认可经验返回。

memory-context与已完成选题的begin返回failure_learning，包含有限条认可经验与待复核观察，按所选领域/分支优先。accepted_count/pending_count显示总数，必要时failure-context --limit 50查看更多，再failure-show打开具体证据。设计前结合适用范围阅读，不能照搬成新的固定Insight模板。

例：某次考点把“核实数据是否完整”和“计算结果是否正确”合为一条。核实反馈确实指出这两个可独立满足的条件后，可以记录原因“独立事实合并导致达成判断含混”，改进“设计时先分开每个可独立判定的事实，再检查是否属于真正决定因素”，范围“适用于同类复合考点；不是把所有必要条件拆到失去机制”。这是构造说明，不是已发生失败或真实模型结果。

## 认可考点不通过如何修复

按[repair.md](../skills/llm-authoring-workflow/references/repair.md)执行：保持prompt，先专业修正Insight/考点并统一重评；不能满足门槛时先征求用户是否重新提供GPT/Claude回复，最后才修改prompt。新冻结版本保留原件；同prompt存储支持原回复复用。替换工具记录具体授权、旧/新哈希和归档，待导入前保留当前原文；导入后重新统一判断。每次尝试均保留，不能只保留最有利的一次。

资料来源不充分、失败原因未验证时保持unresolved，不把假说写成既定规律。经验是设计辅助，不能保证新题通过模型门槛或甲方验收。
