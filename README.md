# CV Explorer (2014—2024): A Decade of Computer Vision Evolution
# 计算机视觉十年 (2014—2024) 可视化分析系统

> **Map the coordinates of Computer Vision history. / 构建你的计算机视觉十年坐标系。**
> A professional data visualization system integrating longitudinal trends, semantic landscapes, citation flows, and AI-driven synthesis. / 一个整合了发展趋势、语义地貌、研究流向与 AI 深度解读的专业可视化系统。

[![Live Demo](https://img.shields.io/badge/demo-Vercel-black?style=for-the-badge&logo=vercel)](https://visualization-project-2025.vercel.app/)
[![GitHub Repo](https://img.shields.io/badge/repo-GitHub-181717?style=for-the-badge&logo=github)](https://github.com/ZR-1N/Visualization_Project_2025)

---

## 🌌 Project Vision / 项目愿景

[EN] Between 2014 and 2024 the CV community jumped from CNN supremacy to Transformer unification and AIGC dominance. CV Explorer treats those 100k+ papers as an archaeological site: using Computer Graphics tooling (UMAP, KDE, Marching Squares, Sankey, d3-cloud) we reconstruct the "Academic Star Map" that reveals where breakthroughs erupted and how influence traveled.

[CN] 2014-2024 的计算机视觉领域经历了从 CNN 到 Transformer，再到 AIGC 爆发的范式迁移。CV Explorer 以图形学+信息可视化的方法，把 10 万+ 顶会论文重建为「学术星图」，让研究者快速定位历史脉络、转折节点与未来势能。

---

## ☄️ Feature Constellation / 特色功能

- **SpaceX Portal & Snap Scroll / SpaceX 叙事门户**：Landing 页以 `bg-animation.js` 粒子背景、数字钟与侧边航点打造沉浸式入场，单击“Enter View”即可切换到六大视图，提供类似星舰发射的叙事实验。
- **Global Dispatcher Core / 事件总线同步**：`main.js` 通过 `d3.dispatch` 暴露 `viewUpdate`, `paperSelected`, `paperSelectedSync`，保证年份、选中论文与 AI 面板在多视图间实时联动。
- **Canvas + SVG Hybrid Landscape / 语义地貌混合渲染**：`views/landscape.js` 将 15k 语义点云投射到 Canvas，借助 Marching Squares、迷你雷达、语义锚点与缩放手势实现科研“气候带”探索。
- **Sankey-led Research Flow / 研究流向自适应**：`views/flow.js` 接入 `d3-sankey@0.12.3`，配合播放年轴、问题/方法过滤与 YoY 标注，跟踪检测→多模态→生成式链路的能量迁移。
- **LLM-ready Insight Panel / AI 深度解读**：`views/ai_panel.js` 将选中节点推送到 Flask 后端 (`backend/server.py`)，支持 Mock/DeepSeek/ChatGPT/Gemini/豆包多模型切换，并用 KaTeX + Marked 渲染 Markdown/公式，离线也可用模拟响应。
- **NKU Dual Leaderboard / 南开双视角封神榜**：`views/leaderboard.js` 提供 GLOBAL 与 NANKAI 主题，同时触发 `paperSelected` 事件，方便 AI 面板生成学者/论文小传。

---

## 🧱 System Architecture / 系统架构

**Data Layer / 数据层** — `cv-explorer/scripts/*.py` 负责采集、清洗与降维：`data_collector.py` 抓取 OpenAlex（支持代理），`data_cleaner.py` 去重抽象，`final_processor.py` 调 `process_advanced.py` 生成 `landscape_data.json`、`sankey_data.json` 等高密度资产，`data/create_data.py` 补充排行榜种子。

**Backend Layer / 后端层** — `cv-explorer/backend/server.py` 是 Flask+CORS 微服务：`POST /api/analyze` 将前端上下文转发到 DeepSeek/OpenAI/Gemini/豆包，未配 Key 时回退到 Mock，总能得到结构化摘要与关键词；`GET /api/health` 用于部署监测。

**Frontend Layer / 前端层** — `cv-explorer/web` 采用零构建 Vanilla JS。`main.js` 负责 dataset fallback 加载、SpaceX Landing、全局 AI 抽屉与 Resize Observer；`router.js` 动态挂载 `overview / landscape / flow / wordcloud / leaderboard / ai` 六个视图，每个视图都是 D3 组件（Canvas+SVG+HTML overlay）。

**Deployment / 部署** — 前端通过 `vercel.json` 部署到 Vercel（线上 demo 已连通 `/api` 代理）；本地可用 VS Code Live Server 或 `npx http-server`，后端以 `python server.py` 跑在 `localhost:5000`，可借 VS Code `liveServer.settings.proxy` 或 nginx 将 `/api/*` 反代至 Flask。

```
OpenAlex / Scholar dumps
		  │
scripts/data_collector.py → data/raw_papers.json
		  │
scripts/data_cleaner.py   → data/cleaned_papers.json
		  │
scripts/final_processor.py → data/{landscape,sankey,summary,wordcloud}_data.json
		  │
cv-explorer/web/data/*.json ──▶ main.js state loader ──▶ router/views
		  │                                              │
		  └─────────────── AI selections ────────────────┘
											  │
							backend/server.py → LLM providers / Mock
```

---

## 🛰 Visual Modules / 航行指南

### 01 Evolutionary Overview / 发展概览（`views/overview.js`）
堆叠面积图+双轴折线梳理年度产出与引用，滑块同步所有视图，mini 面板即时列出该年的 Top Venues & Keywords，并自动生成年度快照叙述。

### 02 Semantic Landscape / 语义景观（`views/landscape.js`）
UMAP+KDE 语义蒙版叠加网格与迷你地图，支持年份/会议/锚点/平滑度调节、Canvas Zoom、语义锚点标签以及 Hover 工牌，适合探索研究“岛屿”与学科气候。

### 03 Research Flow / 研究流向（`views/flow.js`）
Sankey 将问题域→方法族转换为可追溯能量带，内置时间轴播放、All-year 汇总、YoY Trend Pills、关键字搜索与 Top 流向摘要，帮助观察 Transformer、Diffusion 等浪潮的接力。

### 04 Keyword Word Cloud / 趋势词云（`views/word_cloud.js`）
`d3.layout.cloud` + 聚类色板将关键词按引用量、同比增速、新旧程度分类，搭配 Top5 Ranking、AI 卡片与 Year Slider，点击任意词即可把上下文推送到 AI 面板。

### 05 Academic Pantheon / 学术封神榜（`views/leaderboard.js`）
GLOBAL 模式展示图灵奖/Backbone 级学者与经典论文；NANKAI 模式突出南开视觉团队（Res2Net、PVT、显著性检测）。点击卡片会附带 prompt_type（scholar_profile/paper_impact）触发 LLM 解读。

### 06 AI Insight / AI 深度解读（`views/ai_panel.js` & `#global-ai-panel`）
双通道：全局浮动面板用于选中节点时的快速摘要；AI 页面提供 API Key 配置、KaTeX/Markdown 渲染、关键词 Chips 与 Venue/Keyword 总览，实现“图表→文字”闭环。

---

## 📈 Data Workflow / 数据工作流

1. **Collect / 数据采集**
	```bash
	cd cv-explorer
	python scripts/data_collector.py  # 需要稳定代理 (默认 127.0.0.1:7890)
	```
2. **Clean / 数据清洗**
	```bash
	python scripts/data_cleaner.py  # 输入 data/raw_papers.json，输出 data/cleaned_papers.json
	```
3. **High-density Processing / 高密度生成**
	```bash
	python scripts/final_processor.py \
	  --input data/cleaned_papers.json \
	  --landscape-output data/landscape_data.json \
	  --sankey-output data/sankey_data.json
	```
	重要参数：`--top-per-year` 控制年度采样，`--max-landscape` 设置语义点上限，`--min-link` 过滤细流。
4. **Leaderboard Seeds / 封神榜数据**
	```bash
	python data/create_data.py  # 生成 data/leaderboard_seeds.json
	```
5. **Sync to Frontend / 同步前端数据** — 将 `data/*.json` 复制到 `cv-explorer/web/data/`，或在构建脚本中软链，保证浏览器读取本地 JSON。

---

## 🗂 Directory Map / 目录结构

```
cv-explorer/
├── backend/
│   ├── requirements.txt
│   └── server.py
├── data/
│   ├── cleaned_papers.json (生成)
│   ├── landscape_data.json (生成)
│   ├── leaderboard_seeds.json
│   ├── raw_papers.json (生成)
│   └── summary/wordcloud/sankey_data.json
├── scripts/
│   ├── data_collector.py · data_cleaner.py · final_processor.py · process_advanced.py
│   └── wordcloud_new.py 等分析脚本
└── web/
	 ├── index.html · style.css · assets/
	 └── src/
		  ├── bg-animation.js · main.js · router.js
		  └── views/overview.js · landscape.js · flow.js · word_cloud.js · leaderboard.js · ai_panel.js
```

---

## 🧪 Local Setup / 本地运行

**Prereqs / 环境**：Python 3.9+, Node.js（仅需 `npx http-server` 或 VS Code Live Server），可选代理（OpenAlex 抓取）。

1. **Install backend deps / 安装后端依赖**
	```bash
	cd cv-explorer/backend
	python -m venv .venv && .venv\Scripts\activate
	pip install -r requirements.txt
	```
2. **Configure API keys / 配置大模型 Key**
	```powershell
	setx DEEPSEEK_API_KEY "sk-..."
	setx OPENAI_API_KEY "sk-..."
	setx GEMINI_API_KEY "..."
	setx DOUBAO_API_KEY "..."
	```
3. **Run backend / 启动后端**
	```bash
	python server.py  # 默认 0.0.0.0:5000，含 /api/analyze 与 /api/health
	```
4. **Serve frontend / 启动前端**
	```bash
	cd ../web
	npx http-server . -p 4173
	```
	或在 VS Code 中使用 Live Server。若需解决跨域，可在 `.vscode/settings.json` 中加入：
	```json
	{
	  "liveServer.settings.proxy": {
		 "enable": true,
		 "baseUri": "/api",
		 "proxyUri": "http://localhost:5000/api"
	  }
	}
	```
5. **Optional / 选项**：使用 `vercel dev` 同时运行前后端（Vercel 会自动把 `/api/*` 代理到 Flask）。

---

## 🔌 REST API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | 返回状态、已注册模型、版本号，便于存活监控。|
| `/api/analyze` | POST | Body: `{ text, context, model, prompt_type, api_key }`；根据 `model` 调用真实 LLM 或 Mock，输出 `{ summary, keywords, confidence }`。|

Sample:

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
	 "text": "Deep Residual Learning for Image Recognition",
	 "model": "mock",
	 "prompt_type": "paper_impact",
	 "context": {"year": 2016, "venue": "CVPR", "citations": 290000}
  }'
```

---

## 🧰 Tech Stack / 技术栈

- **Visualization / 可视化**：D3.js v7、d3-sankey、d3-cloud、Canvas API、SVG overlays、ParticleBackground。
- **Algorithms / 算法**：UMAP、KDE、Marching Squares、TF-IDF、Citation Normalization、Sankey Layout、自适应词云聚类。
- **Frontend / 前端**：Vanilla JS、CSS Grid/Flexbox、SpaceX Snap Scroll Portal、KaTeX、Marked、LocalStorage 配置面板。
- **Backend / 后端**：Flask 3.0、Flask-CORS、Requests、多模型代理（DeepSeek/OpenAI/Gemini/豆包）+ Mock Fallback。
- **Data Sources / 数据源**：OpenAlex API、Google Scholar（补充引用）、内部南开学术年表。

---

## 🎓 Credits / 学术致谢

Developed by the Computer Science Team at Nankai University. Special gratitude to Prof. Ming-Ming Cheng and the NKU Media Lab for their foundational research support. / 本项目由南开大学计算机学院团队开发，鸣谢程明明教授与 NKU Media Lab 对底层视觉研究的长期投入。

- Field / 学科: Computer Graphics (计算机图形学) · Information Visualization
- Domain / 领域: Computer Vision (计算机视觉)
- Developers / 开发团队: \o/\o/\o/team: Shang Wenxuan (尚文轩), Wang Lezhi (王乐之), Huang Yihao (黄奕浩)

---

## 🔗 Links / 链接

- Deployment / 在线部署: https://visualization-project-2025.vercel.app/
- Repository / 代码仓库: https://github.com/ZR-1N/Visualization_Project_2025

---
© 2026 CV Explorer Team(\o/\o/\o/). Built with Love in Nankai University.