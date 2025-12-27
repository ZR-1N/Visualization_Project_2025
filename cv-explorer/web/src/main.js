// web/src/main.js
import { initRouter } from './router.js';

const dispatcher = d3.dispatch("viewUpdate", "paperSelected", "paperSelectedSync");
const state = {
    summary: null,
    landscape: null,
    sankey: null,
    wordcloud: null,
    filters: {
        year: null
    }
};

let routerInstance = null;
let resizeTimer = null;

const dataSources = [
    { key: "summary", paths: ["./data/summary.json", "../data/summary.json"] },
    { key: "landscape", paths: ["./data/landscape_data.json", "../data/landscape_data.json"] },
    { key: "sankey", paths: ["./data/sankey_data.json", "../data/sankey_data.json"] },
    { key: "wordcloud", paths: ["./data/wordcloud_data.json", "../data/wordcloud_data.json"] }
];

function setupNavigation(router) {
    d3.selectAll(".nav-links li").on("click", function () {
        const view = d3.select(this).attr("data-view");
        d3.selectAll(".nav-links li").classed("active", false);
        d3.select(this).classed("active", true);
        router.navigateTo(view);
    });
}

function setupLanding(router) {
    const landing = d3.select("#landing-shell");
    if (landing.empty()) {
        return;
    }

    const body = d3.select("body");
    const navItems = d3.selectAll(".nav-links li");

    function activateView(targetView = "overview") {
        if (body.classed("landing-active")) {
            body.classed("landing-active", false);
            landing.classed("is-leaving", true);
            setTimeout(() => {
                landing.style("display", "none");
            }, 900);
        }

        if (targetView) {
            router.navigateTo(targetView);
            navItems.classed("active", function () {
                return d3.select(this).attr("data-view") === targetView;
            });
        }
    }

    landing.selectAll('[data-action="enter"]').on("click", (event) => {
        event.preventDefault();
        activateView("overview");
    });
    landing.selectAll(".landing-card[data-view]").on("click", function () {
        const targetView = d3.select(this).attr("data-view") || "overview";
        activateView(targetView);
    });

    const overviewLink = landing.select('a[href="#landing-panels"]');
    if (!overviewLink.empty()) {
        overviewLink.on("click", (event) => {
            event.preventDefault();
            const targetEl = document.getElementById("landing-panels");
            if (!targetEl) {
                return;
            }
            const container = landing.node();
            const offsetTop = targetEl.offsetTop - 32;
            if (container?.scrollTo) {
                container.scrollTo({ top: offsetTop, behavior: "smooth" });
            } else {
                window.scrollTo({ top: offsetTop, behavior: "smooth" });
            }
        });
    }
}

function hydrateLandingStats() {
    const target = d3.select('[data-stat="total-papers"]');
    const yearly = state.summary?.yearly;
    if (target.empty() || !yearly) {
        return;
    }

    const total = Object.values(yearly).reduce((sum, entry) => {
        const count = Number(entry?.count) || 0;
        return sum + count;
    }, 0);

    if (!Number.isFinite(total) || total <= 0) {
        return;
    }

    const formatted = d3.format(",")(total);
    target.text(`${formatted}+`);
    target.attr("title", `清洗后样本总量 ${formatted}`);
}

function setupGlobalPanel() {
    const panel = d3.select("#global-ai-panel");
    const header = panel.select(".panel-header");
    header.on("click", () => {
        panel.classed("collapsed", !panel.classed("collapsed"));
    });

    dispatcher.on("paperSelected.globalPanel", payload => {
        const responseArea = panel.select("#ai-response-area");
        if (!payload) {
            responseArea.text("请在图中选择感兴趣的内容...");
            return;
        }

        panel.classed("collapsed", false);
        const title = payload.title || payload.label || `${payload.source || ''} → ${payload.target || ''}`;
        const metaParts = [];
        if (payload.year) metaParts.push(payload.year);
        if (payload.venue) metaParts.push(payload.venue);
        if (payload.citations != null) metaParts.push(`引用 ${payload.citations.toLocaleString()}`);
        if (!metaParts.length && payload.value) metaParts.push(`权重 ${Math.round(payload.value)}`);
        const concepts = (payload.concepts || payload.keywords || [])
            .slice(0, 5)
            .join(" / ") || payload.summary || "暂无描述";

        responseArea.html(`
            <div class="ai-paper-title">${title}</div>
            <div class="ai-paper-meta">${metaParts.join(" · ") || "上下文信息"}</div>
            <p>${concepts}</p>
        `);
    });
}

function bridgeDispatcher() {
    dispatcher.on("viewUpdate.globalFilter", payload => {
        if (payload?.year && payload.year !== state.filters.year) {
            state.filters.year = payload.year;
            console.info(`[Dispatcher] 年份同步至 ${payload.year}`);
        }
    });

    dispatcher.on("paperSelectedSync.bridge", payload => {
        if (payload) {
            dispatcher.call("paperSelected", null, payload);
        }
    });
}

async function fetchDatasetWithFallback(key, paths = []) {
    for (const candidate of paths) {
        try {
            const payload = await d3.json(candidate);
            console.info(`[Data] ${key} 加载成功 (${candidate})`);
            return payload;
        } catch (error) {
            console.warn(`[Data] ${key} 加载失败 (${candidate})`, error);
        }
    }
    console.error(`[Data] ${key} 所有候选路径均不可用`);
    return null;
}

async function loadData() {
    await Promise.all(
        dataSources.map(async ({ key, paths }) => {
            state[key] = await fetchDatasetWithFallback(key, paths);
        })
    );

    if (!state.filters.year && state.summary?.yearly) {
        const years = Object.keys(state.summary.yearly)
            .map(Number)
            .sort((a, b) => a - b);
        state.filters.year = years[years.length - 1];
    }
}

function handleResize() {
    if (!routerInstance) return;
    if (resizeTimer) {
        clearTimeout(resizeTimer);
    }
    resizeTimer = setTimeout(() => {
        console.log("窗口重塑，刷新视图组件…");
        routerInstance.refresh();
        resizeTimer = null;
    }, 250);
}

async function init() {
    try {
        await loadData();
        hydrateLandingStats();
        routerInstance = initRouter("#view-container", dispatcher, state);
        setupNavigation(routerInstance);
        setupLanding(routerInstance);
        setupGlobalPanel();
        bridgeDispatcher();
        routerInstance.navigateTo('overview');
        window.addEventListener('resize', handleResize);
    } catch (error) {
        console.error("初始化失败:", error);
    }
}

init();