# 商科参考索引与机制卡（工作流优化草稿）

核验日期：2026-10-14（首批，Asia/Shanghai）；2026-10-25（第二批扩充）。本文件只供尚未部署的工作流草稿使用。

本资料集包含 32 个已实际打开的公开一手资料条目、7 个可选子方向和 31 张独立写出的机制卡（首批 20 来源 + 18 卡，第二批 2026-10-25 扩充 12 来源 + 13 卡，全部 7 个子方向每向至少 4 卡）。它是参考索引与出题机制卡，既不是已有题库，也不是商科专家验收结果；不包含真实企业原始经营数据。场景种子均为根据机制构造的教学构思，不能冒充用户经历、事实案例或已合格题目。

核验使用机构网站正文或课件/PDF 文本；Microsoft 论文另打开了链接全文。MIT 课件有抽取噪声，只使用可读段落，不从缺失的图表细节推出结论。SBA 原市场研究链接已重定向到汇总页，记录了最终链接。没有引用收费案例正文。第二批扩充时与首批做了机制查重：同一机制不重复建卡（牛鞭效应、相关成本等保留首批卡），新增卡覆盖首批未涉及的决定性机制；MIT 15.760A 与部分 OCW 资源正文在 PDF，登记页面确认的主题范围并在边界中注明。

## 建议的启动菜单

选择“商科”后，一次展示下表供选择；可以只选一个子方向，也可以用普通话描述想尝试的场景。不得根据任务 ID 的 bus 前缀预先代替用户确认。

| ID | 子方向 | 适合怎样的问题 |
| --- | --- | --- |
| `business_daily` | 日常小微经营与创业 | 副业、小店、自由职业、社团收费服务；先验需求与现金计划，不需要从上市公司战略起步。 |
| `business_marketing` | 营销、消费者与定价 | 客群差异、购买行为、套餐、促销、渠道、定价；重点解释行为和收益而非堆营销名词。 |
| `business_operations` | 运营与供应链 | 排队、产能、排班、补货、交付、供应商、库存；可从校园打印店等生活场景进入。 |
| `business_accounting` | 管理会计与单位经济 | 接单、停业务、外包、盈亏平衡、贡献毛益、回款；数据口径必须一致。 |
| `business_organization` | 组织、管理与激励 | 团队分工、绩效规则、协作、奖金、能力与权限；先诊断约束，再建议管理动作。 |
| `business_analytics` | 商业分析与因果实验 | 业务指标、抽样、A/B 测试、随机化单位、干扰、护栏；避免把相关性说成因果性。 |
| `business_strategy` | 战略与商业模式 | 目标顾客、定位、竞争优势、价值创造与获利、能力取舍；要求可用事实支持，而非泛泛列 SWOT。 |

## 已核验来源

访问状态指本次阅读情况，不保证未来持续可用。教材内容可以支持稳定概念和模型前提；书中的历史品牌案例、统计和价格不视为当前事实。下表的“支持”与“边界”是研究者的归纳，不是从教材复制的文本。

