# CV-Explorer

## Vision & Background

### 学术背景

计算机视觉(CV)在2014-2024十年间经历了从深度学习爆发到大模型范式转移的历史过程

### 学科归属

本项目属于**计算机图形学(Computer Graphics)**中的信息可视化分支。
通过几何拓扑映射、像素缓冲区渲染等图形学手段，将高维文献数据转化为直观的视觉表征。

### 设计目标

构建一个具有“叙事性”的动态探索系统，揭示技术脉络的流向与学术方法中心的更迭。

### 设计逻辑与UI系统(Design Philosophy)

#### 沉浸式门户

- 采用Full-page Snap Scroll(全屏捕捉滚动)技术
- **叙事化引导**

## Members

尚文轩
王乐之
黄奕浩

## views

### ai_panel

**AI Panel 视图设计说明**

- 核心职责：该视图位于 ai_panel.js，负责在用户选择论文、节点或流向后生成上下文化的 AI 解读摘要，向研究者提供十年产出、关键词热点等洞察，并提供可配置的模型/API Key 接入界面，成为全局分析结果的语义补充窗口。
- 独立组件原因：AI 面板需要维护独立的输入配置、状态挂起、缓存恢复与回退逻辑，与其他可视化图层存在不同的生命周期和交互节奏；将其独立封装既方便复用与懒加载，也避免在主视图中引入额外的 AI 状态管理，降低耦合和渲染负担。
- 输入与输出：`renderAiPanel(container, state, dispatcher)` 接收三个参数：① `container` 作为 D3 生成 DOM 的根节点；② `state` 提供全球摘要数据（venues、keywords）、筛选条件以及当前选中项；③ `dispatcher` 负责监听 `paperSelected` 事件。视图输出内容包括：配置按钮与表单、当前选择摘要与标签、Top Venues 卡片、关键词墙，以及经后端 `/api/analyze` 返回的 AI 文案。
- 内部结构与逻辑：布局分为「选择面板」「AI 配置面板」「摘要模块」三部分。组件首先初始化本地存储的模型配置并更新 UI；随后为 selection 区域设置空闲、加载、结果三种状态机，并在合适时发起请求、处理缓存或本地降级。摘要区域聚合全局统计并通过动画与 KaTeX/Markdown 渲染增强可读性。整体逻辑围绕状态管理（config、typing、pending）、数据准备（meta、chips）与异步渲染（fetch、fallback）展开。
- 调用方式：外部视图在创建总体界面时调用 `renderAiPanel`，传入共享 `state` 与事件 `dispatcher`；当其他模块（如概览、语义景观、排行榜）触发 `dispatcher.on('paperSelected')` 时，此组件自动刷新内容。组件卸载时会移除事件监听与计时器，确保与其它视图解耦。

### flow

- AI 流向视图位于 flow.js，核心任务是依据 `state.sankey` 聚合后的“问题域→方法族”关系绘制交互式桑基图，实现多年份流向对比、链路高亮、指标摘要与悬浮提示，帮助读者理解研究问题与技术路径之间的能量分布和年度增减态势。
- 该视图被独立封装，是因为其承担的时间轴播放、筛选控件、桑基布局、Top 流向摘要、工具提示与跨视图事件协同逻辑复杂且与其他视图耦合度低；分离后可单独维护 d3-sankey 渲染、Play/All-Year 状态机、趋势样式等专业交互，同时避免给概览或排行榜视图引入额外的布局与性能负担。
- `renderFlow(container, state, dispatcher)` 接收三类输入：① `container` 作为布局根节点；② `state` 提供 `sankey` 原始链路、`filters.year`、`summary` 等全局数据；③ `dispatcher` 作为事件总线。输出界面包括：筛选与时间轴控制面板、颜色图例、Top 5 流向摘要列表、问题/方法双色标注的桑基主图、动态 Tooltip 以及年度状态栏。
- 内部结构采用“控制面板 + 舞台面板”双区布局。控制面板负责年份滑条及播放按钮、问题/方法选择器、关键字搜索、重置按钮与配色图例，并汇总 Top 链路排名；舞台面板内含 SVG 框架、Sankey 布局、节点/链路高亮、Tooltip、趋势 Pill、Legend 定位及空状态提示。组件内部维护年份状态、播放计时器、当前高亮链路、过滤结果缓存，先过滤/汇总数据，再按舞台尺寸配置 sankey 布局、渲染节点链路，并同步摘要列表与 Tooltip。
- 其他模块在初始化视图时调用 `renderFlow` 并传入共享 `state` 与 `dispatcher`；当用户在此视图点击链路或节点时，它通过 `dispatcher.call('viewUpdate', …)` 与 `dispatcher.call('paperSelectedSync', …)` 将选择信息广播到 AI 面板、概览或排行榜，实现跨视图联动。其他视图若更新年份或选择特定问题/方法，也会发出 `viewUpdate` 事件，`flow` 视图内部的 `externalHandler` 会响应这些外部指令、同步年份与筛选状态，保证多视图协同分析体验。



