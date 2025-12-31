
const VIEW_CONFIG = {
    global: {
        label: "GLOBAL",
        leftTitle: "Academic Titans · 学术泰斗",
        rightTitle: "Classics · 镇山之作"
    },
    nankai: {
        label: "NANKAI",
        leftTitle: "NKU Pioneers · 南开先导",
        rightTitle: "Masterpieces · 经典名作"
    }
};

export function renderLeaderboard(container, state, dispatcher) {
    container.html("");

    const sourceData = state.leaderboard;
    if (!sourceData) {
        container.append("div")
            .attr("class", "empty-state")
            .text("正在加载学术封神榜数据...");
        return;
    }

    const dataset = (sourceData.global || sourceData.nankai)
        ? sourceData
        : { global: sourceData };

    const availableViews = ["global", "nankai"].filter(view => dataset[view]);
    let activeView = availableViews.includes(state.leaderboardView)
        ? state.leaderboardView
        : availableViews[0] || "global";

    const layout = container.append("div")
        .attr("class", "leaderboard-layout")
        .classed("nankai-mode", activeView === "nankai");

    const viewSwitcher = layout.append("div").attr("class", "view-switcher");
    const viewButtons = viewSwitcher.selectAll("button")
        .data(["global", "nankai"].map(key => ({ key, label: VIEW_CONFIG[key]?.label || key.toUpperCase() })))
        .enter()
        .append("button")
        .attr("type", "button")
        .attr("class", d => `view-btn${d.key === activeView ? " is-active" : ""}`)
        .attr("disabled", d => dataset[d.key] ? null : true)
        .text(d => d.label)
        .on("click", function (event, d) {
            if (!dataset[d.key] || d.key === activeView) return;
            activeView = d.key;
            state.leaderboardView = activeView;
            updateView();
        });

    const board = layout.append("div").attr("class", "leaderboard-container");

    const colScholars = board.append("div").attr("class", "column-scholars");
    const scholarTitle = colScholars.append("h2");
    const scholarList = colScholars.append("div").attr("class", "card-list");

    const colPapers = board.append("div").attr("class", "column-papers");
    const paperTitle = colPapers.append("h2");
    const paperList = colPapers.append("div").attr("class", "card-list");

    function updateView() {
        const config = VIEW_CONFIG[activeView] || VIEW_CONFIG.global;
        const current = dataset[activeView] || dataset.global || { scholars: [], papers: [] };

        state.leaderboardView = activeView;
        layout.classed("nankai-mode", activeView === "nankai");
        viewButtons.classed("is-active", d => d.key === activeView);

        scholarTitle.html(`<span class="icon">👑</span> ${config.leftTitle}`);
        paperTitle.html(`<span class="icon">📜</span> ${config.rightTitle}`);

        renderScholars(scholarList, current.scholars || [], dispatcher, activeView);
        renderPapers(paperList, current.papers || [], dispatcher, activeView);
    }

    updateView();
}