| ID | 确切标题与机构 | 本次访问状态 | 支持机制及适用边界 | 可构造的场景 |
| --- | --- | --- | --- | --- |
| S01 | [5.1 Market Segmentation and Consumer Markets](https://openstax.org/books/principles-marketing/pages/5-1-market-segmentation-and-consumer-markets)；OpenStax / Rice University | `html_text_read`，无需登录 | 按实际需求、使用行为和收益诉求区分客群；人口标签本身不足以解释需求差异。 边界：教材框架不提供本地客群规模或转化率；不能把群体标签当成个体偏好。 | 同一小店的通勤客与周末客是否该提供不同套餐。 |
| S02 | [12.3 The Five-Step Procedure for Establishing Pricing Policy](https://openstax.org/books/principles-marketing/pages/12-3-the-five-step-procedure-for-establishing-pricing-policy)；OpenStax / Rice University | `html_text_read`，无需登录 | 定价需要同时考虑目标、需求反应、成本和竞争环境。 边界：需求反应必须有场景证据；成本加成不是最优价格的证明。 | 服务商涨价后收入增加，但是否值得保留新价格。 |
| S03 | [6.3 Steps in a Successful Marketing Research Plan](https://openstax.org/books/principles-marketing/pages/6-3-steps-in-a-successful-marketing-research-plan)；OpenStax / Rice University | `html_text_read`，无需登录 | 先明确决策问题、目标人群和抽样，再选择一手或二手资料。 边界：便利样本的意见不能自动推广到全部顾客；旧资料可能与当前决策不匹配。 | 准备开服务工作室，如何用有限预算验证需求。 |
| S04 | [17.5 The Supply Chain and Its Functions](https://openstax.org/books/principles-marketing/pages/17-5-the-supply-chain-and-its-functions)；OpenStax / Rice University | `html_text_read`，无需登录 | 采购、生产、物流和信息安排需要共同兑现面向顾客的价值承诺。 边界：不能仅凭供应商单价推断总成本、稳定性或质量；具体交付条件需另查。 | 承诺次日到货的小商家是否应换便宜但不稳定的供应商。 |
| S05 | [2.2 Identify and Apply Basic Cost Behavior Patterns](https://openstax.org/books/principles-managerial-accounting/pages/2-2-identify-and-apply-basic-cost-behavior-patterns)；OpenStax / Rice University | `html_text_read`，无需登录 | 固定成本、变动成本和阶梯成本的行为取决于相关业务量区间。 边界：固定不等于永久不变；超出产能区间不能沿用旧单位成本。 | 接大订单需加班或另租设备时如何重算成本。 |
| S06 | [3.2 Calculate a Break-Even Point in Units and Dollars](https://openstax.org/books/principles-managerial-accounting/pages/3-2-calculate-a-break-even-point-in-units-and-dollars)；OpenStax / Rice University | `html_text_read`，无需登录 | 在给定价格、单位变动成本和固定成本下，以贡献毛益分析盈亏平衡。 边界：模型要求相关区间、成本近似线性；多产品需说明销售组合，不能证明需求足以达到盈亏平衡。 | 促销单量增加，考虑折扣、佣金与新增工时后是否真的多赚。 |
| S07 | [10.1 Identify Relevant Information for Decision-Making](https://openstax.org/books/principles-managerial-accounting/pages/10-1-identify-relevant-information-for-decision-making)；OpenStax / Rice University | `html_text_read`，无需登录 | 比较备选方案会改变的未来收入与成本，并区分沉没成本、不可避免成本与机会成本。 边界：短期财务比较不能取代质量、声誉和长期能力判断；不能把所有固定成本都当作无关。 | 一条账面亏损的业务线应继续、自制改外包还是关闭。 |
| S08 | [7.3 Prepare Financial Budgets](https://openstax.org/books/principles-managerial-accounting/pages/7-3-prepare-financial-budgets)；OpenStax / Rice University | `html_text_read`，无需登录 | 按现金收付款时间编排预算，识别账面盈利期间仍可能出现的现金缺口。 边界：预测依赖账期、回款率和支付安排；利润表不能替代现金预算。 | 订单增长且利润为正，但预付采购和延迟回款造成工资支付压力。 |
| S09 | [14.3 Process Theories of Motivation](https://openstax.org/books/principles-management/pages/14-3-process-theories-of-motivation)；OpenStax / Rice University | `html_text_read`，无需登录 | 努力能否改善绩效、绩效能否换来奖励、奖励是否被重视，是不同的激励链条。 边界：这是分析框架而非预测每个员工行为的定律；公平感和工作条件也需调查。 | 涨奖金后产出仍无变化，究竟是能力、流程瓶颈还是奖励规则问题。 |
| S10 | [9.4 Strategic Objectives and Levels of Strategy](https://openstax.org/books/principles-management/pages/9-4-strategic-objectives-and-levels-of-strategy)；OpenStax / Rice University | `html_text_read`，无需登录 | 目标需落到相应层级的行动；单业务经营策略应与采购、服务、运营安排一致。 边界：框架不是具体扩张方案的收益证明；不能直接把多业务组合工具套给单店。 | 一家服务工作室要增长，改套餐、开分店还是购并别的业务。 |
| S11 | [8.6 Competition, Strategy, and Competitive Advantage](https://openstax.org/books/principles-management/pages/8-6-competition-strategy-and-competitive-advantage)；OpenStax / Rice University | `html_text_read`，无需登录 | 成本领先、差异化和聚焦需要相应资源与活动安排。 边界：贴上策略名称不证明竞争优势；低价格不等于具有低成本。 | 小品牌计划同时主打最低价与高强度定制服务，资源如何取舍。 |
| S12 | [8.4 A Firm's Micro Environment: Porter's Five Forces](https://openstax.org/books/principles-management/pages/8-4-a-firms-micro-environment-porters-five-forces)；OpenStax / Rice University | `html_text_read`，无需登录 | 行业内竞争、进入者、替代品、买方与供应商力量影响获利空间。 边界：行业边界和实际证据必须明确；五力分析不直接给出单个企业的成功概率。 | 表面竞争者很少的细分服务为何仍难留住利润。 |
| S13 | [Class 3: Capacity Lecture](https://ocw.mit.edu/courses/15-760b-introduction-to-operations-management-spring-2004/16dde953a29f89a4d2018361900ce886_lec3_capacity.pdf)；MIT OpenCourseWare / Jérémie Gallien | `pdf_text_read_22_pages`，无需登录 | 先画流程并辨认容量瓶颈；随机波动下等待时间与利用率呈非线性关系。 边界：Little 定律需平衡且统计口径一致；平均率不足以推出精确尾部等待时间。 | 接待台明明每天有空闲，忙时顾客却排很久，是否应加人。 |
| S14 | [Analysis of Inventory Models with Limited Demand Information](https://ocw.mit.edu/courses/esd-273j-logistics-and-supply-chain-management-fall-2009/7c024f2f9223e821089500803d96f580_MITESD_273JF09_lec07.pdf)；MIT OpenCourseWare / David Simchi-Levi | `pdf_text_read_22_pages_with_extraction_noise`，无需登录 | 预测更新、订货策略和交付提前期可放大上游订单波动。 边界：课件中的模型依赖需求分布与订货规则；不是所有缺货都由牛鞭效应造成。 | 零售销量较平稳，供应商却反复收到大起大落的补货订单。 |
| S15 | [Session 5: Reward Systems & Incentives](https://ocw.mit.edu/courses/15-322-leading-organizations-ii-fall-2003/e81c2fabfea1ab50bb1db94060a6d6b1_ses5_lincoln_electric.pdf)；MIT OpenCourseWare / John Van Maanen | `pdf_text_read_6_pages_with_extraction_noise`，无需登录 | 外部奖励可能带来短期服从，也可能影响内在动机，需要结合组织环境判断。 边界：课件引用的历史调查和收费案例不能当作已读取案例正文或当前行业事实；奖励并非必然有害。 | 给客服按处理件数发奖后，协作和复杂问题处理意愿发生变化。 |
| S16 | [Three Key Checklists and Remedies for Trustworthy Analysis of Online Controlled Experiments at Scale](https://www.microsoft.com/en-us/research/publication/three-key-checklists-and-remedies-for-trustworthy-analysis-of-online-controlled-experiments-at-scale/)；Microsoft Research / Fabijan et al. / ICSE-SEIP 2019 | `landing_and_linked_pdf_text_read_10_pages`，无需登录 | 先验证数据与分流质量，再解读效果；同时检查成功、功能、护栏和数据质量指标。 边界：不能凭单个显著指标宣布上线；SRM 排查、实验时长和效果持续性需结合具体系统。 | 新页面转化率显著提升，但两组人数比例异常，是否可以宣布获胜。 |
| S17 | [Patterns of Trustworthy Experimentation: Pre-Experiment Stage](https://www.microsoft.com/en-us/research/articles/patterns-of-trustworthy-experimentation-pre-experiment-stage/)；Microsoft Research / Experimentation Platform | `html_text_read`，无需登录 | 随机化单位要适配稳定身份、跨用户影响和组织部署约束，并考虑样本量。 边界：按用户随机并非对所有功能有效；存在干扰时改分组也需要重新定义估计对象与分析。 | 团队共享折扣或协作功能的实验能否按个人随机分组。 |
| S18 | [5.3.3.2. Randomized block designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)；NIST/SEMATECH e-Handbook of Statistical Methods | `html_text_read`，无需登录 | 把可控制的重要干扰因素组织为区组，在区组内比较处理并保留随机化。 边界：区组不能修复所有偏差；不能把星期一投 A、星期二投 B 自动称为有效随机对照。 | 不同门店与时段客流差异很大，如何比较两种服务流程。 |
| S19 | [Plan your business — Market research and competitive analysis](https://www.sba.gov/counseling/plan-your-business/)；U.S. Small Business Administration | `html_text_read_redirect_confirmed`，无需登录 | 用需求、市场范围、位置、替代选择与竞争情况组织小企业的初步市场验证。 边界：美国机构方法可参考；本地需求、统计、税务、许可和平台规则必须另查，不照搬。 | 在小区开预约服务，先查哪些事实才能决定是否签长租。 |
| S20 | [How to Estimate Starting Costs](https://www.sba.gov/blog/2017/2017-01/how-estimate-starting-costs/)；U.S. Small Business Administration / Tim Berry | `html_text_read`，无需登录 | 启动资金包括开业前费用、需要配置的非现金资产和早期经营缺口所需现金。 边界：2017 方法文不是当前开店报价或法规；不同支出分类不能导致重复计算。 | 准备做上门服务，已有设备但账上现金少，应如何估计启动资金。 |
| S21 | [2.4 Marketing Plan Progress Using Metrics](https://openstax.org/books/principles-marketing/pages/2-4-marketing-plan-progress-using-metrics)；OpenStax / Rice University | `html_text_read`，无需登录 | 客户终身价值应超过获客成本，简化公式（每客户年利润×平均保留年数−获客成本）；CLV 是前瞻估计，判断盈利还要计入销货与服务成本。 边界：教学示例非行业实证；不含本地化数据、留存率动态建模或法律合规讨论。 | 两家获客渠道的优劣因估计窗口与成本归集口径不同而反转。 |
| S22 | [15.4 Price Discrimination（Introduction to Economic Analysis, McAfee & Lewis）](https://socialsci.libretexts.org/Bookshelves/Economics/Applied_Economics/Introduction_to_Economic_Analysis_(LibreTexts)/15%3A_Monopoly/15.04%3A_Price_Discrimination)；Saylor / LibreTexts | `html_text_read`，无需登录 | 差别定价两个前提：区分不同需求的客群、阻止转售套利；直接/间接歧视框架，数量折扣、优惠券、版本划分是自选择手段。 边界：无福利效应推导、无一级歧视图形推导、无数值例题；许可 CC BY-NC-SA 3.0。 | 软件是否值得推出学生版，取决于自选择是否成立、套利风险有多大。 |
| S23 | [Lecture Notes（Lec 8 Process Flow Models；Lec 10 Queueing Systems）15.760A](https://ocw.mit.edu/courses/15-760a-operations-management-spring-2002/pages/lecture-notes/)；MIT OpenCourseWare | `html_text_read`，无需登录 | 讲义目录确认流程流模型与排队系统两讲；Little 定律（平均数量=到达率×停留时间）刻画产能、在制与等待的约束。 边界：目录页仅列条目，正文为 PDF；无服务行业基准数据。 | 门店在排队长度、平均等待与放弃率之间做产能决策。 |
| S24 | [2.5 Agency Issues – Shareholders and Corporate Boards（Principles of Finance）](https://biz.libretexts.org/Bookshelves/Finance/Principles_of_Finance_(OpenStax)/02%3A_Corporate_Structure_and_Governance/2.05%3A_Agency_Issues-_Shareholders_and_Corporate_Boards)；OpenStax via LibreTexts | `html_text_read`，无需登录 | 代理冲突分三类（股东-管理层、投资者-债权人、股东-其他利益相关者）；对齐手段含激励、股权与长期薪酬、惩罚与收购威胁。 边界：概念与案例层，不含合约设计模型；董事会运作在 2.4 节。 | 店长奖金只挂钩短期营业额后出现宰客与损耗上升。 |
| S25 | [9.2 Work Group Structure](https://openstax.org/books/organizational-behavior/pages/9-2-work-group-structure)；OpenStax / Rice University | `html_text_read`，无需登录 | 社会性惰化的三个发生条件（任务意义低、产出不可辨识、预期他人偷懒）；大群体更普遍；管理杠杆指向贡献可辨识度。 边界：页面明确群体规模与生产率无确定关系；不含量化模型。 | 个人计件改为团队奖金池后产量下降的归因。 |
| S26 | [A Tutorial on Thompson Sampling (arXiv:1707.02038)](https://arxiv.org/abs/1707.02038)；Russo, Van Roy, Kazerouni, Osband, Wen / arXiv | `html_text_read`，无需登录 | 在线决策在利用已知与获取新信息之间平衡；Bernoulli bandit 按后验采样分配流量；讨论算法何时有效。 边界：方法论综述，无业务案例；非平稳环境变体未全覆盖。 | 固定等长 A/B 与按后验提前分配流量的机会成本权衡。 |
| S27 | [Simpson's paradox in psychological science: a practical guide](https://pmc.ncbi.nlm.nih.gov/articles/PMC3740239)；Kievit et al. / Frontiers in Psychology（PMC 公开版） | `html_text_read`，无需登录 | 聚合后方向整体反转的根源是子群体构成比例（基率）不同；跨层推断需要背景知识，观察数据无法区分混淆与中介。 边界：无直接商业案例；不存在统一规则预防所有情形。 | 两个渠道在每个客群内 A 优、聚合后 B 优的转化率决策。 |
| S28 | [9.04 Inventory Models for Certain Demand – EOQ](https://biz.libretexts.org/Courses/Northeast_Wisconsin_Technical_College/Introduction_to_Operations_Management_(NWTC)/09%3A_Inventory_Management/9.04%3A_Inventory_Models_for_Certain_Demand_-_Economic_Order_Quantity_(EOQ))；LibreTexts（NWTC 运营管理） | `html_text_read`，无需登录 | EOQ 由总成本（仅订货+持有）最小化导出；假设外部订货、需求恒定、提前期恒定、批量固定。 边界：确定需求模型，无随机需求、安全库存、数量折扣与缺货成本；页面示例解答未完整展示。 | 季节性商品按 EOQ 补货却旺季缺货、淡季损耗。 |
| S29 | [19.1 What Is Working Capital?](https://openstax.org/books/principles-finance/pages/19-1-what-is-working-capital)；OpenStax / Rice University | `html_text_read`，无需登录 | 现金转换周期=存货天数+应收天数−应付天数，三段各有两步算法与数值示例（57.2 天拆解）；压缩周期有经营与信用代价。 边界：流动比率是时点值；行业基准需订阅数据库；季节性差异明显。 | 账面盈利但现金紧张的小店，用现金周期定位占款环节。 |
| S30 | [17.3 Hotelling Differentiation（Introduction to Economic Analysis, McAfee & Lewis）](https://socialsci.libretexts.org/Bookshelves/Economics/Applied_Economics/Introduction_to_Economic_Analysis_(LibreTexts)/17%3A_Imperfect_Competition/17.03%3A_Hotelling_Differentiation)；Saylor / LibreTexts | `html_text_read`，无需登录 | 线段定位模型：价格固定时厂商聚集中点（最小差异化）；定位把竞争维度从价格转为位置。 边界：不含价格内生的均衡（17.4 圆形模型）与最大差异化结论；有图示无公式；习题无解答。 | 两家奶茶店扎堆商圈与分散设点的均衡条件。 |
| S31 | [VRIO Analysis（Strategic Management）](https://open.oregonstate.education/strategicmanagement/chapter/4-vrio-analysis)；John Morris / Oregon State University Open Textbook | `html_text_read`，无需登录 | VRIO 四判据与绩效对照表（平价/暂时/持续优势）；难模仿性源于历史条件、因果模糊与社会复杂性；组织利用是必要条件。 边界：被模仿时长的判断依赖主观估计；无行业数据库；例证为公开报道的教学案例。 | 评价秘方、熟客社群与排班系统哪个构成持续优势。 |
| S32 | [15.7 Peak-load Pricing（Introduction to Economic Analysis, McAfee & Lewis）](https://socialsci.libretexts.org/Bookshelves/Economics/Applied_Economics/Introduction_to_Economic_Analysis_(LibreTexts)/15%3A_Monopoly/15.07%3A_Peak-load_Pricing)；Saylor / LibreTexts | `html_text_read`，无需登录 | 共享产能成本 β 由两时段消耗：要么全部计入高峰期价格，要么用价格拉平两期需求；含拉格朗日一阶条件与 Ramsey 定价形式。 边界：两时段模型，无多时段一般化与数值算例；无图示；不含监管与公平性约束。 | 健身房差别定价与统一价之间选择，各自隐含的产能成本归因。 |

## 可复用机制卡

机制可以反复学习，但不能把同一机制、同一决策和同一表达方式只换人名或数字来批量造题。每次先选择真实且有后果的决策，再决定是否适用某张卡；题目仍需独立查证、自然语言改写与本地相似性检查。以下卡片不含固定 Insight 或考点句式。

### B01 同一类人也可能需要不同服务（`business_marketing`）

机制：有用的细分应连接可观察的需求差异、可接触方式和相应方案，而不是只换人口标签。 依据：[S01](https://openstax.org/books/principles-marketing/pages/5-1-market-segmentation-and-consumer-markets)。

成立条件：已说明顾客行为或需求差异；有能力提供不同方案。

不能推出：不能从年龄或职业直接断言购买偏好；细分方案需要当地验证。

构造场景种子：自习空间的周内短时用户与周末长时用户该如何安排套餐。（未经验证，不是成题。）

### B02 涨价不只看收入（`business_marketing`）

机制：价格变化同时影响数量和贡献毛益；以明确经营目标比较方案。 依据：[S02](https://openstax.org/books/principles-marketing/pages/12-3-the-five-step-procedure-for-establishing-pricing-policy)，[S06](https://openstax.org/books/principles-managerial-accounting/pages/3-2-calculate-a-break-even-point-in-units-and-dollars)。

成立条件：有价格与需求反应的情景数据；成本口径和比较期一致。

不能推出：不能假设需求不变；收入上升不等于利润上升。

构造场景种子：维修服务涨价后单量变少、总收入增加，是否继续执行新价。（未经验证，不是成题。）

### B03 问卷支持不等于会付费（`business_marketing`）

机制：先辨认决定成败的需求假设，再选择匹配样本和验证方法；表达兴趣与真实购买行为是不同证据。 依据：[S03](https://openstax.org/books/principles-marketing/pages/6-3-steps-in-a-successful-marketing-research-plan)。

成立条件：已定义目标人群和实际决策；说明预算、时间与样本来源。

不能推出：不能以朋友点赞比例外推市场需求；有购买意愿也不能无条件推出规模化盈利。

构造场景种子：社团同学都说喜欢预约打印服务，应怎样在租设备前进一步验证。（未经验证，不是成题。）

### B04 新增资源要投到约束处（`business_operations`）

机制：总产出受流程瓶颈和步骤间依赖限制，给非瓶颈增加资源可能不改善最终交付。 依据：[S13](https://ocw.mit.edu/courses/15-760b-introduction-to-operations-management-spring-2004/16dde953a29f89a4d2018361900ce886_lec3_capacity.pdf)。

成立条件：流程步骤和处理时间可辨认；返工和并行关系已说明。

不能推出：不能只用平均工时找到任何情形下的瓶颈；需求不足时扩产不一定增加销售。

构造场景种子：咖啡店收银很快、出杯慢，老板想再加一个收银员。（未经验证，不是成题。）

### B05 有空闲仍会排队（`business_operations`）

机制：相同平均需求下，波动与接近满负荷可放大等待；应区分总产能不足与时段拥堵。 依据：[S13](https://ocw.mit.edu/courses/15-760b-introduction-to-operations-management-spring-2004/16dde953a29f89a4d2018361900ce886_lec3_capacity.pdf)。

成立条件：已说明到达或服务存在随机波动；容量、队列边界和观测时段明确。

不能推出：不能从平均利用率直接算精确等待分位数；排队改进也要考虑成本与服务体验。

构造场景种子：预约工作室平均只用掉八成工时，但用户经常等很久。（未经验证，不是成题。）

### B06 销量与订货不是同一条信号（`business_operations`）

机制：上游订单包含下游预测修订和库存调整；提前期等因素可使订单波动大于终端需求。 依据：[S14](https://ocw.mit.edu/courses/esd-273j-logistics-and-supply-chain-management-fall-2009/7c024f2f9223e821089500803d96f580_MITESD_273JF09_lec07.pdf)。

成立条件：存在多阶段补货；可获得销量、库存、在途或订货信息。

不能推出：不能见到波动就认定牛鞭效应；共享信息未必消除所有供需风险。

构造场景种子：批发商看到订单暴增要求扩产，但门店实际销售变化很小。（未经验证，不是成题。）

### B07 关业务看能省掉什么（`business_accounting`）

机制：方案比较应纳入会变化的未来收支与机会成本；已发生投入与仍要承担的费用分开处理。 依据：[S07](https://openstax.org/books/principles-managerial-accounting/pages/10-1-identify-relevant-information-for-decision-making)。

成立条件：决策时限和可选方案明确；能区分可避免和不可避免成本。

不能推出：不能用分摊后的亏损直接判断应关闭；长期能力和顾客影响需要另评估。

构造场景种子：工作室某项服务分摊房租后亏损，停掉它是否真的改善整体收益。（未经验证，不是成题。）

### B08 跨过产能门槛就要重算（`business_accounting`）

机制：成本在一定业务量内近似固定或线性，越过加人、加班或设备门槛后应分段比较。 依据：[S05](https://openstax.org/books/principles-managerial-accounting/pages/2-2-identify-and-apply-basic-cost-behavior-patterns)。

成立条件：产能门槛与新增支出已明确；订单或需求规模可比。

不能推出：不能把旧单位平均成本无限外推；固定成本在长期也可改变。

构造场景种子：烘焙店有一张批量订单，接单后必须多租一天设备。（未经验证，不是成题。）

### B09 有利润也可能付不出钱（`business_accounting`）

机制：应按回款与付款时点估计现金余额和缺口，而不是以收入确认或账面利润替代现金。 依据：[S08](https://openstax.org/books/principles-managerial-accounting/pages/7-3-prepare-financial-budgets)。

成立条件：已给出账期、期初现金与支出日程；比较窗口覆盖主要收付款。

不能推出：不能只算全年利润判断下月是否缺钱；融资成本和坏账假设需明确。

构造场景种子：企业客户下单增加但六十天后付款，材料商要求提前付款。（未经验证，不是成题。）

### B10 激励链条断在哪里（`business_organization`）

机制：把努力能否改善绩效、绩效能否带来奖励、奖励是否受重视分开诊断。 依据：[S09](https://openstax.org/books/principles-management/pages/14-3-process-theories-of-motivation)。

成立条件：有任务条件和规则证据；不预先把动机差当作事实。

不能推出：不能保证加薪或公开排名一定有效；个体反应与公平感需另验证。

构造场景种子：客服奖金翻倍但积压未减少，系统权限和审批是否限制了处理。（未经验证，不是成题。）

### B11 奖励要看短期与长期行为（`business_organization`）

机制：外部奖励可以改变具体行为，但可能伴随内在动机、协作和持久承诺的代价。 依据：[S15](https://ocw.mit.edu/courses/15-322-leading-organizations-ii-fall-2003/e81c2fabfea1ab50bb1db94060a6d6b1_ses5_lincoln_electric.pdf)。

成立条件：说明奖励针对何种行为；能够观察相关副作用。

不能推出：不能推出所有奖金都有害；不能直接照搬历史企业案例的效果。

构造场景种子：维修团队按完工单数发奖后，大家回避困难工单和帮助新人。（未经验证，不是成题。）

### B12 随机化单位要跟影响范围一致（`business_analytics`）

机制：若处理影响同事或共同资源，按个人分组可能出现组间干扰；应重新设计分组和估计对象。 依据：[S17](https://www.microsoft.com/en-us/research/articles/patterns-of-trustworthy-experimentation-pre-experiment-stage/)。

成立条件：说明用户之间或资源之间的联系；知道处理实际部署范围。

不能推出：聚类随机不自动消除所有干扰；需重新考虑功效和推断单位。

构造场景种子：门店导购共享库存和折扣权限，还能给每位顾客单独随机测试吗。（未经验证，不是成题。）

### B13 先查实验能不能信（`business_analytics`）

机制：分流人数、数据缺失、埋点和护栏先过关，再判断业务指标；同时评估效果是否持续。 依据：[S16](https://www.microsoft.com/en-us/research/publication/three-key-checklists-and-remedies-for-trustworthy-analysis-of-online-controlled-experiments-at-scale/)。

成立条件：已定义分流比例、指标与基本检查；数据覆盖比较对象。

不能推出：单个 p 值不能推出可上线；SRM 本身不告诉你偏差方向。

构造场景种子：新版页面转化率显著更高，但计划等分的两组人数明显失衡。（未经验证，不是成题。）

### B14 用区组减少可解释的波动（`business_analytics`）

机制：让主要干扰条件相近的对象组成区组，在区组内比较处理并实施随机化。 依据：[S18](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)。

成立条件：干扰因素可记录或控制；每区组含可比较处理。

不能推出：时间先后比较不是天然随机试验；区组不能弥补数据造假或系统性漏记。

构造场景种子：三家门店客流不同，怎样比较新旧排班而不是比较门店生意好坏。（未经验证，不是成题。）

### B15 定位必须有相应活动支撑（`business_strategy`）

机制：经营策略要和目标顾客、资源配置、采购与服务安排一致，识别不可同时满足的承诺。 依据：[S10](https://openstax.org/books/principles-management/pages/9-4-strategic-objectives-and-levels-of-strategy)，[S11](https://openstax.org/books/principles-management/pages/8-6-competition-strategy-and-competitive-advantage)。

成立条件：有明确客群与有限资源；已给出服务成本或能力约束。

不能推出：策略标签不能证明优势；不能只靠一种通用框架算出最优商业模式。

构造场景种子：一家两人工作室想同时承诺最低价、无限修改和当天交付。（未经验证，不是成题。）

### B16 启动资金还要覆盖早期缺口（`business_daily`）

机制：开办费用、资产配置和初期净现金流缺口应按时间整合，避免漏项和重复计算。 依据：[S20](https://www.sba.gov/blog/2017/2017-01/how-estimate-starting-costs/)，[S08](https://openstax.org/books/principles-managerial-accounting/pages/7-3-prepare-financial-budgets)。

成立条件：说明已有资产与新增支出；至少有一个保守收入情景。

不能推出：不是当前地区报价或法规意见；不能用够开业推断够生存。

构造场景种子：朋友已有相机，计划接商业摄影，预算是否还应留给押金与回款等待期。（未经验证，不是成题。）

### B17 竞争者少也可能赚不到钱（`business_strategy`）

机制：先明确顾客的替代选择、买方与供应商议价能力及进入约束，再判断价值能否被企业保留。 依据：[S12](https://openstax.org/books/principles-management/pages/8-4-a-firms-micro-environment-porters-five-forces)。

成立条件：行业或市场边界明确；已给出实际替代与交易关系。

不能推出：五力不是成功概率模型；不能把不在同一行业的所有企业都当成直接竞争者。

构造场景种子：本地几乎没有同类工作室，但顾客可以自己做、延期做或找线上服务。（未经验证，不是成题。）

### B18 先验证最可能推翻计划的事实（`business_daily`）

机制：围绕客户、实际需求、替代选择与触达范围收集证据，再做不可逆投入。 依据：[S19](https://www.sba.gov/counseling/plan-your-business/)，[S03](https://openstax.org/books/principles-marketing/pages/6-3-steps-in-a-successful-marketing-research-plan)。

成立条件：存在具体经营计划；说明当前不知道的事实与验证成本。

不能推出：全国行业增长不能代替本地需求；不能把美国办事指南当成本地合规流程。

构造场景种子：准备在居民区做周末课程，签一年租约前应该先验证什么。（未经验证，不是成题。）

### B19 客户终身价值与获客成本的口径决定结论（`business_marketing`）

机制：判断一个客群值不值得获取，取决于终身价值与获客成本的比较，而两者都依赖估计窗口与成本归集口径；口径不同，同一组数据的结论可以反转。 依据：[S21](https://openstax.org/books/principles-marketing/pages/2-4-marketing-plan-progress-using-metrics)。

成立条件：估计窗口、留存假设与贴现处理已明确；获客成本只归集为获取该客群实际发生的支出。

不能推出：教材公式是简化估计，不含留存率变化与再投入的动态；不提供任何行业基准值或本地数据。

构造场景种子：门店在两个获客渠道间分配预算，因是否计入服务成本、窗口长短的口径不同，结论相反。（未经验证，不是成题。）

### B20 差别定价成立靠分离与套利阻止（`business_marketing`）

机制：差别定价要成立，须能区分不同需求的客群并阻止转售套利；间接歧视（数量折扣、优惠券、版本划分）靠客群自选择实现分离，而不是直接识别身份。 依据：[S22](https://socialsci.libretexts.org/Bookshelves/Economics/Applied_Economics/Introduction_to_Economic_Analysis_(LibreTexts)/15%3A_Monopoly/15.04%3A_Price_Discrimination)。

成立条件：厂商有一定市场势力；不同客群的需求弹性存在差异。

不能推出：不含福利效应推导与数值例题；不涉及价格法规与平台规则的合规边界。

构造场景种子：一款软件是否值得推出功能受限的学生版，取决于高低需求客群的自选择是否成立、套利风险有多大。（未经验证，不是成题。）

### B21 峰谷定价隐含产能成本的归因口径（`business_operations`）

机制：共享产能在高峰与平峰间分配成本：要么把产能成本全部计入高峰价格，要么用相对价格把各时段需求拉平；归因口径不同，价格结构与高峰压力的结论不同。 依据：[S32](https://socialsci.libretexts.org/Bookshelves/Economics/Applied_Economics/Introduction_to_Economic_Analysis_(LibreTexts)/15%3A_Monopoly/15.07%3A_Peak-load_Pricing)。

成立条件：各时段需求可区分且可分时定价；产能跨时段共享且成本随峰值变化。

不能推出：两时段模型，无多时段一般化与数值算例；不含监管与公平性约束讨论。

构造场景种子：健身房在高峰时段差别定价与全时段统一价之间选择，需要判断两种定价各自隐含的产能成本归因及对高峰拥挤的影响。（未经验证，不是成题。）

### B22 排队系统的吞吐-在制-等待约束（`business_operations`）

机制：稳定状态下系统内平均数量等于到达率乘平均停留时间；产能、在制与等待互相约束，同时改善三者通常需要改变系统结构而不是调参数。 依据：[S23](https://ocw.mit.edu/courses/15-760a-operations-management-spring-2002/pages/lecture-notes/)。

成立条件：系统进入稳定状态；度量口径（系统边界、平均方式）前后一致。

不能推出：目录页仅列讲义条目，正文为 PDF；不含具体服务行业基准数据。

构造场景种子：门店在排队长度、平均等待与放弃率之间做产能决策，需要指出哪个口径的变化能同时改善两个指标、哪个必然牺牲另一个。（未经验证，不是成题。）

### B23 销售组合漂移让盈亏平衡点失真（`business_accounting`）

机制：多产品盈亏平衡依赖销售组合不变假设；组合漂移改变加权贡献毛益，按旧组合算出的盈亏平衡点与目标利润不再适用，税后目标还须先换算为税前口径。 依据：[S06](https://openstax.org/books/principles-managerial-accounting/pages/3-2-calculate-a-break-even-point-in-units-and-dollars)。

成立条件：产品间贡献毛益差异明显；组合比例可观察或可假设。

不能推出：教材页不含多产品盈亏平衡的完整计算与敏感性分析；图表数据不完整。

构造场景种子：门店促销把销量推向低毛利产品后，总销量达标却仍未过盈亏平衡点，需要用组合口径重算。（未经验证，不是成题。）

### B24 代理问题的对齐手段各有成本（`business_organization`）

机制：委托人无法完全观察代理人行为与努力时产生代理冲突；股权与长期薪酬、监督、收购威胁都是对齐手段，但每种手段只对齐特定维度并引入新的行为诱导。 依据：[S24](https://biz.libretexts.org/Bookshelves/Finance/Principles_of_Finance_(OpenStax)/02%3A_Corporate_Structure_and_Governance/2.05%3A_Agency_Issues-_Shareholders_and_Corporate_Boards)。

成立条件：存在可部分观察的业绩信号；激励与监督本身有成本。

不能推出：教材页为概念与公开案例列举，不含合约设计模型；不涉及法律与监管条文细节。

构造场景种子：给店长的奖金只挂钩短期营业额后，出现向上虚报、损耗上升与老客流失，需要归因激励口径漏掉了哪些维度。（未经验证，不是成题。）

### B25 社会性惰化取决于贡献可辨识度（`business_organization`）

机制：群体成员在任务意义低、个人产出不可辨识或预期他人偷懒时降低努力；群体规模放大这三个条件，改变贡献的可辨识度是针对性的管理杠杆。 依据：[S25](https://openstax.org/books/organizational-behavior/pages/9-2-work-group-structure)。

成立条件：个人贡献可辨识性是可操作的关键变量；任务与激励结构给定。

不能推出：教材页明确群体规模与生产率无确定关系，不提供量化模型；工作设计层面的手段细节在其他章节。

构造场景种子：把个人计件改成团队奖金池后产量下降，需要归因到可辨识度变化与预期他人偷懒，而不是笼统的士气说法。（未经验证，不是成题。）

### B26 实验的探索-利用权衡（`business_analytics`）

机制：在线决策要在利用已知最优方案与继续获取新信息之间分配流量；把继续实验的机会成本显式纳入，才能判断实验该跑多久、何时开始倾向更优方案。 依据：[S26](https://arxiv.org/abs/1707.02038)。

成立条件：结果反馈及时且流量可分配；收益分布在实验期内近似平稳。

不能推出：教程为方法论综述，无业务案例与行业数据；非平稳环境的变体未全覆盖。

构造场景种子：促销实验跑满固定两周与按后验提前向更优方案倾斜，两种方案的错选损失与错过更优方案损失不同，需要结构化表达该权衡。（未经验证，不是成题。）

### B27 聚合口径的方向反转（`business_analytics`）

机制：每个子群体内的关系方向在聚合后可能整体反转，根源是子群体构成比例不同；该按聚合还是分层决策，取决于分层变量与决策对象的关系，且需要数据之外的背景判断。 依据：[S27](https://pmc.ncbi.nlm.nih.gov/articles/PMC3740239)。

成立条件：存在同时影响分组与结果的构成变量；各层数据可获得。

不能推出：论文为方法指南，无直接商业案例；观察数据无法区分混淆与中介，需背景知识。

构造场景种子：两个渠道在每个客群内 A 转化率更高，聚合后 B 更高，需要判断按哪个口径决策并指出还缺什么信息。（未经验证，不是成题。）

### B28 EOQ 的确定需求边界（`business_daily`）

机制：经济订货量在需求恒定、提前期恒定、只计订货与持有成本的假设下由总成本最小化决定；把确定模型外推到波动或季节性环境时，结论与实际损耗、缺货表现背离。 依据：[S28](https://biz.libretexts.org/Courses/Northeast_Wisconsin_Technical_College/Introduction_to_Operations_Management_(NWTC)/09%3A_Inventory_Management/9.04%3A_Inventory_Models_for_Certain_Demand_-_Economic_Order_Quantity_(EOQ))。

成立条件：需求与提前期确定；无数量折扣、无缺货情形。

不能推出：教材页示例解答未完整展示；不含随机需求、安全库存与折扣情形。

构造场景种子：季节性商品按 EOQ 安排补货节律，实际却出现旺季缺货与淡季损耗并存，需要逐条指出哪条假设被违反。（未经验证，不是成题。）

### B29 现金转换周期定位占款环节（`business_daily`）

机制：现金周期等于存货天数加应收天数减应付天数；每个分母与平均口径的选择改变结论，压缩周期有经营与信用关系的代价，账面盈利与现金充裕是两回事。 依据：[S29](https://openstax.org/books/principles-finance/pages/19-1-what-is-working-capital)。

成立条件：财务数据可获得且平均口径一致；已意识到行业与季节性差异。

不能推出：应付压缩的信用关系与信用评级代价不能无限化；行业比较基准需要订阅数据库。

构造场景种子：扩张中的小店账面盈利但现金紧张，需要用现金周期口径定位占款环节，并说明缩短每个环节的代价。（未经验证，不是成题。）

### B30 定位竞争与最小差异化（`business_strategy`）

机制：在位置模型中，价格外生时厂商聚集于中点是均衡（最小差异化）；定位选择把竞争维度从价格转为位置，价格是否内生化会改变均衡方向。 依据：[S30](https://socialsci.libretexts.org/Bookshelves/Economics/Applied_Economics/Introduction_to_Economic_Analysis_(LibreTexts)/17%3A_Imperfect_Competition/17.03%3A_Hotelling_Differentiation)。

成立条件：消费者选择最近的厂商；价格外生或给定。

不能推出：不含价格内生的差异化均衡与最大差异化结论；教材页有图示无正式公式，习题无解答。

构造场景种子：两家奶茶店在扎堆商圈与分散设点之间选择，需要说明在什么条件下扎堆是均衡、什么条件下分散成立。（未经验证，不是成题。）

### B31 VRIO 判据区分暂时与持续优势（`business_strategy`）

机制：资源产生持续优势须同时有价值、稀缺、难模仿且被组织利用；有价值但普遍只是平价，难模仿性通常来自历史条件、因果模糊与社会复杂性，缺乏组织利用则优势无法兑现。 依据：[S31](https://open.oregonstate.education/strategicmanagement/chapter/4-vrio-analysis)。

成立条件：资源与能力可识别；竞争者获取它们存在成本或时间劣势。

不能推出：被模仿所需时长的判断依赖主观估计；不提供行业数据库与本地验证手段。

构造场景种子：评价一家店的秘方、熟客社群与排班系统哪个构成持续优势，需要逐项过四判据并指出组织利用缺口。（未经验证，不是成题。）

## 第二批机制卡的难题化切入点（2026-10-25）

以下切入点把新卡与"难度与区分度定位"（design.md 第 5 步）连接：每张新卡的决定性考点应落在口径定义、方法论选择或多约束交互层，避免做成题面数字封闭计算题。

- B19：决定性考点放在口径定义（哪些成本进分子/分母、窗口期选择）与前瞻估计的不确定性表达；代数计算本身不是区分点。
- B20：判断某定价方案属于哪类歧视、其自选择分离机制是否会被套利破坏；把"是否公平"的直觉与"是否可分离"的机制区分开。
- B21：让模型识别定价结构隐含的产能成本归因口径，并推断该归因对高峰拥挤的反作用；不是比较两个价格的高低。
- B22：考点放在口径一致性与稳定状态前提的识别；Little 定律计算简单，错在系统边界或平均方式混用。
- B23：区分"总销量达标"与"加权贡献毛益过盈亏点"两个口径；组合漂移是最有效的干扰源。
- B24：决定性考点在"哪个维度的目标没对齐、激励口径会诱导什么行为"的归因；不是背诵代理定义。
- B25：发生条件逐项核对（可辨识度/任务意义/预期他人行为）与混淆因素排除；笼统归因"士气"是典型错答。
- B26：机会成本口径（错选损失 vs 错过更优方案的损失）与实验有效性的结构化权衡；正解是比较，不是报出"正确算法"名。
- B27："该聚合还是该分层"的口径判断与缺失信息识别；数值计算只是载体。
- B28：假设逐条核对与"确定模型外推到波动环境"的失效识别；不是代入 EOQ 公式。
- B29：口径选择（期初期末平均 vs 期末值）与"缩短周期的代价"权衡；不是算出一个天数。
- B30："价格是否内生化"对均衡方向的改变；"分散更好"的直觉与"聚集中点"均衡的反差是区分点。
- B31：VRIO 逐项判定与"暂时 vs 持续"优势的区分；把"有价值"直接当"有优势"是典型错答。

## 稳定知识与当次核验分工

教材级稳定内容：成本分类、相关区间、贡献毛益、差异成本、现金收付时间、基本流程容量、抽样/区组/随机化逻辑。引用时仍需写成立条件，不把简化模型当现实全貌。组织激励和战略工具属于解释框架，证据强度弱于会计恒等关系，不能据此写成对所有企业都必然成立的考点。

题目当次必须另查：企业或平台现行收费和规则、当地用工/税务/行业许可、真实价格和账期、最新市场规模、客群行为、行业结构、公司当前经营状况、具体算法/软件产品版本。引用日期、地区、单位、样本与口径要一并记录。没有可靠数据时，明确题内是条件化的构造数据，并验证数值自洽；不能伪装成实测。

出题检查：Insight 必须改变这道题的诊断或行动；决定性考点必须能从题内事实与可靠机制推出。不存在足够事实时，允许合理条件分支或收集关键证据，而不是强迫唯一经营结论。仅要求模型说出框架名，不能替代可判定的解决能力。

资料使用方式：保存链接、访问记录和自行写出的简短概念卡，不把教材正文、原案例、图片或大段例题复制进可公开发布的数据包。OpenStax 本次页面列有非商业/再使用及 AI 摄入限制；本文件不建立其全文缓存或训练集。若未来需要商业分发教材衍生内容，应按原站授权范围另外处理。

## 机器可用 JSON 草稿

本节仅一个完整 JSON 代码块，可整体解析。`verification` 是实际读取状态；`scenario_origin` 明确所有场景种子均为构造；不存在对试标合格性的保证。

机器可读的唯一数据源为 [rules/business-reference.json](../rules/business-reference.json)。本研究说明不再复制完整JSON；修改或补充条目时在该数据文件中更新核验日期、来源和边界。
