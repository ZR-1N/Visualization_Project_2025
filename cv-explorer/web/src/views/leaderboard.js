
export function renderLeaderboard(container, state, dispatcher) {
    // 1. Clear & Prepare
    container.html("");

    const data = state.leaderboard;
    if (!data) {
        container.append("div")
            .attr("class", "empty-state")
            .text("正在加载学术封神榜数据...");
        return;
    }

    const { scholars, papers } = data;

    // 2. Main Layout
    const layout = container.append("div").attr("class", "leaderboard-container");

    // --- Left Column: Scholars (Titans) ---
    const colScholars = layout.append("div").attr("class", "column-scholars");
    colScholars.append("h2")
        .html(`<span class="icon">👑</span> Academic Titans · 学术泰斗`);

    const scholarList = colScholars.append("div").attr("class", "card-list");
    renderScholars(scholarList, scholars, dispatcher);

    // --- Right Column: Papers (Classics) ---
    const colPapers = layout.append("div").attr("class", "column-papers");
    colPapers.append("h2")
        .html(`<span class="icon">📜</span> Classics · 镇山之作`);

    const paperList = colPapers.append("div").attr("class", "card-list");
    renderPapers(paperList, papers, dispatcher);
}

/**
 * Render Scholar Cards with Watermark & Staggered Animation
 */
function renderScholars(container, data, dispatcher) {
    const colorScale = d3.scaleOrdinal(d3.schemeTableau10);

    const cards = container.selectAll(".scholar-card")
        .data(data)
        .enter()
        .append("div")
        .attr("class", "scholar-card")
        .style("opacity", 0)
        .style("transform", "translateY(30px)");

    // Entrance Animation: Staggered Fade-in
    cards.transition()
        .duration(600)
        .ease(d3.easeCubicOut)
        .delay((d, i) => i * 100)
        .style("opacity", 1)
        .style("transform", "translateY(0)");

    // Interactions
    cards.on("mouseenter", function () {
        d3.select(this).style("border-color", "var(--accent-color)");
    }).on("mouseleave", function () {
        if (!d3.select(this).classed("active")) {
            d3.select(this).style("border-color", "");
        }
    });

    cards.on("click", function (event, d) {
        // Toggle Active Class
        container.selectAll(".scholar-card")
            .classed("active", false)
            .style("border-color", "");

        d3.select(this)
            .classed("active", true)
            .style("border-color", "var(--accent-color)");

        // Dispatch Event
        dispatcher.call("paperSelected", null, {
            title: d.name,
            summary: d.desc,
            prompt_type: "scholar_profile",
            // Context
            year: "Career",
            venue: d.aff,
            citations: d.citations,
            concepts: d.tags,
            image: d.image
        });
    });

    // --- Card Content ---

    // Set initial styles immediately to prevent flash
    cards.style("opacity", 0)
        .style("transform", "translateY(30px)");

    // 1. Dynamic Rank Watermark
    cards.append("div")
        .attr("class", "rank-watermark")
        .text(d => d.rank);

    const inner = cards.append("div").attr("class", "card-inner");

    // 2. Avatar with Initial Fallback
    const avatarBox = inner.append("div").attr("class", "avatar-circle");
    avatarBox.each(function (d) {
        const el = d3.select(this);
        if (d.image) {
            el.append("img").attr("src", d.image).attr("alt", d.name);
        } else {
            // Initials
            const initials = d.name.split(" ")
                .map(n => n[0])
                .join("")
                .slice(0, 2)
                .toUpperCase();

            el.style("background-color", colorScale(d.name))
                .text(initials);
        }
    });

    // 3. Info Block
    const info = inner.append("div").attr("class", "info-col");

    const header = info.append("div").attr("class", "card-header");
    header.append("h3").text(d => d.name);
    header.append("div").attr("class", "aff").text(d => d.aff);

    // 3.5 Description
    info.append("div")
        .attr("class", "scholar-desc")
        .text(d => d.desc || "")
        .style("display", d => d.desc ? "block" : "none");

    // 4. Footer with Stats & Tags
    const footer = info.append("div").attr("class", "card-footer");

    footer.append("div").attr("class", "citations")
        .html(d => `<span class="label">Citations</span> ${d3.format(",")(d.citations)}`);

    const tagRow = footer.append("div").attr("class", "tags");
    tagRow.selectAll("span")
        .data(d => d.tags || [])
        .enter().append("span")
        .text(d => d);
}

/**
 * Render Paper Items with Energy Bar & Number Tween
 */
function renderPapers(container, data, dispatcher) {
    const maxCitations = d3.max(data, d => d.citations) || 100000;

    const items = container.selectAll(".paper-item")
        .data(data)
        .enter()
        .append("div")
        .attr("class", "paper-item")
        .style("opacity", 0)
        .style("transform", "translateX(20px)");

    // Entrance Animation
    items.transition()
        .duration(600)
        .ease(d3.easeCubicOut)
        .delay((d, i) => i * 80 + 300) // Delay after scholars start
        .style("opacity", 1)
        .style("transform", "translateX(0)");

    // Interactions
    items.on("click", function (event, d) {
        container.selectAll(".paper-item").classed("active", false);
        d3.select(this).classed("active", true);

        dispatcher.call("paperSelected", null, {
            title: d.title,
            prompt_type: "paper_impact",
            year: d.year,
            venue: d.venue,
            citations: d.citations,
            authors: d.authors
        });
    });

    // --- Item Content ---
    // Set initial styles immediately to prevent flash
    items.style("opacity", 0)
        .style("transform", "translateX(20px)");

    const row = items.append("div").attr("class", "paper-row");

    // 1. Rank
    row.append("div")
        .attr("class", "paper-rank")
        .text(d => d.rank);

    // 2. Metadata
    const content = row.append("div").attr("class", "paper-content");
    content.append("div")
        .attr("class", "paper-title")
        .text(d => d.title)
        .attr("title", d => d.title);

    content.append("div")
        .attr("class", "paper-meta")
        .text(d => `${d.venue} · ${d.year} · ${d.authors.split(",")[0]} et al.`);

    // 3. Citation Counter (Tween Animation)
    const citeBox = row.append("div").attr("class", "paper-cite-box");

    citeBox.transition()
        .duration(2000)
        .ease(d3.easeCircleOut)
        .delay((d, i) => i * 100 + 500)
        .tween("text", function (d) {
            const node = d3.select(this);
            const interpolator = d3.interpolateNumber(0, d.citations);
            return function (t) {
                node.text(d3.format(",")(Math.round(interpolator(t))));
            };
        });

    // 4. Energy Bar (Progress Animation)
    const barContainer = items.append("div").attr("class", "progress-bar-container");
    const bar = barContainer.append("div").attr("class", "progress-bar-fill");

    bar.style("width", "0%")
        .transition()
        .duration(1200)
        .ease(d3.easeCubicOut)
        .delay((d, i) => i * 50 + 800)
        .style("width", d => `${(d.citations / maxCitations) * 100}%`);
}
