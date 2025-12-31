// web/src/main.js
import { initRouter } from './router.js';
import { ParticleBackground } from './bg-animation.js';

const dispatcher = d3.dispatch("viewUpdate", "paperSelected", "paperSelectedSync");
const state = {
    summary: null,
    landscape: null,
    sankey: null,
    wordcloud: null,
    filters: {
        year: null
    },
    selection: null // Add selection state
};

let routerInstance = null;
let resizeTimer = null;

const dataSources = [
    { key: "summary", paths: ["./data/summary.json", "../data/summary.json"] },
    { key: "landscape", paths: ["./data/landscape_data.json", "../data/landscape_data.json"] },
    { key: "sankey", paths: ["./data/sankey_data.json", "../data/sankey_data.json"] },
    { key: "wordcloud", paths: ["./data/wordcloud_data.json", "../data/wordcloud_data.json"] },
    { key: "leaderboard", paths: ["./data/leaderboard_seeds.json", "../data/leaderboard_seeds.json"] }
];

function setupNavigation(router) {
    d3.selectAll(".nav-links li").on("click", function () {
        const view = d3.select(this).attr("data-view");
        d3.selectAll(".nav-links li").classed("active", false);
        d3.select(this).classed("active", true);
        router.navigateTo(view);
    });
}

function setupSpaceXLanding(router) {
    const portal = d3.select("#portal-container");
    if (portal.empty()) return;

    const body = d3.select("body");
    const sections = document.querySelectorAll('.snap-section');
    const navDots = document.querySelectorAll('.side-nav .dot');
    const clockEl = document.getElementById("digital-clock");
    const portalHeader = d3.select("#portal-header");
    const appNavbar = d3.select(".navbar");
    const viewContainer = d3.select("#view-container");
    const sideNav = d3.select(".side-nav");
    const scrollControls = d3.select(".scroll-controls");

    // Initialize Background Animation
    const bgAnimation = new ParticleBackground('bg-canvas');

    // 1. Digital Clock
    function updateClock() {
        if (!clockEl) return;
        const now = new Date();
        const pad = n => n.toString().padStart(2, '0');
        const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
        const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
        const dateEl = clockEl.querySelector('.clock-date');
        const timeEl = clockEl.querySelector('.clock-time');
        if (dateEl) dateEl.textContent = dateStr;
        if (timeEl) timeEl.textContent = timeStr;
        if (!dateEl && !timeEl) {
            clockEl.textContent = `${dateStr} ${timeStr}`;
        }
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 2. Intersection Observer for Scroll Spy
    const observerOptions = {
        root: portal.node(),
        threshold: 0.5
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Update active section class
                sections.forEach(s => s.classList.remove('active'));
                entry.target.classList.add('active');

                // Update nav dots
                const id = entry.target.getAttribute('id');
                navDots.forEach(dot => {
                    dot.classList.toggle('active', dot.getAttribute('href') === `#${id}`);
                });

                // Update Background Animation Mode
                if (bgAnimation) {
                    bgAnimation.setMode(id);
                }
            }
        });
    }, observerOptions);

    sections.forEach(section => observer.observe(section));

    // 3. Scroll Controls
    d3.selectAll('.side-nav .dot, .scroll-controls button').on('click', function (event) {
        event.preventDefault();
        const targetId = this.getAttribute('data-target') || this.getAttribute('href');
        let targetEl;

        if (this.id === 'btn-prev' || this.id === 'btn-next') {
            const currentSection = document.querySelector('.snap-section.active');
            targetEl = this.id === 'btn-next' ? currentSection?.nextElementSibling : currentSection?.previousElementSibling;
        } else if (this.id === 'btn-top') {
            targetEl = document.getElementById('section-overview');
        } else if (this.id === 'btn-bottom') {
            targetEl = document.getElementById('section-ai');
        } else if (targetId) {
            targetEl = document.querySelector(targetId);
        }

        if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth' });
        }
    });

    // 4. Enter View Logic
    function enterView(viewName) {
        // Transition Out Portal
        body.classed("landing-active", false);
        portal.style("display", "none");
        sideNav.style("display", "none");
        scrollControls.style("display", "none");
        portalHeader.style("transform", "translateY(-100%)");

        // Transition In App
        appNavbar.style("display", "flex").style("opacity", 0)
            .transition().duration(500).style("opacity", 1);
        viewContainer.style("display", "block").style("opacity", 0)
            .transition().duration(500).style("opacity", 1);

        // Navigate Router
        router.navigateTo(viewName);
        d3.selectAll(".nav-links li").classed("active", function () {
            return d3.select(this).attr("data-view") === viewName;
        });
    }

    d3.selectAll('.enter-view-btn').on('click', function () {
        const section = this.closest('.snap-section');
        const viewName = section.getAttribute('data-target');
        enterView(viewName);
    });

    // 5. Back to Portal Logic
    d3.select("#back-to-portal").on("click", function () {
        // Transition Out App
        appNavbar.transition().duration(300).style("opacity", 0)
            .on("end", () => appNavbar.style("display", "none"));
        viewContainer.transition().duration(300).style("opacity", 0)
            .on("end", () => viewContainer.style("display", "none"));

        // Transition In Portal
        body.classed("landing-active", true);
        portal.style("display", "block");
        sideNav.style("display", "flex");
        scrollControls.style("display", "flex");
        portalHeader.style("transform", "translateY(0)");
    });
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

    // Persist selection to state
    dispatcher.on("paperSelected.state", payload => {
        // If selecting the same item, keep the existing cache if valid
        if (state.selection &&
            state.selection.title === payload.title &&
            state.selection.summary === payload.summary) {
            return;
        }
        state.selection = payload;
        console.log("[State] Selection updated:", payload?.title || "None");
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
        setupSpaceXLanding(routerInstance);
        setupGlobalPanel();
        bridgeDispatcher();
        routerInstance.navigateTo('overview');
        window.addEventListener('resize', handleResize);
    } catch (error) {
        console.error("初始化失败:", error);
    }
}

init();