### landscape

- 语义景观视图位于 landscape.js，其主要任务是将 `state.landscape` 中的论文嵌入点集映射成具有缩放、拖拽、热度轮廓与锚点标注的语义地图，帮助读者从宏观角度观察学科势力版图、热点聚集和代表论文，提供与桑基、排行榜互补的空间洞察。
- 该视图被独立封装，是因为它依赖 Canvas+SVG 双层渲染、密度等值线、缩放状态管理、迷你地图、语义锚点计算与交互提示等专门逻辑，且与其他图层的 DOM 结构、性能需求和交互节奏均不同；拆分为单独组件可以集中维护绘制管线、保留局部状态（缩放矩阵、筛选条件、指针索引），同时通过 `dispatcher` 与全局同步但不互相阻塞。
- `renderLandscape(container, state, dispatcher)` 接收三个参数：① `container` 作为挂载根；② `state` 提供 `landscape` 点集、`filters.year`、全局摘要等上下文；③ `dispatcher` 用于发出/接收跨视图事件。输出界面包含：Canvas 主图、SVG 叠加标签层、年份/会议/锚点/平滑度控制、概览摘要卡、迷你地图、Hover 卡片与 Tooltip 等呈现元素。
- 内部结构采用“舞台（canvas+overlay）+ 控制面板”布局。流程概括为：预处理数据（坐标、年份、关键词归一化）；初始化年份滑条、全周期开关、会议下拉、锚点/平滑滑块、渐变图例、摘要与 Digest 卡片；配置 d3.zoom、ResizeObserver、mini-map；每次 `draw()` 时按当前筛选与缩放态绘制背景网格、密度等值线、点位、语义锚点与重点论文标签，更新摘要/Digest/徽章/迷你视窗；监听鼠标交互以显示 Tooltip、Hover 卡并向 `dispatcher` 广播 `paperSelectedSync`。整体逻辑围绕过滤 → 投影 → 渲染 → 联动四个阶段执行。
- 其他模块在初始化整体仪表板时调用 `renderLandscape` 并传入共享 `state` 与 `dispatcher`。当用户在此视图选择年份或点击论文时，会通过 `dispatcher.call('viewUpdate', …)` 与 `dispatcher.call('paperSelectedSync', …)` 通知桑基、AI 面板等视图；其他视图若广播 `viewUpdate`（如年份切换），`landscape` 的 `externalFilterHandler` 会响应并同步内部年份状态，确保各视图之间的联动一致性。

### leaderboard

