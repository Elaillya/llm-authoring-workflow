# 生活娱乐：资料与出题方法

新增大类与计算机科学、商科并列。五条主干是兴趣爱好、活动与出行、日常生活、个人生活规划、学生学习与课余生活；完整层级与ID见[分类目录](LIFESTYLE_CATALOG.md)。支持兴趣爱好 → 文艺 → 音乐 → 摇滚，也支持运动 → 球类 → 乒乓球等不同深度。大范围确认后由助手继续细化，不强迫用户了解分类树。

## 这份资料能支持什么

截至2026-10-15，共50个实际打开阅读的一手来源、73张独立机制卡、73个明确标注的构造情境。来源包含博物馆与大学教学资料、官方运动/桌游规则、政府与公共机构指南、大学推广服务、原始研究及机构研究摘要；后两者分别标注，不互相冒充。每张卡有决定性因素、机制、适用条件、边界、误区、独立判定目标及情境种子。

它是帮助设计和核验题目的参考集，未进行真实五模型测评或甲方验收。目录有61个叶节点，43个直接关联资料卡；未覆盖方向及本地时效资料必须补查。不能把卡片改几个名词或数字就当作新合格题，也不能把所有生活问题都写成“先检查再行动”。本地记忆仍比较题面、Insight机制和评分要求。

机器可读的唯一公共资料源是[rules/lifestyle-reference.json](../rules/lifestyle-reference.json)。下方只展示简短索引；完整情境和证据边界通过命令分页读取。失败抓取、仅搜索摘要、未读论文与旧规则不计入已读来源。

## 助手怎样用

```bash
bin/lab choose-domain 生活娱乐
bin/lab domain-tree --domain 生活娱乐
bin/lab choose-subdirection life_hobbies
# 若用户明确指定摇滚，也可直接记录：
bin/lab choose-subdirection life_music_rock
# 若用户希望停在音乐范围，则明确确认：
bin/lab choose-subdirection life_arts_music --confirm
bin/lab choose-type How-to类
bin/lab lifestyle-references --subdirection life_arts_music --limit 8 --offset 0
```

`begin`只显示当前层选项；已有明确范围直接记录。`lifestyle-references`返回完整简短机制索引、当前页卡片和关联来源、下一页offset、所选范围的直接/继承覆盖和缺口，以及公共/本题补充数量；不能只看第一页就声称已覆盖全部。命令由助手执行，用户用日常语言选择即可。

1. 先读本地全库记忆，选择在目标、约束、机制、证据与评分要求上有实质区别的方向。
2. 按匹配节点读卡，再打开原始来源。检查原结论适用条件和本题事实；天气、开放时间、票价、规章版本等当次核实。国外制度和单一个案不跨范围推断。
3. 在drafts/sources.md记录原链接、实际读取内容、题设哪些是构造事实、地区与时间边界、不确定处。候选绑定lifestyle_mechanisms与lifestyle_references，必须包含所选卡全部关联来源；ID绑定只检查可追踪性，不能证明内容真的适用。
4. 没有合适卡或资料时，由助手先研究并在本题drafts/lifestyle-supplement.json新增sources、mechanisms两个列表，沿用公共JSON条目结构；可从[空白结构](../templates/lifestyle-supplement.json)开始。每条使用新ID，例如LH-LOCAL-S01/LH-LOCAL-M01，来源必须实际打开、写日期/范围/边界，卡绑定目录中最具体的适当节点；不能覆盖公共ID或把合成示例冒充真实来源。本题扩展不进入GitHub，命令会同时检索它。
5. prompt自然简短，只交代影响判断的事实与真实目标，不堆出题术语。Insight用灵活纯文本突出改变结论的因素；核心考点短而独立，一条判断一件事。设计复核绑定公共资料、私有补充资料与来源笔记的哈希；改资料后重做本地复核。更新本功能不重写既有题目与旧判断。
6. 继续原流程：题面/Insight难度标签检查 → 考点和冻结 → Seed → 合条件后GPT/Claude → 三模型门槛通过才并行两项质检 → Arena两模型 → 五模型排序与六份MD。

生活娱乐在项目原领域清单中的标签为“生活娱乐”；工具会为缺少它的旧私有映射补默认值，不改service.json或Cookie，不覆盖显式自定义映射。该新增领域的线上质检尚未在本轮实际调用。

