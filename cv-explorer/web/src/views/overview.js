// web/src/views/overview.js
export function renderOverview(container, state, dispatcher) {
    const summary = state.summary;

    if (!summary?.yearly) {
        container.append('div')
            .attr('class', 'empty-state')
            .text('缺少 summary 数据，无法渲染概览视图。');
        return;
    }

    const yearlyData = Object.entries(summary.yearly)
        .map(([year, metrics]) => ({ year: +year, count: metrics.count, cites: metrics.cites }))
        .sort((a, b) => a.year - b.year);

    if (!yearlyData.length) {
        container.append('div')
            .attr('class', 'empty-state')
            .text('暂未找到年份级别数据。');
        return;
    }

    const years = yearlyData.map(d => d.year);
    const yearlyLookup = new Map(yearlyData.map(entry => [entry.year, entry]));
    let selectedYear = years.includes(state.filters?.year) ? state.filters.year : years[years.length - 1];

    const layout = container.append('div').attr('class', 'overview-grid');
    const controlPanel = layout.append('div').attr('class', 'panel overview-controls');
    const trendPanel = layout.append('div').attr('class', 'panel overview-trend');
    const insightPanel = layout.append('div').attr('class', 'panel overview-insights');

    controlPanel.append('h2').text('筛选面板');
    controlPanel.append('p').text('选择年份可同步到其他视图，快速观察该年度的热点走势。');

    const sliderBlock = controlPanel.append('div').attr('class', 'control-block');
    sliderBlock.append('label').text('年份').attr('for', 'overview-year-range');
    const sliderValue = sliderBlock.append('div').attr('class', 'control-value').text(selectedYear);
    const sliderInput = sliderBlock.append('input')
        .attr('type', 'range')
        .attr('min', years[0])
        .attr('max', years[years.length - 1])
        .attr('step', 1)
        .attr('value', selectedYear)
        .attr('id', 'overview-year-range')
        .on('input', event => {
            selectedYear = +event.target.value;
            sliderValue.text(selectedYear);
            updateInsights(selectedYear);
            updateFocus(selectedYear);
            dispatcher.call('viewUpdate', sliderBlock.node(), { source: 'overview', year: selectedYear });
        });

    const formatNumber = d3.format(',');
    const signedPercentFormatter = d3.format('+.1f');
    const percentFormatter = d3.format('.1f');

    const metricMeta = [
        { id: 'count', label: '年度论文数', subtitle: '全部 CV 顶会' },
        { id: 'cites', label: '年度引用数', subtitle: '累计引用' }
    ];

    const metricCardSelection = controlPanel.append('div')
        .attr('class', 'metric-cards')
        .selectAll('.metric-card')
        .data(metricMeta)
        .join('div')
        .attr('class', 'metric-card');

    metricCardSelection.append('div').attr('class', 'metric-label').text(d => d.label);
    metricCardSelection.append('div').attr('class', 'metric-value');
    metricCardSelection.append('div').attr('class', 'metric-delta');
    metricCardSelection.append('div').attr('class', 'metric-subtitle').text(d => d.subtitle);

    const chartWidth = trendPanel.node().clientWidth || 800;
    const chartHeight = Math.max(300, trendPanel.node().clientHeight || 360);
    const margin = { top: 32, right: 70, bottom: 40, left: 56 };
    const innerWidth = chartWidth - margin.left - margin.right;
    const innerHeight = chartHeight - margin.top - margin.bottom;

    const svg = trendPanel.append('svg')
        .attr('viewBox', `0 0 ${chartWidth} ${chartHeight}`)
        .attr('preserveAspectRatio', 'xMidYMid meet');

    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
        .attr('id', 'count-gradient')
        .attr('x1', '0%')
        .attr('x2', '0%')
        .attr('y1', '0%')
        .attr('y2', '100%');

    gradient.append('stop').attr('offset', '0%').attr('stop-color', 'rgba(56, 189, 248, 0.35)');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', 'rgba(15, 118, 110, 0.1)');

    const chartGroup = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
    const x = d3.scaleLinear().domain(d3.extent(yearlyData, d => d.year)).range([0, innerWidth]);
    const yCount = d3.scaleLinear().domain([0, d3.max(yearlyData, d => d.count) * 1.1]).range([innerHeight, 0]);
    const yCites = d3.scaleLinear().domain([0, d3.max(yearlyData, d => d.cites) * 1.1]).range([innerHeight, 0]);

    const area = d3.area()
        .x(d => x(d.year))
        .y0(innerHeight)
        .y1(d => yCount(d.count))
        .curve(d3.curveCatmullRom.alpha(0.5));

    const citeLine = d3.line()
        .x(d => x(d.year))
        .y(d => yCites(d.cites))
        .curve(d3.curveCatmullRom.alpha(0.5));

    chartGroup.append('path')
        .datum(yearlyData)
        .attr('class', 'count-area')
        .attr('d', area);

    chartGroup.append('path')
        .datum(yearlyData)
        .attr('class', 'cite-line')
        .attr('d', citeLine);

    chartGroup.append('g')
        .attr('class', 'axis axis-x')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(yearlyData.length).tickFormat(d3.format('d')));

    chartGroup.append('g')
        .attr('class', 'axis axis-y')
        .call(d3.axisLeft(yCount).ticks(5).tickFormat(d3.format('~s')))
        .append('text')
        .attr('class', 'axis-label')
        .attr('x', 0)
        .attr('y', -16)
        .text('论文数');

    chartGroup.append('g')
        .attr('class', 'axis axis-y axis-y-secondary')
        .attr('transform', `translate(${innerWidth},0)`)
        .call(d3.axisRight(yCites).ticks(5).tickFormat(d3.format('~s')))
        .append('text')
        .attr('class', 'axis-label')
        .attr('x', 0)
        .attr('y', -16)
        .text('引用数');

    const focusLine = chartGroup.append('line')
        .attr('class', 'focus-line')
        .attr('y1', 0)
        .attr('y2', innerHeight);

    const focusDots = {
        count: chartGroup.append('circle')
            .attr('class', 'focus-dot focus-dot-count')
            .attr('r', 4)
            .attr('opacity', 0),
        cites: chartGroup.append('circle')
            .attr('class', 'focus-dot focus-dot-cites')
            .attr('r', 4)
            .attr('opacity', 0)
    };

    const tooltip = trendPanel.append('div').attr('class', 'chart-tooltip hidden');

    svg.append('rect')
        .attr('class', 'chart-overlay')
        .attr('width', chartWidth)
        .attr('height', chartHeight)
        .attr('fill', 'transparent')
        .on('mousemove', event => {
            const [mx] = d3.pointer(event, chartGroup.node());
            const yearValue = x.invert(mx);
            const nearest = d3.least(yearlyData, d => Math.abs(d.year - yearValue));
            if (!nearest) return;
            showTooltip(nearest, event);
            updateFocus(nearest.year);
        })
        .on('mouseleave', () => {
            tooltip.classed('hidden', true);
            updateFocus(selectedYear);
        })
        .on('click', () => {
            if (tooltip.classed('hidden')) return;
            const textYear = tooltip.attr('data-year');
            if (textYear) {
                const newYear = +textYear;
                selectedYear = newYear;
                sliderInput.property('value', newYear);
                sliderValue.text(newYear);
                updateInsights(newYear);
                dispatcher.call('viewUpdate', sliderBlock.node(), { source: 'overview', year: newYear });
            }
        });

    function updateFocus(year) {
        const clampedYear = Math.max(years[0], Math.min(years[years.length - 1], year));
        const xPos = x(clampedYear);
        focusLine
            .attr('x1', xPos)
            .attr('x2', xPos);

        const entry = yearlyLookup.get(clampedYear);
        if (entry) {
            focusDots.count
                .attr('cx', xPos)
                .attr('cy', yCount(entry.count || 0))
                .attr('opacity', 1);
            focusDots.cites
                .attr('cx', xPos)
                .attr('cy', yCites(entry.cites || 0))
                .attr('opacity', 1);
        } else {
            focusDots.count.attr('opacity', 0);
            focusDots.cites.attr('opacity', 0);
        }
    }

    function showTooltip(entry, event) {
        const [mx, my] = d3.pointer(event, trendPanel.node());
        const countDelta = getMetricDelta(entry.year, 'count');
        const citeDelta = getMetricDelta(entry.year, 'cites');
        tooltip
            .classed('hidden', false)
            .style('left', `${mx + 12}px`)
            .style('top', `${my}px`)
            .attr('data-year', entry.year)
            .html(`
                <strong>${entry.year}</strong>
                <div>论文数：${formatNumber(entry.count)}
                    <span class="${deltaClass(countDelta)}">${formatDeltaCompact(countDelta)}</span>
                </div>
                <div>引用数：${formatNumber(entry.cites)}
                    <span class="${deltaClass(citeDelta)}">${formatDeltaCompact(citeDelta)}</span>
                </div>
            `);
    }

    function updateInsights(year) {
        const venueData = Object.entries(summary.venues || {})
            .map(([venue, counts]) => ({ venue, value: counts[year] || 0 }))
            .filter(d => d.value > 0)
            .sort((a, b) => b.value - a.value)
            .slice(0, 4);

        const keywordEntries = summary.keywords?.[year] || {};
        const keywordData = Object.entries(keywordEntries)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8);

        const venueItems = venueList.selectAll('.insight-item')
            .data(venueData, d => d.venue)
            .join(enter => {
                const block = enter.append('div').attr('class', 'insight-item');
                block.append('span').attr('class', 'insight-label');
                block.append('span').attr('class', 'insight-value');
                return block;
            });

        venueItems.select('.insight-label').text(d => d.venue);
        venueItems.select('.insight-value').text(d => formatNumber(d.value));

        keywordList.selectAll('li')
            .data(keywordData)
            .join('li')
            .text(d => `${d[0]} · ${formatNumber(d[1])}`);

        updateMetricCards(year);
        updateSnapshot(year, venueData, keywordData);
    }

    insightPanel.append('h2').text('亮点洞察');
    insightPanel.append('p').attr('class', 'insight-tip').text('自动提取该年的顶级会议产出与 Top 关键词。');

    const snapshotSection = insightPanel.append('div').attr('class', 'insight-block');
    snapshotSection.append('h3').text('年度快照');
    const snapshotCopy = snapshotSection.append('p').attr('class', 'insight-tip insight-snapshot');

    const venueSection = insightPanel.append('div').attr('class', 'insight-block');
    venueSection.append('h3').text('Top Venues');
    const venueList = venueSection.append('div').attr('class', 'insight-list');

    const keywordSection = insightPanel.append('div').attr('class', 'insight-block');
    keywordSection.append('h3').text('Top Keywords');
    const keywordList = keywordSection.append('ul').attr('class', 'keyword-list');

    function updateMetricCards(year) {
        metricCardSelection.each(function (meta) {
            const card = d3.select(this);
            const entry = yearlyLookup.get(year) || {};
            const value = entry[meta.id] || 0;
            const delta = getMetricDelta(year, meta.id);
            const deltaNode = card.select('.metric-delta');

            card.select('.metric-value').text(formatNumber(value));
            deltaNode
                .text(formatDeltaLabel(delta))
                .classed('negative', delta !== null && delta < 0)
                .classed('muted', delta === null);
        });
    }

    function updateSnapshot(year, venueData, keywordData) {
        if (!snapshotCopy) return;
        const entry = yearlyLookup.get(year) || {};
        const countDelta = getMetricDelta(year, 'count');
        const citeDelta = getMetricDelta(year, 'cites');
        const lines = [];

        lines.push(`${year} 年收录 ${formatNumber(entry.count || 0)} 篇论文${describeDelta(countDelta)}。`);
        lines.push(`累计引用 ${formatNumber(entry.cites || 0)} 次${describeDelta(citeDelta)}。`);

        if (venueData?.length) {
            lines.push(`${venueData[0].venue} 产出最高，达 ${formatNumber(venueData[0].value)} 篇。`);
        }

        if (keywordData?.length) {
            const [keyword, value] = keywordData[0];
            lines.push(`关键词 ${keyword} 热度最高（${formatNumber(value)} 次提及）。`);
        }

        snapshotCopy.text(lines.join(' '));
    }

    function getMetricDelta(year, key) {
        const current = yearlyLookup.get(year)?.[key] ?? 0;
        const prev = yearlyLookup.get(year - 1)?.[key];
        if (!prev) return null;
        const delta = ((current - prev) / prev) * 100;
        return Number.isFinite(delta) ? delta : null;
    }

    function formatDeltaLabel(value) {
        if (value === null) return '—';
        return `${signedPercentFormatter(value)}% YoY`;
    }

    function formatDeltaCompact(value) {
        if (value === null) return 'N/A';
        return `${signedPercentFormatter(value)}%`;
    }

    function deltaClass(value) {
        if (value === null) return 'delta-pill muted';
        return `delta-pill${value < 0 ? ' negative' : ''}`;
    }

    function describeDelta(value) {
        if (value === null) return '';
        const magnitude = percentFormatter(Math.abs(value));
        return `${value >= 0 ? '，同比增长 ' : '，同比下降 '}${magnitude}%`;
    }

    const externalHandler = payload => {
        if (payload?.year && payload.source !== 'overview') {
            selectedYear = payload.year;
            sliderInput.property('value', selectedYear);
            sliderValue.text(selectedYear);
            updateInsights(selectedYear);
            updateFocus(selectedYear);
        }
    };

    dispatcher.on('viewUpdate.overview', externalHandler);

    updateInsights(selectedYear);
    updateFocus(selectedYear);

    return () => dispatcher.on('viewUpdate.overview', null);
}