- leaderboard.js 的“学术封神榜”视图承担展示顶尖学者与代表论文的双列榜单，配合动画化计数与进度条，突出学术影响力、机构分布与作品热度，在整体项目中为用户提供对作者与经典成果的权威速览，补足桑基流向与语义地图对“谁创造这些成果”维度的洞察。
- 该视图被抽象为独立组件，是因为其需要维护“全球/南开”双模式切换、榜单动画、头像生成、卡片激活状态及与 AI 面板的联动；将其解耦可以独立管理布局（左右列）、主题皮肤和交互节奏，避免对其他视图的 DOM 结构和状态管理造成污染，同时便于后续为不同学校或主题扩展更多榜单模式。
- `renderLeaderboard(container, state, dispatcher)` 接收三个输入：① `container` 为渲染根节点；② `state` 提供 `leaderboard` 数据结构与当前 `leaderboardView` 选择；③ `dispatcher` 负责跨视图事件广播。该视图输出内容包括：模式切换按钮、学者卡片（头像/职衔/简介/标签/引用数动画）、论文条目（排名、题名、元信息、引用数、相对影响力条）以及激活态视觉反馈。
- 内部逻辑自上而下分为：① 数据整备与模式确定（`availableViews`、`activeView`）；② 顶部视图切换器监听器；③ 双列布局（`renderScholars`、`renderPapers`）；④ 卡片/条目入场动画、头像 fallback、引用数字插值、进度条归一化；⑤ 点击事件触发 `paperSelected`，附带 `prompt_type`、`leaderboardView` 等上下文；整体围绕“渲染→动画→交互→联动”循环执行，且在视图切换时重用相同容器更新数据。
- 其他模块在构建仪表盘时直接调用 `renderLeaderboard` 并传入共享 `state`、`dispatcher`；当用户在此视图点击学者或论文时，会通过 `dispatcher.call('paperSelected', …)` 向 AI 面板等组件投递上下文，从而触发摘要生成；全局 `state.leaderboardView` 也因用户切换而同步，让 AI 面板、流向视图等能识别当前榜单来源，实现跨视图一致性。

### overview

- overview.js 的概览视图承担全局宏观指标展示：以年度论文数量与引用趋势曲线、Top venues/keywords 列表、同比卡片与文字快照组成“总览控制台”，帮助用户快速锁定研究热度、峰值年份及重点主题，是其他视图的入口与节奏基准。
- 之所以独立成组件，是因为它集成了自适应折线/面积图（SVG+D3）、年份滑条、指标卡、洞察文本与跨视图事件同步等多层 UIs，需要独立管理 `yearlyData`、`selectedYear`、tooltip/focus 状态；拆分后不仅降低对其他视图的 DOM 干扰，还可单独复用或懒加载概览逻辑，保持项目整体架构清晰。
- `renderOverview(container, state, dispatcher)` 的输入包括：① `container` 作为渲染根；② `state.summary`（含 `yearly`、`venues`、`keywords`）与 `state.filters.year`；③ `dispatcher` 用于 `viewUpdate` 事件。组件输出内容涵盖：筛选面板（年份滑条、年度指标、Top venues/keywords 列表）、趋势面板（论文面积+引用折线+双轴+tooltip）、洞察面板（年度快照文案）。
- 内部结构流程：先校验 summary→整理 `yearlyData`→设置默认年份→构建三块面板（controls/trend/insights）；控制面板包含滑条、指标卡、Mini 列表；趋势面板构造 d3 scales、面积/折线、焦点线与 tooltip overlay，并在鼠标交互时更新焦点与 tooltip；洞察面板根据当前年份组装 venue/keyword Top、同比描述等文案。状态更新函数 `updateInsights`、`updateMetricCards`、`updateSnapshot` 与 `updateFocus` 协同保持 UI 一致。
- 其他视图在初始化仪表盘时调用 `renderOverview`，并共享全局 `state` 与 `dispatcher`。用户拖动年份滑条或点击趋势图，会通过 `dispatcher.call('viewUpdate', …)` 广播年份变动，驱动流向图、语义地图、AI 面板等同步；反之，当其他视图广播年份时，概览视图的 `externalHandler` 会更新本地 `selectedYear` 与 UI，使整个系统维持一致的年度上下文。

### wordcloud