## 什么题值得出

- 音乐：不是“你最喜欢哪种摇滚”，而是给出排练记录、角色与共同目标，定位为何各自能演奏却合奏不稳。审美选择可多解，所需机制和约束要可判定。
- 园艺：两盆绿植同样萎蔫，根区状态却相反；决定因素是区分证据，不能只凭相同表象统一补水。不能据此替植物作病害诊断。
- 学生复习：计划已经排满时，要从保持目标、可用连续时段、独立回忆记录判断如何调整，而不是列通用学习技巧。
- 社团活动：场地“有空”是否足够，取决于给定审批与资源约束；外国大学政策仅为机制参考，实际学校规则需当次查验。
- 桌游：题面提供版本、路线与人数规则，判断已占路网中的可行方案；难点是资源和约束的共同作用，不是背一条冷门规则。

这些只是构造方向，均未保证通过Seed/GPT/Claude门槛。个人生活方式、艺术偏好与人生价值不设唯一正确答案；要先给目标与可核实限制。日常学习安排属于生活规划，专业教育理论另选适当领域。临床诊疗、心理治疗、法律与投资判断不作为生活类默认情境；食品、清洁与户外规划依官方边界，不出危险操作题。

## 来源索引

- LH-A-S01：[Practice Journal: Practice Tips & Techniques](https://pulse.berklee.edu/content/practicepalooza/journal/PracticeTips.pdf)；Berklee PULSE；official_teaching_material。读取范围：PDF 第 1—2 页：练习目标、难点定位、练习日志与长短练习安排；未逐项检验所有技术练习。
- LH-A-S02：[Centre for Performance Science researchers identify links between memorisation and virtuosity](https://www.rcm.ac.uk/about/news/all/2018-12-20cpsmemorisationandvirtuosity.aspx)；Royal College of Music；first_party_research_summary。读取范围：第一方研究说明正文：一名大提琴演奏者两年练习及十次公演、表演线索与记忆恢复；未读取链接中的完整研究论文。
- LH-A-S03：[Ensemble Courses](https://college.berklee.edu/ensemble/ensemble-courses)；Berklee College of Music；official_course_catalog。读取范围：ENCF-100、ENCF-121、ENCF-122、摇滚合奏基础课程说明：角色、曲式、倾听、节奏与动态。
- LH-A-S04：[Hearing Protection](https://musiciansunion.org.uk/health-safety-wellbeing/health-and-safety/key-health-and-safety-issues/hearing-health/hearing-protection)；Musicians’ Union；professional_association_guidance。读取范围：Hearing Protection 正文，尤其是先减少噪声暴露、再考虑个人听力防护的控制层级。
- LH-A-S05：[Understanding Formal Analysis: Principles of Design](https://www.getty.edu/education/teachers/building_lessons/formal_analysis2.html)；J. Paul Getty Museum；museum_education。读取范围：Balance、Emphasis、Movement 三节及其说明文字，未独立测量图片中的注意分布。
- LH-A-S06：[Light, ultraviolet and infrared](https://www.canada.ca/en/conservation-institute/services/agents-deterioration/light.html)；Canadian Conservation Institute；government_conservation_guidance。读取范围：阅读光照剂量定义、可见光与 UV 的区分、保存和观看的权衡及材料敏感性讨论；不把表中寿命估计用于个人藏品定年。
- LH-A-S07：[Close Reading a Text and Avoiding Pitfalls](https://owl.purdue.edu/owl/subject_specific_writing/writing_in_literature/writing_about_fiction/index.html)；Purdue University OWL；university_writing_guidance。读取范围：Close Reading 与 Avoiding Pitfalls 正文，尤其是解释需与全文和具体文本证据相核验。
- LH-A-S08：[Image Stabilization](https://www.nikon.com/company/technology/technology_fields/software_and_systems/image_stabilization/)；Nikon Corporation；manufacturer_technical_explanation。读取范围：Technology Overview：通过传感器检测相机运动并移动镜片/传感器补偿；没有将产品的标称档数泛化。
- LH-A-S09：[What Is Aperture in Photography?](https://www.usa.canon.com/learning/training-articles/training-articles-list/what-is-aperture)；Canon U.S.A.；manufacturer_educational_material。读取范围：文章正文：光圈与入光量、景深、Av 模式自动选择快门；未采用商品广告和优惠信息。
- LH-A-S10：[Measuring Physical Activity Intensity](https://www.cdc.gov/physicalactivity/basics/measuring/index.html)；U.S. Centers for Disease Control and Prevention；government_public_health_guidance。读取范围：Moderate Intensity 与 Vigorous Intensity 两节：谈话测试和相对强度。
- LH-A-S11：[Get running with Couch to 5K](https://www.nhs.uk/better-health/get-active/get-running-with-couch-to-5k/)；NHS Better Health；government_public_health_programme。读取范围：计划概述、每周三次且间隔休息日、跑走交替、九周或更长及启动时的健康边界。
- LH-A-S12：[ITTF Statutes 2026: Laws of Table Tennis](https://db.ittf.com/sites/default/files/public/2026-02/2026_Statutes_v1_consolidated_clean.pdf)；International Table Tennis Federation；official_sport_rules。读取范围：PDF 第 41—45 印刷页附近：2.6 发球、2.8 击球顺序、2.13 发接发顺序、2.14 顺序错误处理；未审阅全书其他规则。
- LH-A-S13：[Law 11: Offside](https://www.theifab.com/laws/latest/offside/)；The IFAB；official_sport_rules。读取范围：11.1—11.3 与关于 deliberate play、deflection、save 的说明和相邻 FAQ；未独立裁判任何真实比赛视频。
- LH-A-S14：[Bicycle Safety](https://www.nhtsa.gov/road-safety/bicycle-safety)；National Highway Traffic Safety Administration；government_road_safety_guidance。读取范围：Prepare Before Heading Out 与 Drive Defensively：选路线、设备可用性、日夜可见性。
- LH-A-S15：[Trip Planning Guide](https://www.nps.gov/subjects/healthandsafety/trip-planning-guide.htm)；U.S. National Park Service；government_outdoor_safety_guidance。读取范围：出行前、抵达、途中三个阶段：活动能力匹配、备用活动、装备、联系计划、改变行程与返程。
- LH-A-S16：[Lightning Safety and Outdoor Sports Activities](https://www.weather.gov/safety/lightning-sports)；NOAA National Weather Service；government_weather_safety_guidance。读取范围：停止活动、避险场所、恢复条件、专人监测和授权职责等正文。
- LH-A-S17：[Put crowd controls in place](https://www.hse.gov.uk/event-safety/crowd-management-controls.htm)；UK Health and Safety Executive；government_event_safety_guidance。读取范围：进入离开、分时到场、排队和楼梯等正文；未采用站外交通工程或密度上限计算。
- LH-A-S18：[Eating Outdoors: Handling Food Safely](https://www.fda.gov/media/79871/download)；U.S. Food and Drug Administration；government_food_safety_guidance。读取范围：PDF 第 1—4 页的运送、冷藏、分开生熟食与器具、时间温度控制；不提供治疗建议。
- LH-A-S19：[Split Train Tickets](https://www.nationalrail.co.uk/tickets-railcards-and-offers/buying-a-ticket/split-train-tickets/)；National Rail；official_transport_ticket_guidance。读取范围：一般 split ticket 的停站条件、每段车次限制、可不下车、座位可能需更换及 Season/area ticket 例外 FAQ。
- LH-A-S20：[Fertilizing and watering container plants](https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/fertilizing-and-watering-container-plants)；University of Minnesota Extension；university_extension_guidance。读取范围：Quick facts、Fertilize regularly、Maintain even moisture、Watch out for soggy soil，网页标注 Reviewed in 2026。
- LH-A-S21：[Gauge Swatch 101: How to Make and Measure Your Swatch](https://www.lionbrand.com/community/blog/gauge-swatch-101-how-to-make-and-measure-your-swatch/)；Lion Brand Yarn；manufacturer_craft_tutorial。读取范围：Step 1—5：按项目针法织样片、分别量横纵、按将来方式洗护和整形、复测；未依赖评论区。
- LH-A-S22：[Adult Activity: An Overview](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html)；U.S. Centers for Disease Control and Prevention；government_public_health_guidance。读取范围：成人活动建议及三个例子：有氧活动与肌肉强化分别列出；不读取为个体训练处方。
- LH-B-S01：[Preventing Wasted Food At Home](https://www.epa.gov/recycle/preventing-wasted-food-home)；US Environmental Protection Agency；government_guidance。读取范围：正文 Planning and Shopping Tips、Storage Tips、Cooking and Preparation Tips；未把页面美国总体浪费统计用于构造数据。
- LH-B-S02：[Are You Storing Food Safely?](https://www.fda.gov/consumers/consumer-updates/are-you-storing-food-safely)；US Food and Drug Administration；government_safety_guidance。读取范围：Storage Basics、Refrigeration Tips、Freezer Facts；未使用停电段落中较复杂的例外。
- LH-B-S03：[Clothes Captioning: Complying with the Care Labeling Rule](https://www.ftc.gov/business-guidance/resources/clothes-captioning-complying-care-labeling-rule)；US Federal Trade Commission；government_label_guidance。读取范围：Instructions and Warnings、Reasonable Basis、Washing Instructions五要素及相关FAQ。
- LH-B-S04：[When and How to Clean and Disinfect Your Home](https://www.cdc.gov/hygiene/about/when-and-how-to-clean-and-disinfect-your-home.html)；US Centers for Disease Control and Prevention；government_safety_guidance。读取范围：Definitions、Cleaning、Disinfecting，特别是标签接触时间及使用禁忌。
- LH-B-S05：[How to Preserve Family Archives: Storing Family Papers and Photographs](https://www.archives.gov/preservation/family-archives/storing)；US National Archives and Records Administration；public_institution_preservation_guidance。读取范围：存放环境、避水虫鼠、容器尺寸与材料、相册装裱、应避免的材料各段。
- LH-B-S06：[Personal Archiving: Digital Photographs](https://www.digitalpreservation.gov/personalarchiving/photos.html)；Library of Congress；public_institution_preservation_guidance。读取范围：Archiving Tips全部四组建议；未观看视频及下载另附PDF。
- LH-B-S07：[Creating a cash flow budget tool](https://files.consumerfinance.gov/f/documents/cfpb_your-money-your-goals_cash_flow_budget_tool_2018-11_ADA.pdf)；Consumer Financial Protection Bureau；government_educational_tool。读取范围：PDF四页：逐周余额步骤、跨周结转表与用途说明。
- LH-B-S08：[Bill calendar tool](https://files.consumerfinance.gov/f/documents/cfpb_your-money-your-goals_bill_calendar_tool_2018-11_ADA.pdf)；Consumer Financial Protection Bureau；government_educational_tool。读取范围：PDF三页：GETTING STARTED、填表步骤与说明。
- LH-B-S09：[Planning for life events and large purchases tool](https://files.consumerfinance.gov/f/documents/cfpb_your-money-your-goals_events-purchases_tool_2018-11.pdf)；Consumer Financial Protection Bureau；government_educational_tool。读取范围：PDF三页：时间、费用、相关费用与筹资分解步骤及工具表。
- LH-B-S10：[Revising goals handout](https://files.consumerfinance.gov/f/documents/cfpb_your-money-your-goals_revising_goals_handout_2018-11.pdf)；Consumer Financial Protection Bureau；government_educational_tool。读取范围：PDF两页中条件变化、储蓄进度不足、优先级与目标价值变化段落。
- LH-B-S11：[Does Monitoring Goal Progress Promote Goal Attainment? A Meta-Analysis of the Experimental Evidence](https://eprints.whiterose.ac.uk/id/eprint/91437/8/3_PDFsam_Does%20monitoring%20goal.pdf)；Harkin et al.; White Rose Research Online, University of Sheffield；primary_research_meta_analysis。读取范围：作者接受稿PDF摘要（PDF第3页）、监测定义（PDF第6页）、指标维度（PDF第11至13页）、局限（PDF第41至43页）；未逐一核验138项原研究。
- LH-B-S12：[Studying 101: Study Smarter Not Harder](https://learningcenter.unc.edu/tips-and-tools/studying-101-study-smarter-not-harder/)；University of North Carolina at Chapel Hill Learning Center；university_learning_guidance。读取范围：Reading is not studying、技术课练习、解释步骤、学习环境、分散练习与分心段落。
- LH-B-S13：[What To Do With Practice Exams](https://lsc.cornell.edu/how-to-study/studying-for-and-taking-exams/what-to-do-with-practice-exams/)；Cornell University Learning Strategies Center；university_learning_guidance。读取范围：正文Taking practice exams及Testing effect；未观看嵌入视频。
- LH-B-S14：[What To Do When You Get Your Graded Test or Essay Back](https://lsc.cornell.edu/how-to-study/studying-for-and-taking-exams/what-to-do-when-you-get-your-graded-test-or-essay-back/)；Cornell University Learning Strategies Center；university_learning_guidance。读取范围：正文按读题失误、遗忘、不熟悉迁移及未明白原因分类的建议。
- LH-B-S15：[Managing Time](https://lsc.cornell.edu/managing-time/)；Cornell University Learning Strategies Center；university_learning_guidance。读取范围：学期日历、周日历、固定承诺、各课时间需求与平衡活动段落；未进入Canvas模块。
- LH-B-S16：[What are best practices for designing group projects?](https://www.cmu.edu/teaching/designteach/design/instructionalstrategies/groupprojects/design.html)；Carnegie Mellon University Eberly Center；university_teaching_guidance。读取范围：Create interdependence、分工与中期截止、整合协调、individual accountability。
- LH-B-S17：[Spacing effects in learning: A temporal ridgeline of optimal retention](https://escholarship.org/content/qt0kp5q19x/qt0kp5q19x.pdf)；Cepeda et al.; UC San Diego eScholarship；primary_research_experiment。读取范围：PDF第2页摘要、第4至5页方法、第5至6页结果与讨论；材料为事实回忆，未复算统计。
- LH-B-S18：[Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf)；Roediger and Karpicke; Purdue Cognition and Learning Lab；primary_research_experiment。读取范围：PDF第1至5页：摘要、两项大学生短文实验、即刻与延迟测试结果；未逐条追溯参考文献。
- LH-B-S19：[Management Standards: Demands](https://www.hse.gov.uk/stress/standards/demands.htm)；UK Health and Safety Executive；government_workplace_guidance。读取范围：正文工作负荷、工作模式、约定工时内可达要求与反映问题机制。
- LH-B-S20：[How to change your address](https://www.usa.gov/change-address)；US General Services Administration / USAGov；government_process_guidance。读取范围：Postal Service地址更新与其他联邦州服务分别更新段落；未打开链接中的具体办理流程。
- LH-B-S21：[Start Strong!](https://lsc.cornell.edu/consult-with/start-strong/)；Cornell University Learning Strategies Center；university_learning_guidance。读取范围：公开正文中的学期准备、syllabus、资源定位、新生术语和office hours；未访问仅校内Canvas课程。
- LH-B-S22：[How to Use Office Hours](https://lsc.cornell.edu/help-with-classes/how-to-use-office-hours/)；Cornell University Learning Strategies Center；university_learning_guidance。读取范围：公开正文的准备、职责、带尝试记录与具体卡点、可替代求助资源。
- LH-B-S23：[Booking Spaces & Equipment](https://studentsunionucl.org/how-to/clubs-and-societies/booking-spaces-equipment)；Students Union UCL；first_party_venue_policy。读取范围：场地容量表、预约仍为临时状态、无障碍、设备申请与外部场地截止提醒。
- LH-B-S24：[Organising Activities & Events](https://studentsunionucl.org/how-to/clubs-and-societies/organising-activities-events)；Students Union UCL；first_party_event_policy。读取范围：Planning中按活动类型的时间表、Budget、核心与额外风险评估适用范围。
- LH-C-S01：[Watering Indoor Plants](https://extension.umd.edu/resource/watering-indoor-plants)；University of Maryland Extension；university_extension_guidance。读取范围：正文浇水判断、土壤湿度、花盆重量、萎蔫与排水段落；不使用文末静置水去矿物质的说法。
- LH-C-S02：[Growing Vegetables in Containers and Salad Tables](https://www.extension.umd.edu/resource/growing-vegetables-containers-and-salad-tables)；University of Maryland Extension；university_extension_guidance。读取范围：容器排水、底部碎石、容器材质、介质与根系空间；了解自浇水容器结构，未采用马里兰州播种月历。
- LH-C-S03：[Ticket to Ride — Rules (US, 2015)](https://ncdn0.daysofwonder.com/tickettoride/en/img/tt_rules_2015_en.pdf)；Days of Wonder；official_game_rulebook。读取范围：四页规则正文，重点读目的地票正负分、双线路人数限制、回合动作与终局触发。
- LH-C-S04：[Paper Conservation Lab](https://americanart.si.edu/art/conservation/center/paper)；Smithsonian American Art Museum；museum_conservation_guidance。读取范围：纸质藏品预防性装裱与存放、压敏胶带及劣质衬垫风险；未把专业修复流程转成DIY教程。

## 机制卡索引

| ID | 机制主题 | 所在细类 |
| --- | --- | --- |
| LH-A-M01 | 练习总时长与具体薄弱环节脱节 | 乐器练习 |
| LH-A-M02 | 背谱连锁记忆缺少可恢复地标 | 乐器练习 |
| LH-A-M03 | 乐队个体正确与合奏共同参照不一致 | 摇滚与乐队、合奏与演出准备 |
| LH-A-M04 | 摇滚排练的防护层级 | 摇滚与乐队、合奏与演出准备 |
| LH-A-M05 | 宣传画的焦点冲突与任务目标 | 素描、绘画与构图 |
| LH-A-M06 | 藏画展示的累计光照剂量 | 作品装裱与保存 |
| LH-A-M07 | 文学解读中的局部引文与全文反证 | 阅读、细读与读书交流 |
| LH-A-M08 | 防抖无法消除主体运动 | 手机与相机拍摄 |
| LH-A-M09 | 合照的景深覆盖与大光圈冲突 | 手机与相机拍摄 |
| LH-A-M10 | 半自动曝光模式掩盖了被改变的变量 | 手机与相机拍摄 |
| LH-A-M11 | 同一配速不是同一相对强度 | 日常跑步与目标安排、骑行与日常运动出行 |
| LH-A-M12 | 初学跑步补课不能只按总次数合并 | 新手与重返跑步 |
| LH-A-M13 | 乒乓球双打回合内的击球顺序 | 乒乓球 |
| LH-A-M14 | 乒乓球发接发顺序纠错与已得分分离 | 乒乓球 |
| LH-A-M15 | 乒乓球发球可见性独立于抛球高度 | 乒乓球 |
| LH-A-M16 | 足球越位位置与实际参与分开判断 | 足球及配合 |
| LH-A-M17 | 足球防守者碰球不一定重置越位判断 | 足球及配合 |
| LH-A-M18 | 休闲骑行路线的距离目标与暴露约束 | 骑行与日常运动出行 |
| LH-A-M19 | 自行车夜间可见性不是只穿亮色 | 骑行与日常运动出行 |
| LH-A-M20 | 徒步备用方案必须真正可启用 | 日间徒步与山野活动 |
| LH-A-M21 | 徒步行程变更使原有联系计划失效 | 日间徒步与山野活动、多人户外协调 |
| LH-A-M22 | 户外活动暂停阈值必须包含撤离时间和权限 | 户外及跨场地活动 |
| LH-A-M23 | 排队整齐不能证明出入口仍可用 | 小型活动与社团活动 |
| LH-A-M24 | 活动结束时间相同造成离场峰值 | 小型活动与社团活动 |
| LH-A-M25 | 野餐冷链必须覆盖运输与取用全过程 | 聚餐与家庭招待 |
| LH-A-M26 | 聚餐生熟隔离不能用冷藏替代 | 聚餐与家庭招待 |
| LH-A-M27 | 旅行分票节省必须先满足票种与停站约束 | 行程、换乘与节奏 |
| LH-A-M28 | 阳台园艺的均匀湿润与积水不是一回事 | 阳台与容器种植 |
| LH-A-M29 | 编织成品尺寸取决于洗护后的横纵密度 | 编织与纤维手工 |
| LH-A-M30 | 活动计划中的有氧与肌肉强化是两条目标轴 | 一般力量与体能活动 |
| LH-B-M01 | 采购量取决于真实用餐日历 | 备餐与厨房流程 |
| LH-B-M02 | 大包装便宜取决于可用量 | 备餐与厨房流程、日常预算与资源分配 |
| LH-B-M03 | 冰箱冷不冷需要测量 | 食品保存与剩食安排 |
| LH-B-M04 | 冷藏不会清零此前的室温暴露 | 食品保存与剩食安排、琐事、家务与时间安排 |
| LH-B-M05 | 冷冻储存不能挽救先前的不当保存 | 食品保存与剩食安排 |
| LH-B-M06 | 整件衣物的标签决定洗护边界 | 洗衣、晾晒与衣物照护 |
| LH-B-M07 | 分洗要求是跨衣物约束 | 洗衣、晾晒与衣物照护 |
| LH-B-M08 | 清洁在消毒之前 | 家庭清洁与低风险照护 |
| LH-B-M09 | 消毒看湿接触时间，不看擦了几遍 | 家庭清洁与低风险照护 |
| LH-B-M10 | 常规清洁与额外消毒的适用范围 | 家庭清洁与低风险照护 |
| LH-B-M11 | 相册好看不等于适合保存原件 | 照片、纪念物与个人档案 |
| LH-B-M12 | 收纳位置不能只看空余体积 | 照片、纪念物与个人档案、搬家与居住过渡 |
| LH-B-M13 | 重要照片副本要脱离同一故障范围 | 文件、照片与备份 |
| LH-B-M14 | 能存住不等于找得到 | 文件、照片与备份、照片、纪念物与个人档案 |
| LH-B-M15 | 月结余不能替代逐期余额 | 日常预算与资源分配、搬家与居住过渡 |
| LH-B-M16 | 到期日与发起操作日不一定相同 | 琐事、家务与时间安排、日常预算与资源分配 |
| LH-B-M17 | 生活转变的成本包含附带费用 | 搬家与居住过渡、日常预算与资源分配 |
| LH-B-M18 | 调整目标应改变约束中的量 | 阶段目标与进度复盘、日常预算与资源分配 |
| LH-B-M19 | 阶段目标要有与目标对应的证据 | 阶段目标与进度复盘 |
| LH-B-M20 | 先判断一周装不装得下 | 个人时间与精力安排、课余活动与社团选择 |
| LH-B-M21 | 碎片时间要与任务连续需求匹配 | 课程任务与日程、个人时间与精力安排 |
| LH-B-M22 | 工作生活冲突有时来自工作量本身 | 边界、责任与可控安排 |
| LH-B-M23 | 搬家的一次地址更新不等于全部同步 | 搬家与居住过渡、琐事、家务与时间安排 |
| LH-B-M24 | 熟悉感与延迟回忆不是同一表现 | 练习、复盘与知识保持、期中期末复习 |
| LH-B-M25 | 复习间隔应围绕保持目标而定 | 练习、复盘与知识保持、期中期末复习 |
| LH-B-M26 | 会跟着例题不等于会选择方法 | 练习、复盘与知识保持、课程任务与日程 |
| LH-B-M27 | 模拟考试需要匹配资源和时间 | 期中期末复习 |
| LH-B-M28 | 复盘先区分失分原因 | 期中期末复习、练习、复盘与知识保持 |
| LH-B-M29 | 任务拆开不等于成果能集成 | 同伴学习与小组合作、课程任务与日程 |
| LH-B-M30 | 小组交付质量与个人理解分别验证 | 同伴学习与小组合作、课程任务与日程 |
| LH-B-M31 | 协作里程碑要服务后续依赖 | 同伴学习与小组合作、学生活动执行与协调 |
| LH-B-M32 | 新阶段的旧经验需经课程规则核验 | 入学、毕业与阶段过渡、课程任务与日程 |
| LH-B-M33 | 求助要暴露具体卡点 | 练习、复盘与知识保持、课程任务与日程 |
| LH-B-M34 | 有场地不等于活动已获准 | 学生活动执行与协调、小型活动与社团活动 |
| LH-B-M35 | 场地选择先过硬约束 | 学生活动执行与协调、小型活动与社团活动 |
| LH-B-M36 | 常规活动批准不覆盖新增范围 | 学生活动执行与协调、小型活动与社团活动 |
| LH-C-M01 | 同样萎蔫不能直接决定加水 | 室内观叶与盆栽 |
| LH-C-M02 | 固定浇水表应随环境和状态校正 | 室内观叶与盆栽 |
| LH-C-M03 | 盆底铺石不能替代排水通路 | 阳台与容器种植 |
| LH-C-M04 | 阳台种植先匹配实际光照和根域 | 阳台与容器种植 |
| LH-C-M05 | 可选任务的收益包含失败扣分 | 桌游规则与组织 |
| LH-C-M06 | 人数改变会改变共享路线可用容量 | 桌游规则与组织 |
| LH-C-M07 | 自制作品的固定方式会影响日后保存 | 作品装裱与保存、纸艺与普通作品保存 |
