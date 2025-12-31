// web/src/views/word_cloud.js

const clusterDefs = [
    { id: 'frontier', label: '前沿热点', color: '#fbbf24', description: '高引用 · 稳定主导力量' },
    { id: 'growth', label: '高速增长', color: '#a855f7', description: '同比增速领跑' },
    { id: 'steady', label: '稳健主题', color: '#38bdf8', description: '动能回落或保持平稳' },
    { id: 'emerge', label: '萌芽方向', color: '#34d399', description: '新兴或小体量但在升温' }
];

const clusterColor = d3.scaleOrdinal()
    .domain(clusterDefs.map(d => d.id))
    .range(clusterDefs.map(d => d.color));

export function renderWordCloud(container, state, dispatcher) {
    const cloudFactory = window?.d3?.layout?.cloud;
    if (!cloudFactory) {
        container.append('div')
            .attr('class', 'empty-state')
            .text('词云布局库未加载，请检查网络或依赖。');
        return;
    }

    const dataset = state.wordcloud || {};
    const yearKeys = Object.keys(dataset);
    if (!yearKeys.length) {
        container.append('div')
            .attr('class', 'empty-state')
            .text('缺少关键词词云数据。');
        return;
    }

    const years = yearKeys.map(Number).sort((a, b) => a - b);
    let selectedYear = years.includes(state.filters?.year) ? state.filters.year : years[years.length - 1];
    let maxWords = 60;
    let minCitations = 0;
    let allowTilt = true;
    let selectedToken = null;
    let activeLayout = null;

    const allSizes = [];
    const yearWordLookup = new Map();
    yearKeys.forEach(year => {
        const list = dataset[year] || [];
        yearWordLookup.set(+year, new Map(list.filter(item => item?.text).map(item => [item.text, +item.size])));
        list.forEach(item => {
            if (item?.size != null) allSizes.push(+item.size);
        });
    });

    const globalMax = d3.max(allSizes) || 1;
    const globalMin = d3.min(allSizes) || 0;
    const formatNumber = d3.format(',');
    const formatPercent = d3.format('+.0%');

    const layout = container.append('div').attr('class', 'wordcloud-layout');
    const controlPanel = layout.append('div').attr('class', 'panel wordcloud-controls');
    const stagePanel = layout.append('div').attr('class', 'panel wordcloud-stage');
    const insightPanel = layout.append('div').attr('class', 'panel wordcloud-insight');

    controlPanel.append('h2').text('关键词词云');
    controlPanel.append('p')
        .attr('class', 'wordcloud-tip')
        .text('根据年份引用权重筛选关键词，观察主题集群与热度变化。');

    const yearBlock = controlPanel.append('div').attr('class', 'wordcloud-control');
    yearBlock.append('label').text('年份');
    const yearValue = yearBlock.append('div').attr('class', 'wordcloud-control-value').text(selectedYear);
    const yearSliderWrap = yearBlock.append('div').attr('class', 'wordcloud-slider');
    const yearSlider = yearSliderWrap.append('input')
        .attr('type', 'range')
        .attr('min', years[0])
        .attr('max', years[years.length - 1])
        .attr('step', 1)
        .attr('value', selectedYear)
        .on('input', event => {
            selectedYear = +event.target.value;
            yearValue.text(selectedYear);
            dispatcher.call('viewUpdate', yearSlider.node(), { source: 'wordcloud', year: selectedYear });
            runLayout();
        });

    const countBlock = controlPanel.append('div').attr('class', 'wordcloud-control');
    countBlock.append('label').text('可视关键词');
    const countValue = countBlock.append('div').attr('class', 'wordcloud-control-value').text(maxWords);
    const countSliderWrap = countBlock.append('div').attr('class', 'wordcloud-slider');
    countSliderWrap.append('input')
        .attr('type', 'range')
        .attr('min', 20)
        .attr('max', 120)
        .attr('step', 5)
        .attr('value', maxWords)
        .on('input', event => {
            maxWords = +event.target.value;
            countValue.text(maxWords);
            runLayout();
        });

    const citationBlock = controlPanel.append('div').attr('class', 'wordcloud-control');
    citationBlock.append('label').text('引用阈值');
    const citationValue = citationBlock.append('div').attr('class', 'wordcloud-control-value').text(formatNumber(minCitations));
    const citationSliderWrap = citationBlock.append('div').attr('class', 'wordcloud-slider');
    citationSliderWrap.append('input')
        .attr('type', 'range')
        .attr('min', globalMin)
        .attr('max', globalMax)
        .attr('step', Math.max(50, Math.round(globalMax / 200)))
        .attr('value', minCitations)
        .on('input', event => {
            minCitations = +event.target.value;
            citationValue.text(formatNumber(minCitations));
            runLayout();
        });

    const toggleRow = controlPanel.append('label').attr('class', 'wordcloud-toggle');
    toggleRow.append('input')
        .attr('type', 'checkbox')
        .property('checked', allowTilt)
        .on('change', event => {
            allowTilt = event.target.checked;
            runLayout();
        });
    toggleRow.append('span').text('允许倾斜排布');

    const controlButtons = controlPanel.append('div').attr('class', 'wordcloud-button-row');
    controlButtons.append('button')
        .attr('class', 'wordcloud-button')
        .text('重新排布')
        .on('click', () => runLayout());

    const stageBadge = stagePanel.append('div').attr('class', 'wordcloud-stage-status');
    const loader = stagePanel.append('div').attr('class', 'wordcloud-loading hidden').text('布局计算中...');
    const tooltip = stagePanel.append('div').attr('class', 'chart-tooltip hidden wordcloud-tooltip');
    const svg = stagePanel.append('svg').attr('class', 'wordcloud-svg');
    const wordGroup = svg.append('g').attr('class', 'wordcloud-group');

    const insightTip = insightPanel.append('h2').text('AI 关键词解读');
    insightPanel.append('p').attr('class', 'wordcloud-tip').text('点击词语并将其发送到 AI 助手，后续可接入 LLM 接口。');
    const insightCard = insightPanel.append('div').attr('class', 'wordcloud-ai-card');
    const insightTitle = insightCard.append('h3').text('等待选择');
    const insightMeta = insightCard.append('p').attr('class', 'ai-meta').text('—');
    const insightText = insightCard.append('p').attr('class', 'wordcloud-ai-text').text('从词云中选择任意关键词，即可生成上下文提示。');

    const legend = controlPanel.append('div').attr('class', 'wordcloud-legend');
    legend.selectAll('.wordcloud-legend-item')
        .data(clusterDefs)
        .join('div')
        .attr('class', 'wordcloud-legend-item')
        .html(d => `
            <span class="swatch" style="background:${d.color}"></span>
            <div>
                <strong>${d.label}</strong>
                <small>${d.description}</small>
            </div>
        `);

    const rankingBlock = insightPanel.append('div').attr('class', 'wordcloud-ranking');
    rankingBlock.append('h3').text('Top 5 热词');
    const rankingList = rankingBlock.append('ol').attr('class', 'wordcloud-ranking-list');
    const rankingEmpty = rankingBlock.append('div').attr('class', 'wordcloud-ranking-empty').text('暂无关键词，试着降低阈值。');

    const ro = new ResizeObserver(() => runLayout());
    ro.observe(stagePanel.node());

    function prepareWords() {
        const raw = (dataset[selectedYear] || []).filter(d => d?.text);
        if (!raw.length) return [];

        const sorted = raw.slice().sort((a, b) => b.size - a.size);
        const filtered = sorted.filter(d => d.size >= minCitations).slice(0, maxWords);
        if (!filtered.length) return [];

        const yearIndex = years.indexOf(selectedYear);
        const prevYear = yearIndex > 0 ? years[yearIndex - 1] : null;
        const prevMap = prevYear != null ? yearWordLookup.get(prevYear) : null;

        const minVal = d3.min(filtered, d => d.size);
        const maxVal = d3.max(filtered, d => d.size);
        const sizeValues = filtered.map(d => d.size);
        const highCut = d3.quantile(sizeValues, 0.7) || maxVal || 1;
        const lowCut = d3.quantile(sizeValues, 0.25) || minVal || 1;

        const fontScale = d3.scaleSqrt()
            .domain([Math.max(1, minVal || 1), maxVal || 1])
            .range([14, 78]);

        return filtered.map(item => {
            const prevValue = prevMap ? (prevMap.get(item.text) || 0) : 0;
            const hasPrevWindow = !!prevMap;
            const isNew = hasPrevWindow && prevValue === 0;
            const yoy = hasPrevWindow && prevValue > 0 ? (item.size - prevValue) / prevValue : null;
            return {
                text: item.text,
                value: item.size,
                prevValue,
                yoy,
                isNew,
                clusterId: classifyToken(item.size, yoy, isNew, highCut, lowCut),
                fontSize: fontScale(item.size)
            };
        });
    }

    function classifyToken(value, yoy, isNew, highCut, lowCut) {
        if (isNew) {
            return value >= highCut * 0.85 ? 'growth' : 'emerge';
        }

        const growth = Number.isFinite(yoy) ? yoy : 0;
        if (value >= highCut && growth >= -0.05) return 'frontier';
        if (growth >= 0.2) return 'growth';
        if (growth <= -0.15) return 'steady';
        if (value <= lowCut && growth <= 0.05) return 'emerge';
        return 'steady';
    }

    function formatTrendValue(yoy) {
        if (!Number.isFinite(yoy)) return '—';
        const formatted = formatPercent(yoy);
        return formatted === '+0%' ? '0%' : formatted;
    }

    function formatTrendText(yoy, isNew, options = {}) {
        const { withPrefix = true } = options;
        if (isNew) return '新出现';
        const base = formatTrendValue(yoy);
        if (base === '—') return '暂无同比';
        return withPrefix ? `YoY ${base}` : base;
    }

    function trendClass(yoy, isNew) {
        if (isNew) return 'new';
        if (!Number.isFinite(yoy)) return 'muted';
        if (yoy < 0) return 'negative';
        if (yoy < 0.08) return 'muted';
        return 'positive';
    }

    function runLayout() {
        const words = prepareWords();
        selectedToken = null;
        updateRanking(words);
        updateStageBadge(words);
        stagePanel.selectAll('.wordcloud-empty').remove();

        if (activeLayout) {
            activeLayout.stop();
            activeLayout = null;
        }

        if (!words.length) {
            wordGroup.selectAll('text').remove();
            loader.classed('hidden', true);
            stagePanel.append('div')
                .attr('class', 'empty-state wordcloud-empty')
                .text('当前筛选暂无关键词，尝试调整阈值或年份。');
            return;
        }

        loader.classed('hidden', false);
        const bounds = stagePanel.node().getBoundingClientRect();
        const width = Math.max(420, bounds.width);
        const height = Math.max(360, bounds.height);
        const verticalOffset = Math.min(8, Math.max(28, Math.round(height * 0.08)));
        svg
            .attr('width', width)
            .attr('height', height)
            .attr('viewBox', `0 0 ${width} ${height}`);

        const layoutWords = words.map(word => ({
            ...word,
            size: word.fontSize
        }));

        activeLayout = cloudFactory()
            .size([width, height])
            .words(layoutWords)
            .padding(3)
            .rotate(() => allowTilt ? (Math.random() > 0.7 ? 0 : (Math.random() > 0.5 ? 25 : -25)) : 0)
            .font('Space Grotesk')
            .fontSize(d => d.size)
            .on('end', placed => {
                drawWords(placed, width, height, verticalOffset);
                loader.classed('hidden', true);
                activeLayout = null;
            });

        activeLayout.start();
    }

    function drawWords(words, width, height, verticalOffset = 0) {
        const nodes = wordGroup.selectAll('text')
            .data(words, d => d.text);

        nodes.join(
            enter => enter.append('text')
                .attr('class', 'wordcloud-word')
                .attr('text-anchor', 'middle')
                .attr('font-size', d => d.size)
                .attr('fill', d => clusterColor(d.clusterId))
                .attr('data-cluster', d => d.clusterId)
                .attr('opacity', 0)
                .text(d => d.text)
                .attr('transform', `translate(${width / 2}, ${height / 2 + verticalOffset})`)
                .on('mouseenter', (event, d) => showTooltip(event, d))
                .on('mousemove', (event, d) => showTooltip(event, d))
                .on('mouseleave', hideTooltip)
                .on('click', (event, d) => handleSelect(d))
                .classed('is-new', d => d.isNew)
                .transition()
                .duration(450)
                .attr('transform', d => `translate(${d.x + width / 2}, ${d.y + height / 2 + verticalOffset}) rotate(${d.rotate})`)
                .attr('opacity', 0.95),
            update => update
                .classed('is-new', d => d.isNew)
                .attr('data-cluster', d => d.clusterId)
                .transition()
                .duration(350)
                .attr('font-size', d => d.size)
                .attr('fill', d => clusterColor(d.clusterId))
                .attr('transform', d => `translate(${d.x + width / 2}, ${d.y + height / 2 + verticalOffset}) rotate(${d.rotate})`)
                .attr('opacity', 0.95),
            exit => exit.transition().duration(200).attr('opacity', 0).remove()
        );

        updateSelectionStyles();
    }

    function showTooltip(event, word) {
        const clusterMeta = clusterDefs.find(d => d.id === word.clusterId);
        const [mx, my] = d3.pointer(event, stagePanel.node());
        const trendLabel = formatTrendText(word.yoy, word.isNew);
        const pillClass = trendClass(word.yoy, word.isNew);
        tooltip
            .classed('hidden', false)
            .style('left', `${mx + 12}px`)
            .style('top', `${my + 12}px`)
            .html(`
				<strong>${word.text}</strong>
				<div>引用：${formatNumber(word.value)}</div>
				<div>${clusterMeta?.label || '关键词'} · ${clusterMeta?.description || ''}</div>
				<div><span class="delta-pill ${pillClass}">${trendLabel}</span></div>
			`);
    }

    function hideTooltip() {
        tooltip.classed('hidden', true);
    }

    function handleSelect(word) {
        selectedToken = word.text;
        updateSelectionStyles();
        const clusterMeta = clusterDefs.find(d => d.id === word.clusterId);
        const trendLabel = formatTrendText(word.yoy, word.isNew);
        const summary = `在 ${selectedYear} 年，“${word.text}” 累计引用 ${formatNumber(word.value)} 次，属于 ${clusterMeta?.label || '该'} 集群，${trendLabel}。可结合上下游任务挖掘进一步的应用落地机会。`;
        insightTitle.text(word.text);
        insightMeta.text(`${selectedYear} · 引用 ${formatNumber(word.value)} · ${trendLabel}`);
        insightText.text(summary);
        dispatcher.call('paperSelectedSync', stagePanel.node(), {
            title: `${word.text} ｜ ${selectedYear}`,
            year: selectedYear,
            keywords: [word.text],
            citations: word.value,
            summary,
            yoy: word.yoy
        });
    }

    function updateSelectionStyles() {
        wordGroup.selectAll('text')
            .classed('is-active', d => selectedToken === d.text);
    }

    function updateStageBadge(words = []) {
        const count = words.length;
        const highlight = words.find(d => d.isNew || (Number.isFinite(d.yoy) && d.yoy >= 0.25)) || words[0];
        const trendLabel = highlight ? formatTrendText(highlight.yoy, highlight.isNew) : '暂无同比';
        const badgeText = highlight ? `高增速：${highlight.text} ${trendLabel}` : '暂无高增速关键词';
        stageBadge.html(`<strong>${selectedYear}</strong> · ${count} 个关键词 · ${badgeText}`);
    }

    function updateRanking(words) {
        const top = words.slice().sort((a, b) => b.value - a.value).slice(0, 5);
        rankingEmpty.style('display', top.length ? 'none' : 'block');
        const items = rankingList.selectAll('li').data(top, d => d.text);
        const rows = items.join('li');
        rows.html(d => `
			<div class="wordcloud-rank-label">
				<span>${d.text}</span>
				<span class="delta-pill ${trendClass(d.yoy, d.isNew)}">${formatTrendText(d.yoy, d.isNew, { withPrefix: false })}</span>
			</div>
			<strong>${formatNumber(d.value)}</strong>
		`)
            .on('click', (_, d) => handleSelect(d));
        if (top.length === 0) {
            rankingList.selectAll('li').remove();
        }
    }

    const externalHandler = payload => {
        if (payload?.year && payload.source !== 'wordcloud' && years.includes(payload.year)) {
            selectedYear = payload.year;
            yearSlider.property('value', selectedYear);
            yearValue.text(selectedYear);
            runLayout();
        }
    };

    dispatcher.on('viewUpdate.wordcloud', externalHandler);

    runLayout();

    return () => {
        dispatcher.on('viewUpdate.wordcloud', null);
        if (activeLayout) activeLayout.stop();
        ro.disconnect();
    };
}