- word_cloud.js 的词云视图主要负责根据 `state.wordcloud` 的年度关键词权重，生成带有集群分类、同比趋势与 AI 助手入口的互动词云，用于洞察热点主题的体量和变化速度，补充整体项目在“主题热词”维度的分析能力。
- 将其独立成组件的原因：词云需要单独加载 `d3.layout.cloud`、维护布局参数（词数、引用阈值、旋转策略）、处理 Canvas/SVG 复合渲染、Hover/Click 交互以及与 AI 卡片的联动，这些逻辑与其他视图耦合度低、性能和依赖独特，因此拆分能保持代码清晰并便于按需加载。
- `renderWordCloud(container, state, dispatcher)` 输入：① `container` 为挂载根；② `state.wordcloud`（按年划分的 `text/size` 列表）与 `state.filters.year`；③ `dispatcher` 用于跨视图同步。视图输出元素包括：控制面板（年份/词数/阈值/倾斜滑块、重新排布按钮、集群图例）、主舞台 SVG 词云（带 Tooltip、状态徽章、加载提示）、AI 解释卡与 Top5 排行榜。
- 逻辑结构概览：初始化控制面板与图例 → 解析数据构建年份索引、全局范围 → `runLayout()` 根据当前筛选过滤/排序词条、推断 YoY/集群，并用 `d3.layout.cloud` 计算位置 → `drawWords()` 渲染文本节点并挂载 Hover/Click 事件 → 点击词语时更新 AI 提示卡、设置 `selectedToken` 并通过 `dispatcher` 广播；同时维护 Stage 徽章、Top5 列表、ResizeObserver 与外部年份同步。
- 其他模块在仪表盘装载时调用 `renderWordCloud`，并与全局 `state` 共用 `dispatcher`。当用户在词云视图调整年份或选择关键词，组件会调用 `dispatcher.call('viewUpdate', …)` 或 `dispatcher.call('paperSelectedSync', …)`，触发概览/AI 面板等视图的同步；若其他视图广播年份变更，`word_cloud` 的 `externalHandler` 会接收并刷新本地布局，实现全局一致的时间上下文。

## Datasets

### 方法论

#### 数据采集

利用 OpenAlex API 获取 2014-2024 期间 CVPR、ICCV、ECCV 等顶级会议的 100,000+ (103815)条原始数据

#### 数据清洗与富集

- 黑名单过滤：建立NLP停用词库，剔除“Image”、“Method”等无意义高频词以及跨学科噪声（如误入的心理学标签）
- 引用归一化：针对年份差异（老论文引用天然高于新论文），引入“相对影响力评分”算法，确保2024年的新兴热点（如Diffusion）不被掩盖

#### 技术栈

后端Python处理大规模JSON聚合；前端D3.js+Canvas进行高性能渲染

### Collector

**功能定位**：data_collector.py 属于数据采集模块，负责从 OpenAlex API 批量抓取 CVPR/ICCV/ECCV 2014–2024 年论文元数据，形成后续数据清洗与前端可视化所需的原始输入；与前端可视化无直接关系，但为整个可视化系统提供基础数据资产。

- **设计动机**：将采集流程独立成脚本，可集中管理场馆列表、年份区间、代理、请求头及分页策略，避免与数据清洗或前端逻辑耦合；其问题域是“稳定获取多年的顶会论文记录并落盘”，通过单一入口函数 `fetch_all_papers()` 简化运维，同时支持命令行独立运行。
- **数据设计**：脚本以 OpenAlex `works` API 为数据源，按照 venue×year 分页请求，每页 200 条并按引用数降序；采集到的字段包括 `title`、`publication_year`、`cited_by_count`、作者列表、重建的摘要与前五个概念。所有记录即时写入 `data/raw_papers.json`（UTF-8、indent=4）以防崩溃。脚本假设：OpenAlex 可按搜索条件检索对应年份的会议论文，`abstract_inverted_index` 可以重建摘要文本，且使用本地代理即可稳定访问。
- **视图关联**：本文件不渲染视图，但其输出 JSON 是 `data_cleaner.py`、`process_advanced.py` 等管道的上游输入，最终被转换为 `web/data/*.json` 供概览、桑基、景观、词云等视图使用。
- **模块交互**：data_collector.py 通过写入 `RAW_FILE` 与后续脚本共享数据，并依赖共享配置（目录结构、VPN 代理端口）；它不与 Flask 后端或前端直接通信，但在数据流上处于最前端，保障数据源一致性与完整性。

### Cleaner

