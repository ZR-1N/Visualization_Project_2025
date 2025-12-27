// web/src/views/flow.js
import { sankey as d3Sankey, sankeyCenter, sankeyLinkHorizontal } from 'https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/+esm';

export function renderFlow(container, state, dispatcher) {
    const rawLinks = (state.sankey || [])
        .map(d => ({
            source: d.source,
            target: d.target,
            value: +d.value || 0,
            year: d.year != null ? +d.year : null
        }))
        .filter(d => d.source && d.target && d.value > 0);

    if (!rawLinks.length) {
        container.append('div').attr('class', 'empty-state').text('缺少 sankey 数据。');
        return;
    }

    const problemOptions = Array.from(new Set(rawLinks.map(d => d.source))).sort((a, b) => a.localeCompare(b));
    const methodOptions = Array.from(new Set(rawLinks.map(d => d.target))).sort((a, b) => a.localeCompare(b));
    const hasYearField = rawLinks.some(d => Number.isFinite(d.year));
    const years = hasYearField
        ? Array.from(new Set(rawLinks.map(d => d.year).filter(y => Number.isFinite(y)))).sort((a, b) => a - b)
        : [];
    const linkKey = (source, target) => `${source}__${target}`;

    let selectedYear = hasYearField
        ? (years.includes(state.filters?.year) ? state.filters.year : years[years.length - 1])
        : 'ALL';
    if (hasYearField && selectedYear !== 'ALL' && !years.includes(selectedYear)) {
        selectedYear = years[years.length - 1];
    }
    let focusProblem = 'ALL';
    let focusMethod = 'ALL';
    let searchTerm = '';
    let yearSlider = null;
    let yearValueLabel = null;
    let playButton = null;
    let allYearsButton = null;
    let playTimer = null;
    let isPlaying = false;
    let lastYearValue = typeof selectedYear === 'number' ? selectedYear : (hasYearField ? years[years.length - 1] : null);
    let highlightedLink = null;
    let lastRenderedLinks = [];

    const layout = container.append('div').attr('class', 'flow-layout');
    const controlPanel = layout.append('div').attr('class', 'panel flow-controls');
    const stagePanel = layout.append('div').attr('class', 'panel flow-stage');

    controlPanel.append('h2').text('研究流向');
    controlPanel.append('p')
        .attr('class', 'flow-tip')
        .text('左侧筛选问题域 / 方法族或搜索关键字，右侧桑基图支持拖拽缩放。');

    const filterGroup = controlPanel.append('div').attr('class', 'flow-control-stack');

    if (hasYearField) {
        const timelineBlock = filterGroup.append('div').attr('class', 'flow-control-group flow-timeline-control');
        timelineBlock.append('label').text('时间轴 / 播放');
        const timelineRow = timelineBlock.append('div').attr('class', 'flow-timeline-row');
        playButton = timelineRow.append('button')
            .attr('class', 'flow-button tiny')
            .text('▶ 播放')
            .on('click', () => togglePlayback());

        const sliderWrapper = timelineRow.append('div').attr('class', 'flow-timeline-slider');
        yearSlider = sliderWrapper.append('input')
            .attr('type', 'range')
            .attr('min', years[0])
            .attr('max', years[years.length - 1])
            .attr('step', 1)
            .attr('value', typeof selectedYear === 'number' ? selectedYear : years[years.length - 1])
            .on('input', event => {
                stopPlayback();
                setYear(+event.target.value);
            });

        yearValueLabel = timelineRow.append('span')
            .attr('class', 'flow-timeline-value');

        allYearsButton = timelineBlock.append('button')
            .attr('class', 'flow-button ghost tiny flow-year-all-btn')
            .text('查看全周期')
            .on('click', () => {
                stopPlayback();
                setYear('ALL', { emit: false });
            });
    }

    if (hasYearField) {
        updateYearUI();
    }

    const problemBlock = filterGroup.append('div').attr('class', 'flow-control-group');
    problemBlock.append('label').text('问题域');
    const problemSelect = problemBlock.append('select')
        .attr('class', 'flow-select')
        .on('change', event => {
            focusProblem = event.target.value;
            draw();
        });
    problemSelect.append('option').attr('value', 'ALL').text('全部问题');
    problemSelect.selectAll('option.problem-option')
        .data(problemOptions)
        .join('option')
        .attr('class', 'problem-option')
        .attr('value', d => d)
        .text(d => d);

    const methodBlock = filterGroup.append('div').attr('class', 'flow-control-group');
    methodBlock.append('label').text('方法族');
    const methodSelect = methodBlock.append('select')
        .attr('class', 'flow-select')
        .on('change', event => {
            focusMethod = event.target.value;
            draw();
        });
    methodSelect.append('option').attr('value', 'ALL').text('全部方法');
    methodSelect.selectAll('option.method-option')
        .data(methodOptions)
        .join('option')
        .attr('class', 'method-option')
        .attr('value', d => d)
        .text(d => d);

    const searchBlock = filterGroup.append('div').attr('class', 'flow-control-group');
    searchBlock.append('label').text('关键字过滤');
    searchBlock.append('input')
        .attr('type', 'search')
        .attr('placeholder', '输入问题或方法...')
        .attr('class', 'flow-search')
        .on('input', event => {
            searchTerm = event.target.value.trim().toLowerCase();
            draw();
        });

    const resetRow = controlPanel.append('div').attr('class', 'flow-reset-row');
    resetRow.append('button')
        .attr('class', 'flow-button ghost')
        .text('重置筛选')
        .on('click', () => {
            focusProblem = 'ALL';
            focusMethod = 'ALL';
            searchTerm = '';
            problemSelect.property('value', 'ALL');
            methodSelect.property('value', 'ALL');
            searchBlock.select('input').property('value', '');
            highlightLink(null, null);
            draw();
        });

    const legendSection = controlPanel.append('div').attr('class', 'flow-control-group');
    legendSection.append('label').text('方法族配色');
    const legend = legendSection.append('div').attr('class', 'flow-legend');

    const summarySection = controlPanel.append('div').attr('class', 'flow-summary');
    summarySection.append('h3').text('Top 流向');
    const summaryList = summarySection.append('div').attr('class', 'flow-summary-list');

    const tooltip = stagePanel.append('div').attr('class', 'chart-tooltip hidden');
    const statusBar = stagePanel.append('div').attr('class', 'flow-stage-status');
    const zoomControls = stagePanel.append('div').attr('class', 'flow-zoom-controls');
    const zoomInBtn = zoomControls.append('button').attr('class', 'flow-button').text('+');
    const zoomOutBtn = zoomControls.append('button').attr('class', 'flow-button').text('−');
    const zoomResetBtn = zoomControls.append('button').attr('class', 'flow-button ghost').text('重置');

    const svg = stagePanel.append('svg')
        .attr('class', 'flow-chart');

    const rootGroup = svg.append('g').attr('class', 'flow-root');
    const linkGroup = rootGroup.append('g').attr('class', 'flow-links');
    const nodeGroup = rootGroup.append('g').attr('class', 'flow-nodes');

    const color = d3.scaleOrdinal()
        .domain(methodOptions)
        .range(d3.schemeTableau10.concat(['#f97316', '#a855f7', '#14b8a6', '#facc15', '#f472b6']));

    legend.selectAll('span')
        .data(methodOptions)
        .join('span')
        .attr('class', 'legend-item')
        .style('border-color', d => color(d))
        .text(d => d);

    const valueFormatter = d3.format(',.0f');
    const zoomFormatter = d3.format('.0%');

    let currentTransform = d3.zoomIdentity;

    const zoomBehavior = d3.zoom()
        .scaleExtent([0.6, 2.5])
        .on('zoom', event => {
            currentTransform = event.transform;
            rootGroup.attr('transform', currentTransform);
            zoomControls.attr('data-zoom', zoomFormatter(currentTransform.k));
        });

    svg.call(zoomBehavior);

    zoomInBtn.on('click', () => svg.transition().duration(220).call(zoomBehavior.scaleBy, 1.2));
    zoomOutBtn.on('click', () => svg.transition().duration(220).call(zoomBehavior.scaleBy, 0.8));
    zoomResetBtn.on('click', () => svg.transition().duration(220).call(zoomBehavior.transform, d3.zoomIdentity));

    const resizeObserver = new ResizeObserver(() => draw());
    resizeObserver.observe(stagePanel.node());

    const percentFormatter = d3.format('+.0%');

    function getPrevYear(year) {
        if (!hasYearField || year === 'ALL') return null;
        const idx = years.indexOf(year);
        return idx > 0 ? years[idx - 1] : null;
    }

    function formatYoy(yoy, isNew = false) {
        if (isNew) return '新流向';
        if (!Number.isFinite(yoy)) return '—';
        const formatted = percentFormatter(yoy);
        return formatted === '+0%' ? '0%' : formatted;
    }

    function trendClass(yoy, isNew = false) {
        if (isNew) return 'new';
        if (!Number.isFinite(yoy)) return 'muted';
        if (yoy < 0) return 'negative';
        if (yoy < 0.08) return 'muted';
        return 'positive';
    }

    function linkOpacity(d) {
        const prevYear = getPrevYear(selectedYear);
        if (!hasYearField || selectedYear === 'ALL' || prevYear == null) return 0.35;
        if (d.isNew) return 0.65;
        if (!Number.isFinite(d.yoy)) return 0.4;
        return d.yoy >= 0 ? 0.55 : 0.25;
    }

    function linkMatchesHighlight(d) {
        if (!highlightedLink) return false;
        const sourceName = d.source?.name ?? d.source;
        const targetName = d.target?.name ?? d.target;
        return sourceName === highlightedLink.problem && targetName === highlightedLink.method;
    }

    function highlightLink(problem, method, { allowToggle = true } = {}) {
        if (!problem || !method) {
            highlightedLink = null;
        } else if (allowToggle && highlightedLink && highlightedLink.problem === problem && highlightedLink.method === method) {
            highlightedLink = null;
        } else {
            highlightedLink = { problem, method };
        }
        refreshLinkStates();
        refreshNodeStates();
        updateSummary(lastRenderedLinks);
    }

    function refreshLinkStates() {
        const hasHighlight = !!highlightedLink;
        const paths = linkGroup.selectAll('path.flow-link');
        paths
            .classed('is-highlighted', d => hasHighlight && linkMatchesHighlight(d))
            .classed('is-dimmed', d => hasHighlight && !linkMatchesHighlight(d))
            .attr('stroke-opacity', d => {
                if (!hasHighlight) return linkOpacity(d);
                return linkMatchesHighlight(d) ? 0.9 : 0.08;
            });
    }

    function refreshNodeStates() {
        const hasHighlight = !!highlightedLink;
        const nodes = nodeGroup.selectAll('.flow-node');
        nodes
            .classed('is-highlighted', d => hasHighlight && ((d.depth === 0 && d.name === highlightedLink.problem) || (d.depth > 0 && d.name === highlightedLink.method)))
            .classed('is-dimmed', d => {
                if (!hasHighlight) return false;
                if (d.depth === 0) return d.name !== highlightedLink.problem;
                return d.name !== highlightedLink.method;
            });
    }

    function updateYearUI() {
        if (!hasYearField) return;
        const isAll = selectedYear === 'ALL';
        if (yearSlider) {
            yearSlider.property('disabled', isAll);
            const sliderValue = (isAll ? lastYearValue : selectedYear) ?? years[years.length - 1];
            yearSlider.property('value', sliderValue);
        }
        if (yearValueLabel) {
            yearValueLabel.text(isAll ? '全周期' : `${selectedYear}`);
        }
        if (allYearsButton) {
            allYearsButton.classed('is-active', isAll);
        }
    }

    function setYear(value, { emit = true } = {}) {
        if (!hasYearField) return;
        let normalized = value;
        if (normalized !== 'ALL') {
            normalized = years.includes(normalized) ? normalized : years[years.length - 1];
        }
        if (selectedYear === normalized) {
            updateYearUI();
            return;
        }
        selectedYear = normalized;
        if (selectedYear !== 'ALL') {
            lastYearValue = selectedYear;
        }
        updateYearUI();
        draw();
        if (emit && selectedYear !== 'ALL') {
            dispatcher.call('viewUpdate', yearSlider?.node() || stagePanel.node(), { source: 'flow', year: selectedYear });
        }
    }

    function stopPlayback() {
        if (playTimer) {
            clearInterval(playTimer);
            playTimer = null;
        }
        isPlaying = false;
        playButton?.text('▶ 播放');
    }

    function togglePlayback() {
        if (!hasYearField) return;
        if (isPlaying) {
            stopPlayback();
            return;
        }
        if (selectedYear === 'ALL') {
            setYear(lastYearValue ?? years[0], { emit: false });
        }
        isPlaying = true;
        playButton?.text('⏸ 暂停');
        playTimer = setInterval(() => {
            const current = typeof selectedYear === 'number' ? selectedYear : (lastYearValue ?? years[0]);
            const idx = years.indexOf(current);
            const nextIdx = (idx + 1) % years.length;
            setYear(years[nextIdx]);
        }, 1800);
    }

    function filterRawLinks(yearCriterion = selectedYear) {
        let filtered = rawLinks;
        if (hasYearField && yearCriterion !== 'ALL') {
            filtered = filtered.filter(d => d.year === yearCriterion);
        }
        if (focusProblem !== 'ALL') {
            filtered = filtered.filter(d => d.source === focusProblem);
        }
        if (focusMethod !== 'ALL') {
            filtered = filtered.filter(d => d.target === focusMethod);
        }
        if (searchTerm) {
            filtered = filtered.filter(d => `${d.source}`.toLowerCase().includes(searchTerm) || `${d.target}`.toLowerCase().includes(searchTerm));
        }
        return filtered;
    }

    function rollupLinks(list) {
        return d3.flatRollup(
            list,
            v => d3.sum(v, d => d.value),
            d => d.source,
            d => d.target
        ).map(([source, target, value]) => ({ source, target, value }));
    }

    function buildLinks(filteredRaw = null) {
        const base = filteredRaw ?? filterRawLinks();
        const rolled = rollupLinks(base);
        if (hasYearField && selectedYear !== 'ALL') {
            const prevYear = getPrevYear(selectedYear);
            const prevMap = prevYear != null
                ? new Map(rollupLinks(filterRawLinks(prevYear)).map(d => [linkKey(d.source, d.target), d.value]))
                : null;
            return rolled.map(link => {
                const key = linkKey(link.source, link.target);
                const prevValue = prevMap?.get(key) ?? 0;
                const yoy = prevValue > 0 ? (link.value - prevValue) / prevValue : null;
                const isNew = prevMap != null && prevValue === 0 && link.value > 0;
                return { ...link, prevValue, yoy, isNew };
            });
        }
        return rolled.map(link => ({ ...link, prevValue: null, yoy: null, isNew: false }));
    }

    function draw() {
        const filteredRaw = filterRawLinks();
        const filteredLinks = buildLinks(filteredRaw);
        lastRenderedLinks = filteredLinks;
        if (highlightedLink && !filteredLinks.some(d => d.source === highlightedLink.problem && d.target === highlightedLink.method)) {
            highlightedLink = null;
        }
        const problems = new Set(filteredLinks.map(d => d.source));
        const methods = new Set(filteredLinks.map(d => d.target));
        const countSummary = `显示 ${problems.size || 0} 个问题 → ${methods.size || 0} 个方法 (${filteredLinks.length} 条关系)`;
        const totalValue = d3.sum(filteredRaw, d => d.value);
        const prevYear = getPrevYear(selectedYear);
        const prevTotal = prevYear != null ? d3.sum(filterRawLinks(prevYear), d => d.value) : null;
        const yearLabel = selectedYear === 'ALL' ? '全周期汇总' : `${selectedYear} 年`;
        let statusHtml = `<strong>${yearLabel}</strong> · ${countSummary} · 影响力 ${valueFormatter(totalValue)}`;
        if (prevYear != null) {
            const yoy = prevTotal > 0 ? (totalValue - prevTotal) / prevTotal : null;
            statusHtml += ` <span class="delta-pill ${trendClass(yoy, prevTotal === 0)}">${formatYoy(yoy, prevTotal === 0)}</span>`;
        }
        statusBar.html(statusHtml);

        stagePanel.selectAll('.empty-state').remove();
        if (!filteredLinks.length) {
            linkGroup.selectAll('*').remove();
            nodeGroup.selectAll('*').remove();
            stagePanel.append('div').attr('class', 'empty-state').text('筛选条件下暂无路径。');
            updateSummary([]);
            return;
        }

        const bounds = stagePanel.node().getBoundingClientRect();
        const width = bounds.width || 960;
        const dynamicHeight = Math.max(bounds.height, Math.max(problems.size, methods.size) * 42 + 160);

        svg
            .attr('width', width)
            .attr('height', dynamicHeight)
            .attr('viewBox', `0 0 ${width} ${dynamicHeight}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const sankey = d3Sankey()
            .nodeId(d => d.name)
            .nodeWidth(18)
            .nodePadding(22)
            .nodeAlign(sankeyCenter)
            .extent([[0, 0], [width, dynamicHeight - 40]]);

        const nodes = Array.from(new Set(filteredLinks.flatMap(d => [d.source, d.target])), name => ({ name }));
        const graph = sankey({
            nodes: nodes.map(d => ({ ...d })),
            links: filteredLinks.map(d => ({ ...d }))
        });

        const linksSel = linkGroup.selectAll('path.flow-link')
            .data(graph.links, d => `${d.source.name}-${d.target.name}`);

        linksSel.join(
            enter => enter.append('path')
                .attr('class', 'flow-link')
                .attr('stroke', d => color(d.target.name))
                .attr('fill', 'none')
                .attr('stroke-opacity', d => linkOpacity(d))
                .attr('stroke-width', d => Math.max(1, d.width))
                .attr('d', sankeyLinkHorizontal())
                .attr('stroke-dasharray', d => d.isNew ? '6 3' : null)
                .classed('is-new', d => d.isNew)
                .style('cursor', 'pointer')
                .on('mouseenter', function () {
                    d3.select(this).attr('stroke-opacity', 0.85);
                })
                .on('mouseleave', function () {
                    tooltip.classed('hidden', true);
                    refreshLinkStates();
                })
                .on('mousemove', (event, d) => {
                    showTooltip(event, `${d.source.name} → ${d.target.name}`, d.value, {
                        year: selectedYear === 'ALL' ? null : selectedYear,
                        yoy: d.yoy,
                        isNew: d.isNew
                    });
                })
                .on('click', (event, d) => {
                    highlightLink(d.source.name, d.target.name);
                    const payload = {
                        source: 'flow',
                        problem: d.source.name,
                        method: d.target.name,
                        value: d.value
                    };
                    if (hasYearField && selectedYear !== 'ALL') payload.year = selectedYear;
                    dispatcher.call('viewUpdate', event.currentTarget, payload);
                    dispatcher.call('paperSelectedSync', event.currentTarget, {
                        label: `${d.source.name} → ${d.target.name}`,
                        value: d.value,
                        summary: '已聚合该流向相关论文，可在其他视图中进一步筛选。'
                    });
                }),
            update => update
                .classed('flow-link', true)
                .attr('stroke', d => color(d.target.name))
                .attr('stroke-width', d => Math.max(1, d.width))
                .attr('d', sankeyLinkHorizontal())
                .attr('stroke-opacity', d => linkOpacity(d))
                .attr('stroke-dasharray', d => d.isNew ? '6 3' : null)
                .classed('is-new', d => d.isNew),
            exit => exit.remove()
        );

        refreshLinkStates();

        const nodesSel = nodeGroup.selectAll('g')
            .data(graph.nodes, d => d.name)
            .join(enter => {
                const nodeEnter = enter.append('g').attr('class', 'flow-node');
                nodeEnter.append('rect')
                    .attr('rx', 3)
                    .style('cursor', 'pointer');
                nodeEnter.append('text')
                    .attr('class', 'node-label');
                return nodeEnter;
            });

        nodesSel.attr('transform', d => `translate(${d.x0},${d.y0})`);

        nodesSel.select('rect')
            .attr('height', d => Math.max(1, d.y1 - d.y0))
            .attr('width', d => d.x1 - d.x0)
            .attr('fill', d => (d.depth === 0 ? '#475569' : color(d.name)))
            .attr('opacity', d => (d.depth === 0 ? 0.65 : 0.95))
            .on('mousemove', (event, d) => showTooltip(event, d.name, d.value, { year: selectedYear === 'ALL' ? null : selectedYear }))
            .on('mouseleave', () => tooltip.classed('hidden', true))
            .on('click', (event, d) => {
                const payload = {
                    source: 'flow',
                    role: d.depth === 0 ? 'problem' : 'method',
                    name: d.name
                };
                if (hasYearField && selectedYear !== 'ALL') payload.year = selectedYear;
                dispatcher.call('viewUpdate', event.currentTarget, payload);
            });

        nodesSel.select('text')
            .attr('x', d => (d.depth === 0 ? -10 : (d.x1 - d.x0) + 10))
            .attr('y', d => (d.y1 - d.y0) / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', d => (d.depth === 0 ? 'end' : 'start'))
            .text(d => d.name);

        rootGroup.attr('transform', currentTransform);

        refreshNodeStates();
        updateSummary(filteredLinks);
    }

    function showTooltip(event, title, value, meta = {}) {
        const [mx, my] = d3.pointer(event, stagePanel.node());
        let html = `
            <strong>${title}</strong>
            <div>影响力：${valueFormatter(value)}</div>
        `;
        if (meta.year && meta.year !== 'ALL') {
            html += `<div>年份：${meta.year}</div>`;
        }
        if (meta && (meta.isNew || Number.isFinite(meta.yoy))) {
            html += `<div><span class="delta-pill ${trendClass(meta.yoy, meta.isNew)}">${formatYoy(meta.yoy, meta.isNew)}</span></div>`;
        }
        tooltip
            .classed('hidden', false)
            .style('left', `${mx + 14}px`)
            .style('top', `${my + 14}px`)
            .html(html);
    }

    function updateSummary(data) {
        const topLinks = data
            .slice()
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);

        const items = summaryList.selectAll('.flow-summary-item')
            .data(topLinks, d => `${d.source}-${d.target}`);

        const enter = items.enter().append('div').attr('class', 'flow-summary-item');
        enter.append('div').attr('class', 'flow-summary-title');
        enter.append('div').attr('class', 'flow-summary-value');

        const canShowTrend = hasYearField && selectedYear !== 'ALL' && getPrevYear(selectedYear) != null;

        items.merge(enter)
            .attr('tabindex', 0)
            .style('cursor', 'pointer')
            .on('click', (_, d) => highlightLink(d.source, d.target))
            .on('keydown', (event, d) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    highlightLink(d.source, d.target);
                }
            })
            .select('.flow-summary-title')
            .html(d => {
                const base = `${d.source} → ${d.target}`;
                if (!canShowTrend || (!d.isNew && !Number.isFinite(d.yoy))) {
                    return base;
                }
                return `
                    <span>${base}</span>
                    <span class="delta-pill ${trendClass(d.yoy, d.isNew)}">${formatYoy(d.yoy, d.isNew)}</span>
                `;
            });

        items.merge(enter)
            .select('.flow-summary-value')
            .text(d => valueFormatter(d.value));

        items.merge(enter)
            .classed('is-highlighted', d => highlightedLink && d.source === highlightedLink.problem && d.target === highlightedLink.method)
            .classed('is-dimmed', d => highlightedLink && !(d.source === highlightedLink.problem && d.target === highlightedLink.method));

        items.exit().remove();
        summaryList.selectAll('.flow-summary-empty').remove();
        if (!topLinks.length) {
            summaryList.append('div').attr('class', 'flow-summary-empty').text('暂无流向数据');
        }
    }

    const externalHandler = payload => {
        if (payload?.year && payload.source !== 'flow' && hasYearField) {
            if (payload.year === 'ALL') {
                setYear('ALL', { emit: false });
            } else if (years.includes(payload.year)) {
                stopPlayback();
                setYear(payload.year, { emit: false });
            }
        }
        if (payload?.problem && payload?.method && payload.source !== 'flow') {
            highlightLink(payload.problem, payload.method, { allowToggle: false });
        }
        if (payload?.problem && payload.source !== 'flow') {
            focusProblem = payload.problem;
            problemSelect.property('value', focusProblem);
            draw();
        }
        if (payload?.method && payload.source !== 'flow') {
            focusMethod = payload.method;
            methodSelect.property('value', focusMethod);
            draw();
        }
    };

    dispatcher.on('viewUpdate.flow', externalHandler);

    draw();

    return () => {
        dispatcher.on('viewUpdate.flow', null);
        tooltip.remove();
        svg.remove();
        zoomControls.remove();
        statusBar.remove();
        resizeObserver.disconnect();
        stopPlayback();
        layout.remove();
    };
}