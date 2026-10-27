手动分支后两项质检是否执行先按optional-model-checks.md的本题实际选择：required沿下述检查流程，skipped去掉两项调用但仍须题目检查及三模型门槛。交付标明跳过，不能写成三项通过。

# 认可考点不通过后的修复顺序

自动化分支沿用本文的专业修复顺序；版本补取与授权范围以[automation.md](automation.md)“版本补取”为准：正式修订题面/Insight/考点后先统一重评，门槛仍不满足时GPT/Claude各有一次补取机会，已有规则授权不逐轮询问。下文需要本次具体询问的人工替换分支适用于手动流程或自动化额度以外的另行替换。质检渠道、修复轮预算及网页证据按[平台操作流程](platform-automation.md)，不伪造 API failure ID，不直接覆盖原文。

已有平台配方完整网页考点不通过证据时，在改输入或替换回复前用 `lab web-failure-register <检查目录>` 登记专用网页失败观察；它核对原冻结输入、三份原文、本次派发及结果哈希，不生成 API 回执。随后按本文复核该观察；自动化额度内使用 --retry-evaluation 准备入口，额度外另行替换才取得本次具体授权并使用 --failure，均复用 model-replace-prepare/import 的归档路径。缺失或不匹配的证据先核实，不手工补造；其他网页阶段的能力边界见[失败经验](../../../docs/FAILURE_LEARNING.md)。自动化获准采集的新回复可用 piweb-import 的 --replacement-id 接续该入口，普通导入仍不会覆盖。

手动并行检查返回后读取本文件；自动化考点不通过立即按本文修复，达成性尚未发送，无需等待它。先核对实际反馈；不认同的意见继续走platform-checks.md的证据异议。登录、网络、服务错误和结果未知沿原进程处理，不当成题目失败。

返修前必须重读[研究报告](insight-rubric-study.md)的三组修复、反馈张力及局限，并按[检查单](insight-rubric-checklist.md)核对。先区分真正目标遗漏、机制/结论问题、可判性问题和普通表达建议，不把服务故障或无法质检记作内容病因；不因质检标签给所有题追加同一条文。

## 先记原因，再判断能否保持prompt修复

1. 运行failure-context；API内容不通过/模型门槛失败已有自动观察，网页考点先按上文登记。用failure-show <ID>读取原观察，failure-review-template <ID> <新复核JSON>生成助手填写文件。按[经验闭环](../../../docs/FAILURE_LEARNING.md#做题中的经验闭环)写verdict、实际reviewer、具体cause、可执行prevention、applicability与准确evidence_quotes，再failure-review <文件>。未确定原因用unresolved；错误意见用disputed。助手完成复核，不额外向用户索取批准；返修时把相关认可经验用于当前考点自查，避免修完一个缺口又漏掉同类问题。
2. 对题面给定事实与独立专业来源重新核对：Insight是否缺少决定因素、点是否混合多个要求/有隐藏条件/超出题面、备注是否错判原文。先说明要修什么以及为什么。把“专业标准合理吗”与“现有回复满足吗”分开判断；不能为保住某模型命中而删必要条件、降要求或补写回复。
3. 能合理修复时保持prompt逐字不变，按报告的方法修真正缺项、独立判定或等价边界，不删除必要机制、不把可选建议全升为硬要求，再修改Insight、独立考点与必要说明，保存新候选和新冻结版本。Insight变化先重新题目检查；仅补改考点且题面/Insight未变，可复用有效题目检查。按design.md重新设计复核，再freeze。旧冻结、评估、反馈、原文与交付保持；需要编辑旧默认草稿/复核文件时先留快照。
4. 同一prompt的原回复已按prompt哈希保存，可直接读取，无需重取或重新model-import，更不能改原件的采集时间。先生成并完成新版本Seed评估，使用新文件名；Seed未全部达成后，再为全部三模型生成当前evaluation-template，按同一新标准填写met、reason与原文quotes。全部模型统一重评，不能只改GPT/Claude备注或复制旧真假值而不复核。lab check读取three_model_gate；true才按输入依赖补检查，qa-run models可复用仍有效的一项，只发缺失/已变化项。达成性备注单独变化只使实际依赖该备注的检查失效。

## 仅修标准仍不可行：先询问重新提供回复

5. 如果合理修复后仍不满足三模型门槛，明确指出哪个模型缺哪些决定性点，以及为何继续修改Insight/考点不合理；保留失败观察。询问用户是否重新提供GPT-5.6 sol、Claude Opus 4.6中的一个或两个完整官方网页回复。可以给“换Claude / 换GPT / 换两者 / 改新题”等适合当前情况的选项。当前启用这个功能不等于用户已同意某次具体替换；使用request_user_input_async并等待实际答复，等待期间可整理证据，不能把超时当同意。Seed若已全部达成，说明换GPT/Claude不能改变Seed结果，属于替换路线不可行，再考虑新prompt。
6. 获得明确同意后，助手运行下列命令，为获准的每个模型创建新填写入口。failure为本题已认可的考点失败ID；reason说明仅修Insight/考点不足和缺口；authorization-note记录本次用户实际授权语句及对应轮次。不可假造授权，也不在公开仓库留私人原文。

```bash
bin/lab model-replace-prepare claude --failure <ID> --authorization-note '<本次用户明确授权>' --reason '<修复评估和缺口>' --seed-evaluation <当前Seed评估JSON>
```

给出工具返回的prompt_file和input_file可点击链接；重开侧栏时status的pending_replacements会继续给出同一填写入口。用户发送与原prompt完全相同的文字到对应官方网页新会话，按项目要求采用中高推理模式；只填完整MD，截图自行提交。不往prompt追加任何要求，不索取API配置。

7. 用户保存后model-replace-import <gpt或claude> <replacement_id> --seed-evaluation <当前Seed评估>。工具校验同题面/型号/先行Seed，归档旧回复并保存新原文；旧评估和质检会因回复哈希变化失效，保留作历史。旧Seed与未替换的模型不动。重新生成三模型评估，统一核对，门槛true才补平台检查；新回复可能仍不达成，不承诺替换成功。不要重复使用同一授权创建多个候选、挑选有利回复而隐藏其他尝试。
8. 用户拒绝、无法提供、替换路线无助于门槛，或获准替换仍不达成时，解释当前证据，再修改prompt并从题目检查和Seed开始。继续替换须用户另行明确要求，不自动无限重抽。新prompt不能复用旧回复。

该分支处理认可的后期考点质检失败。初次Seed全部达成/GPT与Claude都未达成，仍先记失败原因、保留负结果并换新prompt，不发后两项质检。仅达成性备注误判而标准正确时，按原文纠正判断/备注并重检对应依赖，不为了采用这个分支修改标准。