- **功能定位**：data_cleaner.py 属于数据处理模块，承担从 `raw_papers.json` 生成可用于后续分析和可视化的结构化数据；其职责是去重、过滤无效记录、压缩字段，是前端视图的数据上游，而非采集或可视化代码。
- **设计动机**：为了让后续流程（如 `process_advanced.py`、前端加载）只处理质量可靠、体量可控的数据，该脚本独立存在并专注于清洗逻辑：移除标题缺失/重复、摘要过短等噪声样本，将字段统一映射为紧凑键名（`t/y/c/v/a/abs/con`），解决原始数据杂乱、冗长且可能包含空值的问题。
- **数据设计**：输入为采集脚本生成的 `raw_papers.json`，假设其包含论文字典列表；脚本遍历时依次执行：类型健壮性检查 → 标题存在性与去重 → 摘要长度过滤 → 字段精简。输出的 `cleaned_papers.json` 用 UTF-8、紧凑 JSON 存储，字段语义明确（标题、年份、引用、会议、作者、摘要、概念），为后续聚合脚本提供统一 schema。
- **视图关联**：本文件不直接实现任何前端视图，但其输出为概览、桑基、语义景观、词云等视图的数据源之一，因此在报告中应强调它是“前端可视化数据管线”的关键环节，负责保障数据完整性与一致性。
- **模块交互**：数据流为 data_collector.py → data_cleaner.py → 其他处理脚本（如 `process_advanced.py`、`create_data.py`），最终生成 `web/data/*.json`；脚本通过文件读写与后续模块通信，不与 Flask 后端或视图直接交互，但决定了前端可视化能否获得干净、紧凑的数据。

### Processor

- **功能定位**：final_processor.py 是可视化数据管线的统一入口，负责以既定参数调用 `process_advanced.main()`，一次性生成前端真正使用的高密度语义景观点集 (`landscape_data.json`) 和流向矩阵 (`sankey_data.json`)；因此它归属“数据处理/预计算”层，为前端所有视图提供核心素材，而非数据采集或可视化代码。
- **设计 rationale**：早期项目曾尝试直接运行 `process_advanced.py` 的 CLI 或使用简化的 `processor.py` / `wordcloud_*` 脚本，但在样本量扩展到 1.5 万篇、需要同步控制 TF-IDF 维度、年度采样数、桑基阈值等参数时，命令行配置冗长且易错。final_processor.py 将这些关键超参固化为默认值，通过 `python scripts/final_processor.py` 即可重复得到同一套数据，解决了“高维配置记忆困难”和“多数据源参数漂移”的问题。
- **数据设计**：模块默认读取 `data/cleaned_papers.json`（由 data_cleaner.py 输出），并将 CLI 参数打包传给高级管线：`--top-per-year` 控制每年采样上限以平衡热点年份；`--max-landscape` 限制投影点总量；`--tfidf-features`、`--top-terms` 决定语义标签密度；`--min-link` 保障桑基边权的可读性。脚本假设输入数据已完成去重与字段规范化，只需进一步抽样、嵌入、聚类和流向聚合即可用于前端渲染。
- **视图关联**：final_processor.py 不直接实现视图，但它输出的 `landscape_data.json` 与 `sankey_data.json` 分别驱动语义景观视图和研究流向视图；这些数据随后被 `renderLandscape`、`renderFlow` 加载，成为前端可交互的点云、锚点、桑基节点与边。
- **模块协作**：该入口通过 `build_cli()` 将参数数组传递给 `process_advanced.main`，后者负责 TF-IDF、SVD、t-SNE、MiniBatchKMeans 等繁重步骤；输出文件位于 `data/` 目录，供 `web/src/views/*.js` 异步加载。相比旧版的 `processor.py`（仅统计 summary、关键词）或 `wordcloud_*`（单独生成词云数据），final_processor.py 实际被部署用于当前前端，因为它统一驱动了景观与桑基两大数据源，避免多脚本之间的口径不一致，并支持一次运行即可得到全部必需资产。

## backend

**Server**