function renderScholars(container, data, dispatcher, mode) {
    const colorScale = d3.scaleOrdinal(d3.schemeTableau10);

    const cards = container.selectAll(".scholar-card")
        .data(data, d => d.name);

    cards.exit()
        .transition()
        .duration(250)
        .style("opacity", 0)
        .style("transform", "translateY(10px)")
        .remove();

    const enterCards = cards.enter()
        .append("div")
        .attr("class", "scholar-card")
        .style("opacity", 0)
        .style("transform", "translateY(30px)");

    enterCards.append("div").attr("class", "rank-watermark");

    const inner = enterCards.append("div").attr("class", "card-inner");
    const avatar = inner.append("div").attr("class", "avatar-circle");
    avatar.append("img").attr("alt", d => d.name).style("display", "none");
    avatar.append("span").attr("class", "avatar-initials");

    const info = inner.append("div").attr("class", "info-col");
    const header = info.append("div").attr("class", "card-header");
    header.append("h3");
    header.append("div").attr("class", "aff");
    info.append("div").attr("class", "scholar-desc");
    const footer = info.append("div").attr("class", "card-footer");
    const citationBlock = footer.append("div").attr("class", "citations");
    citationBlock.html('<span class="label">Citations</span> <span class="value">0</span>');
    footer.append("div").attr("class", "tags");

    const mergedCards = enterCards.merge(cards);

    mergedCards.select(".rank-watermark").text(d => d.rank);

    mergedCards.select(".card-header h3").text(d => d.name);
    mergedCards.select(".card-header .aff").text(d => d.aff || "");

    mergedCards.select(".scholar-desc")
        .text(d => d.desc || "")
        .style("display", d => d.desc ? "block" : "none");

    mergedCards.each(function (d) {
        const avatarNode = d3.select(this).select(".avatar-circle");
        const img = avatarNode.select("img");
        const initials = avatarNode.select(".avatar-initials");
        if (d.image) {
            img.attr("src", d.image).style("display", "block");
            initials.style("display", "none");
            avatarNode.style("background-color", "#1e293b");
        } else {
            img.attr("src", "").style("display", "none");
            const text = d.name
                .split(/\s+/)
                .map(part => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase();
            initials.text(text).style("display", "flex");
            avatarNode.style("background-color", colorScale(d.name));
        }
    });

    mergedCards.select(".citations .value")
        .text("0")
        .transition()
        .duration(1200)
        .tween("text", function (d) {
            const interp = d3.interpolateNumber(0, d.citations || 0);
            return function (t) {
                d3.select(this).text(d3.format(",")(Math.round(interp(t))));
            };
        });

    mergedCards.select(".tags").each(function (d) {
        const tags = d3.select(this).selectAll("span")
            .data(d.tags || [], tag => tag);
        tags.exit().remove();
        tags.enter()
            .append("span")
            .merge(tags)
            .text(tag => tag);
    });

    const interactiveCards = mergedCards;
    interactiveCards
        .on("mouseenter", function () {
            d3.select(this).style("border-color", "var(--leaderboard-accent-start)");
        })
        .on("mouseleave", function () {
            if (!d3.select(this).classed("active")) {
                d3.select(this).style("border-color", "");
            }
        })
        .on("click", function (event, d) {
            container.selectAll(".scholar-card")
                .classed("active", false)
                .style("border-color", "");

            d3.select(this)
                .classed("active", true)
                .style("border-color", "var(--leaderboard-accent-start)");

            dispatcher.call("paperSelected", null, {
                title: d.name,
                summary: d.desc,
                prompt_type: "scholar_profile",
                year: "Career",
                venue: d.aff,
                citations: d.citations,
                concepts: d.tags,
                image: d.image,
                desc: d.desc,
                leaderboardView: mode
            });
        });

    enterCards.transition()
        .duration(600)
        .ease(d3.easeCubicOut)
        .delay((d, i) => i * 80)
        .style("opacity", 1)
        .style("transform", "translateY(0)");
}

function renderPapers(container, data, dispatcher, mode) {
    const maxCitations = d3.max(data, d => d.citations) || 1;

    const items = container.selectAll(".paper-item")
        .data(data, d => d.title);

    items.exit()
        .transition()
        .duration(200)
        .style("opacity", 0)
        .style("transform", "translateX(-20px)")
        .remove();

    const enterItems = items.enter()
        .append("div")
        .attr("class", "paper-item")
        .style("opacity", 0)
        .style("transform", "translateX(30px)");

    const row = enterItems.append("div").attr("class", "paper-row");
    row.append("div").attr("class", "paper-rank rank-num");
    const content = row.append("div").attr("class", "paper-content");
    content.append("div").attr("class", "paper-title");
    content.append("div").attr("class", "paper-meta");
    row.append("div").attr("class", "paper-cite-box");

    enterItems.append("div")
        .attr("class", "progress-bar-container")
        .append("div")
        .attr("class", "progress-bar-fill");

    const mergedItems = enterItems.merge(items);

    mergedItems.select(".paper-rank").text(d => d.rank);

    mergedItems.select(".paper-title")
        .text(d => d.title)
        .attr("title", d => d.title);

    mergedItems.select(".paper-meta")
        .text(d => {
            const venue = d.venue || "";
            const year = d.year || "";
            const author = (d.authors || "").split(",")[0] || "";
            return `${venue} · ${year} · ${author} et al.`;
        });

    mergedItems.select(".paper-cite-box")
        .text("0")
        .transition()
        .duration(1600)
        .ease(d3.easeCircleOut)
        .delay((d, i) => i * 100)
        .tween("text", function (d) {
            const interp = d3.interpolateNumber(0, d.citations || 0);
            return function (t) {
                d3.select(this).text(d3.format(",")(Math.round(interp(t))));
            };
        });

    mergedItems.select(".progress-bar-fill")
        .interrupt()
        .style("width", "0%")
        .transition()
        .duration(1200)
        .ease(d3.easeCubicOut)
        .delay((d, i) => i * 60 + 200)
        .style("width", d => `${((d.citations || 0) / maxCitations) * 100}%`);

    mergedItems
        .on("click", function (event, d) {
            container.selectAll(".paper-item").classed("active", false);
            d3.select(this).classed("active", true);

            dispatcher.call("paperSelected", null, {
                title: d.title,
                prompt_type: "paper_impact",
                year: d.year,
                venue: d.venue,
                citations: d.citations,
                authors: d.authors,
                leaderboardView: mode
            });
        });

    enterItems.transition()
        .duration(600)
        .ease(d3.easeCubicOut)
        .delay((d, i) => i * 60 + 200)
        .style("opacity", 1)
        .style("transform", "translateX(0)");
}
