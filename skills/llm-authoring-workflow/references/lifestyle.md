# 生活娱乐设计入口

只在选择生活娱乐时读取；现有五模型、质检和交付流程保持。

1. begin显示当前层选项，按用户回答choose-subdirection；内部节点继续询问下一层，或用户明确希望助手在此范围选题时加--confirm。可以直接指定细类，不要求一路回答。最后选择题型。完整目录在工具仓docs/LIFESTYLE_CATALOG.md；横向标签由助手补充。
2. 读memory-context全库机制索引，随后lifestyle-references --subdirection <ID>分页查卡。返回短索引和next_offset，必要时翻页，不只看第一张反复复用。精确运动/地区规则不得借给兄弟主题。
3. 读工具仓docs/LIFESTYLE_REFERENCES.md及卡片原始来源，逐题核实决定因素、适用条件和时效。缺口由助手查一手来源，按同结构写drafts/lifestyle-supplement.json，记录实际读到的内容；不要让用户写事实，不伪造已读或把摘要当完整论文。
4. 候选写lifestyle_mechanisms/lifestyle_references，保存drafts/sources.md。卡片是构造灵感，不是已验收题；个人偏好允许多解，通过给定目标、限制和证据建立可判定因素。自然prompt、灵活Insight与独立考点按writing.md。
5. 难度标签检查、设计差异复核和冻结沿design.md；公共与本题补充资料变化会使设计复核过期。后续Seed优先，三模型门槛满足才并行质检，再Arena五模型排序。不因新增领域重做已有冻结题或改写原回复。