- **功能定位**：server.py 是系统的 AI 分析服务端，负责接收前端（如 AI 面板、词云、榜单等）发起的 `/api/analyze` 请求，代理调用 DeepSeek、ChatGPT、Gemini、豆包或本地 mock 引擎并返回摘要、关键词、置信度等结果；因此它属于“数据处理/洞察生成”层，而非前端可视化或原始数据采集。
- **设计动机**：将 AI 调用封装为单独 Flask 模块，可统一管理多模型路由、API Key 读取、错误处理与 CORS 配置，解决前端直接访问外部模型 API 带来的跨域、安全和密钥泄露问题；同时通过 mock/真实模式切换，支持在无 Key 场景下演示。
- **数据设计**：输入为 JSON 请求体，包含 `text`（分析主题）、`context`（年份、venue、summary、concepts 等）、`model`、`prompt_type`、可选 `api_key`。模块根据模型类型路由至对应 `call_*` 函数或 `generate_mock_response`，在调用真实 API 前统一构造 prompt、payload，假定上下文字段存在但允许缺省。输出结构固定为 `{summary, keywords, confidence}` 或错误信息，方便前端直接展示。
- **视图相关**：本文件不渲染前端视图，但其返回的数据直接驱动 AI 面板中的 Markdown 摘要、关键词 Chips 和 KaTeX 渲染，因此在报告中应强调它是“视图的数据供应者”，负责将复杂的 LLM 响应规整为前端可消费的语义。
- **模块交互**：前端通过 `fetch('/api/analyze', …)` 与该服务通信；服务端利用 `dispatcher` 广播结果的逻辑发生在前端，后端仅返回 JSON。`/api/health` 提供健康检查与可用模型列表，供部署或前端调试检查；真实模型调用依赖 `requests` 与环境变量 API Key，mock 模式则在本模块内生成内容。

## other files

### router.js

- **功能定位**：router.js 是前端可视化框架的视图调度器，负责在单页应用中根据用户导航切换概览、语义景观、流向、词云、AI 面板、榜单等视图，并在切换时执行对应的渲染与清理逻辑。它完全属于前端视图层，承担页面级路由与生命周期管理的职责，而非数据采集或后端处理。
- **设计 rationale**：将路由与视图挂载逻辑独立成模块，可以将“容器清空、动画过渡、错误兜底、cleanup 回调”等通用行为集中处理，避免在每个视图中重复手写卸载与异常处理。同时，集中式路由使得新增视图或调整导航顺序时仅需修改 `routes` 映射，解决多视图切换难、资源泄露风险高的问题。
- **数据设计**：路由本身不拉取数据，它通过 `initRouter(containerSelector, dispatcher, state)` 接收由 main.js 管理的全局 `state` 与 `dispatcher`，并将其透明传给各 `render*` 视图。模块假设这些视图遵循统一签名 `(mount, state, dispatcher, params)`，并可选择返回一个清理函数，形成约定式的生命周期契约。
- **视图设计**：`routes` 字典定义了各个视图名称与渲染函数的绑定；`navigateTo` 负责添加过渡类、调用渲染器、展示错误占位和执行视图返回的清理回调；`refresh` 则用于窗口尺寸变化时重新渲染当前视图。通过这一机制，所有可视化模块被统一挂载到 `mount` 容器，保证切换动画、空状态、错误提示一致。
- **模块交互**：router.js 与 main.js 协作：主入口在数据加载后实例化路由并调用 `navigateTo`；各视图内部再借助 `dispatcher` 与其他模块通信（如概览广播年份、AI 面板监听选择）。路由本身作为中枢仅负责“视图装卸 + 参数传递”，不会修改状态，从而保持结构清晰、易于扩展。

### index.html

- **整体职责**：`index.html` 是前端应用的唯一入口文件，负责搭建基础 DOM 框架、引入全局资源与装载脚本，同时作为 Portal 与主应用的宿主；它不包含业务逻辑、数据处理或可视化渲染，而是把这些责任交给 main.js 及各视图模块，从而保持入口文件的轻量与稳定。
- **页面结构设计**：页面由 `body.landing-active`、SpaceX 风格 Portal（含各 “VIEW xx” 展示段）、侧边导航与滚动控制、隐藏的主导航 (`.navbar`)、视图容器 (`#view-container`)、全局 AI Panel 构成，另有背景 Canvas 与头部品牌区。通过将 Portal 与正式应用共置，项目既能提供沉浸式落地页体验，又确保主视图挂载点简洁清晰；`#view-container` 初始仅含 loading，占位待 JavaScript 注入。
- **资源加载与初始化**：`head` 中按需加载 D3、d3-contour/geo、marked、KaTeX、全局 `style.css` 等依赖，并在底部引入 d3-cloud 和 main.js（ES Module）；这些 CDN/本地资源共同为可视化、Markdown、数学公式等功能提供支撑。入口文件只负责加载与顺序控制，真正的数据获取、状态初始化和视图挂载在 main.js 内完成。
- **与前端视图的关系**：`index.html` 通过 `#view-container` 和 `#global-ai-panel` 等占位，交由 main.js 及 router.js 将 Overview/Landscape/Flow/WordCloud/Leaderboard/AI 视图动态渲染进去。Portal 段通过 `data-target` 标记对应视图，JavaScript 监听按钮点击后触发路由跳转；因此视觉、交互均由 JS 组件驱动，入口页面仅提供结构与语义钩子。
- **可维护与扩展性**：入口页面保持无业务逻辑，方便在不触及核心 JS 的情况下调整品牌、Portal 视觉或全局容器；新增视图仅需在导航/Portal 增加项并让 router 注册即可。此设计的权衡在于：HTML 本身不具备渲染能力，全部依赖 JS 初始化——若脚本加载失败，页面仅显示骨架，但这符合现代 SPA 的分层策略，便于统一管理状态与路由。

### main.js

- **功能定位**：main.js 是前端可视化系统的“应用入口与状态协调器”，负责加载所有数据集（summary、landscape、sankey、wordcloud、leaderboard）、初始化全局 `state` 与 `dispatcher`，搭建路由、导航、Portal 登录页、全局 AI 面板等壳层逻辑；它完全属于前端可视化层，并统筹各视图的生命周期与事件同步。
- **设计 rationale**：将这一层单独成模块，可集中解决跨视图的数据共享、懒加载、导航体验（含 SpaceX 风格 Portal、滚动定位、Digital Clock）以及事件派发，避免在每个视图中重复处理路由、数据获取或全局状态；main.js 提供单一初始化入口，使团队可以在不修改各子视图的情况下扩展导航、动画或全局面板，实现低耦合的应用框架。
- **数据设计**：文件通过 `loadData()` 调用 `fetchDatasetWithFallback`，对每个数据源设置本地/部署双路径，并在 Promise 汇聚后写入 `state.summary/landscape/sankey/wordcloud/leaderboard`；还负责推导默认年份过滤（取 summary 的最新年份）并填充 `state.filters.year` 与 `state.selection`。假设数据文件已由后端脚本生成且结构稳定，前端只需 JSON 读取即可。
- **视图相关**：main.js 不直接绘制可视化，但它初始化路由（`initRouter`）、导航交互（`setupNavigation`）、登录 Portal（`setupSpaceXLanding`）、全局 AI 面板（`setupGlobalPanel`）以及窗口重绘刷新（`handleResize`），确保 Overview、Landscape、Flow、Leaderboard、WordCloud 等视图以统一方式挂载在 `#view-container` 下，并能通过 `dispatcher` 接收 `viewUpdate` / `paperSelected` 事件。
- **模块协作**：文件创建的 `dispatcher` 提供 `viewUpdate`、`paperSelected`、`paperSelectedSync` 三类事件；`bridgeDispatcher()` 负责跨视图年份同步与 selection 状态持久化，并把同步事件转发到全局面板。它与 `router.js`、`bg-animation.js` 等壳层模块协作，向各子视图传入共享 `state` 和 `dispatcher`，形成“主控制器 → 子视图”组件层级，也是前端与后端 Flask API 的桥梁（例如 AI 面板通过 dispatcher 将选中项传给 main.js，再由 main.js 更新全局 AI 面板文案）。

### style.css

- **整体视觉与体验**：`web/style.css` 定义了整套“航天科技 + 数据驾驶舱”风格，通过深色背景、霓虹渐变、高对比信息卡、柔和动效，营造具有未来感的沉浸式体验；全局样式强调阅读层次（粗体标题、柔和正文）、可视化与 AI 模块的共存感，并在落地页与工作区之间维持统一的品牌语言，确保用户穿梭各视图时感知连续、节奏一致。
- **样式组织策略**：文件按“基础重置 → 全局变量/排版 → 布局容器 → 导航 & Portal → 各视图共享组件（panel, card, tooltip） → 特殊模块覆盖”递进组织，将所有跨视图共用的样式集中维护，避免在分散的 CSS 片段中重复定义色值或布局规则；集中式 `style.css` 方便脚本化构建与主题切换，也便于在报告中说明“统一设计系统”的存在。
- **设计系统要素**：文档内通过 CSS 变量/类约定了主辅色（青蓝、琥珀、紫等）、渐变轨迹、阴影层级、玻璃拟态面板、流式网格间距等原则；字体以现代无衬线配合定制数字字体，间距遵循 8/12px 模数，组件间使用统一圆角、描边、动效时长；同时复用 `panel`, `metric-card`, `delta-pill`, `chart-tooltip` 等原子样式，形成可在多个视图复用的视觉模式。
- **与视图的关系**：概览、流向、语义景观、AI 面板、词云等视图均继承 `panel` 与排版基类，并通过 `metric-card`, `legend`, `chip`, `tooltip` 等通用样式实现一致的卡片语言；导航、Portal、全局 AI 折叠面板等壳层组件共享阴影、渐变、动画规范，使得不同视图虽功能各异，却保持统一的视觉节奏和交互反馈。
- **可维护性与扩展性**：集中式样式允许在新增视图时直接复用既有组件类，或通过新增少量修饰类实现差异化；当需要改版主题、调整网格或响应式策略时，可在单文件内统一调整。权衡在于：集中样式需谨慎命名以避免冲突，且修改可能影响多视图，需要严格的命名约定与测试流程，但整体上为项目提供了更易迭代的设计系统基础。

### bg-animation.js

- **功能定位**：bg-animation.js 实现 Portal 阶段的背景粒子动画，属于前端可视化层的“装饰/沉浸式体验”模块，不参与数据采集或业务图表渲染。它通过 `ParticleBackground` 类在落地页背后生成动态粒子和模式切换，让用户在进入数据视图前获得统一的品牌体验。
- **设计 rationale**：动画模块独立成文件，便于在不影响主数据视图的情况下调整特效、性能策略或关闭动画；同时通过 `setMode()` 针对不同 Portal section 切换粒子形态（球体、波浪、流线、云爆、塔、立方）和配色，解决了“如何在概览/景观/流向等入口之间建立情绪联系”的问题。
- **数据设计**：该模块不消费业务数据，仅使用视窗尺寸、光标位置及当前 section ID 作为输入，内部维护粒子数组、颜色映射、运动参数；假设 Portal 视图会告知 `ParticleBackground` 当前 section（通过 `setMode`），并监听 `prefers-reduced-motion` 媒体查询以自适应动画强度。
- **视图关联**：动画并不渲染主 BI 视图，而是在 Portal 背景的 `canvas#bg-canvas` 绘制 3D 投影粒子，随着 section 切换呈现不同视觉符号（sphere/wave/stream/cloud/pillar/network）；当用户进入应用主体后，main.js 会切换 body class 以暂停动画，避免干扰数据面板性能。
- **模块交互**：main.js 在 `setupSpaceXLanding()` 中实例化 `ParticleBackground` 并在 IntersectionObserver 回调里调用 `bgAnimation.setMode(id)`；模块自身监听窗口大小、指针事件、`prefers-reduced-motion` 变化，并通过 requestAnimationFrame 循环在落地页激活状态下渲染。通过这种松耦合方式，动画模块可被单独替换或扩展，同时不会污染业务视图逻辑。