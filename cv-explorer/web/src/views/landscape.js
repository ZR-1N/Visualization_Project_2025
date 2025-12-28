// web/src/views/landscape.js
export function renderLandscape(container, state, dispatcher) {
    const rawDataset = state.landscape || [];
    const dataset = rawDataset
        .map((entry, index) => {
            const parsedYear = typeof entry.year === 'string' ? parseInt(entry.year, 10) : entry.year;
            const parsedCitations = Number(entry.citations);
            const normalizedConcepts = Array.isArray(entry.concepts)
                ? entry.concepts
                : (typeof entry.concepts === 'string'
                    ? entry.concepts.split(/[,;/]/).map(token => token.trim()).filter(Boolean)
                    : []);
            return {
                ...entry,
                id: entry.id ?? `paper-${index}`,
                year: Number.isFinite(parsedYear) ? parsedYear : null,
                citations: Number.isFinite(parsedCitations) ? parsedCitations : 0,
                x: Number(entry.x),
                y: Number(entry.y),
                venue: entry.venue || 'Others',
                concepts: normalizedConcepts,
            };
        })
        .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));

    if (!dataset.length) {
        container.append('div').attr('class', 'empty-state').text('暂无语义数据，请检查 landscape_data.json');
        return;
    }

    const semanticLabelOf = entry => entry?.semantic_primary
        || (Array.isArray(entry?.concepts) ? entry.concepts[0] : null)
        || entry?.semantic_cluster
        || entry?.venue
        || 'Others';

    const secondaryKeywordOf = entry => entry?.semantic_cluster
        || (Array.isArray(entry?.concepts) ? entry.concepts[1] : null)
        || (Array.isArray(entry?.concepts) ? entry.concepts[0] : null)
        || '递补';

    const numberFormat = d3.format(',');
    const layout = container.append('div').attr('class', 'landscape-layout');
    const controlPanel = layout.append('div').attr('class', 'panel landscape-controls');
    const stagePanel = layout.append('div').attr('class', 'panel landscape-stage');

    const canvas = stagePanel.append('canvas').attr('class', 'landscape-canvas').node();
    const ctx = canvas.getContext('2d');
    const overlay = stagePanel.append('svg').attr('class', 'landscape-overlay');
    const labelRoot = overlay.append('g').attr('class', 'landscape-label-root');
    const islandLayer = labelRoot.append('g').attr('class', 'island-label-layer');
    const anchorLayer = labelRoot.append('g').attr('class', 'anchor-layer');
    const paperLayer = labelRoot.append('g').attr('class', 'paper-label-layer');
    const stageBadge = stagePanel.append('div').attr('class', 'landscape-stage-status');
    const tooltip = stagePanel.append('div').attr('class', 'chart-tooltip hidden');
    const defaultHoverHtml = '<h3>语义锚点待命</h3><p>在图中移动或放大，即可唤醒对应论文与领域。</p>';
    let hoverCard = null;

    const years = Array.from(new Set(dataset.map(d => d.year).filter(Number.isFinite))).sort((a, b) => a - b);
    const latestYear = years[years.length - 1] ?? new Date().getFullYear();
    const requestedYear = Number(state.filters?.year);
    const venues = ['ALL', ...Array.from(new Set(dataset.map(d => d.venue || 'Others'))).sort()];
    let selectedYear = Number.isFinite(requestedYear) && years.includes(requestedYear)
        ? requestedYear
        : latestYear;
    let showAllYears = true; // 默认显示所有年份，避免因年份过滤导致初始空白
    let selectedVenue = 'ALL';
    let anchorCount = 12;
    let smoothingFactor = 0.4;
    let transform = d3.zoomIdentity;

    const validYears = dataset.map(d => d.year).filter(Number.isFinite);
    const minYear = validYears.length ? d3.min(validYears) : latestYear - 5;
    const maxYear = validYears.length ? d3.max(validYears) : latestYear;
    const yearExtentForColor = [minYear, maxYear];

    // Safety check for interpolator
    const interpolator = typeof d3.interpolateSpectral === 'function'
        ? d3.interpolateSpectral
        : d3.interpolateViridis; // Fallback

    const colorScale = d3.scaleOrdinal(d3.schemeTableau10);

    // 颜色不再使用语义颜色，而是回归年份颜色
    const semanticColor = d => {
        if (Number.isFinite(d.year)) return yearColor(d.year);
        return '#94a3b8';
    };

    // 保留 yearColor 仅作为降级方案，但主要使用 semanticColor
    const yearColor = value => {
        if (!Number.isFinite(value)) return '#94a3b8';
        // 使用与图例一致的逻辑：minYear -> 1 (Spectral左), maxYear -> 0 (Spectral右)
        // 注意 d3.interpolateSpectral 通常蓝紫色在 0，红色在 1
        // 我们希望旧年份(min)是冷色/暖色，新年份(max)是暖色/冷色
        // 这里沿用之前的逻辑：(maxYear - value) / (maxYear - minYear)
        // value=max -> 0, value=min -> 1
        return d3.color(interpolator((maxYear - value) / (maxYear - minYear))).formatRgb();
    };

    const citationExtent = d3.extent(dataset, d => d.citations || 1);
    if (citationExtent[0] === citationExtent[1]) {
        citationExtent[1] = citationExtent[0] + 1;
    }

    const radiusScale = d3.scaleSqrt().domain(citationExtent).range([2, 11]);

    const normalizeExtent = ([min, max]) => (min === max ? [min - 1, max + 1] : [min, max]);
    const xExtent = normalizeExtent(d3.extent(dataset, d => d.x));
    const yExtent = normalizeExtent(d3.extent(dataset, d => d.y));
    const padding = 30;
    let pointerCache = [];

    controlPanel.append('h2').text('语义学术地图');
    controlPanel.append('p').attr('class', 'flow-tip').text('拖拽、缩放解锁“语义锚点”，观察学科势力版图。');

    const yearRow = controlPanel.append('div').attr('class', 'control-row');
    const yearHeader = yearRow.append('div').attr('class', 'control-row-head');
    yearHeader.append('label').text('年份');
    const yearValue = yearHeader.append('span').attr('class', 'control-value');
    const yearSlider = yearRow.append('input')
        .attr('class', 'control-slider')
        .attr('type', 'range')
        .attr('min', years[0] ?? selectedYear)
        .attr('max', years[years.length - 1] ?? selectedYear)
        .attr('step', 1)
        .property('value', selectedYear)
        .on('input', event => {
            selectedYear = Number(event.target.value);
            syncYearControls();
            draw();
            dispatcher.call('viewUpdate', canvas, { source: 'landscape', year: selectedYear });
        });

    const syncYearControls = () => {
        if (!showAllYears && Number.isFinite(selectedYear)) {
            yearSlider.property('value', selectedYear);
        }
        yearSlider.property('disabled', showAllYears || years.length <= 1);
        yearRow.classed('is-disabled', yearSlider.property('disabled'));
        yearValue.text(showAllYears ? '全部' : selectedYear);
    };
    syncYearControls();

    const allYearsToggle = controlPanel.append('label').attr('class', 'toggle');
    allYearsToggle.append('input')
        .attr('type', 'checkbox')
        .property('checked', showAllYears)
        .on('change', event => {
            showAllYears = event.target.checked;
            syncYearControls();
            draw();
        });
    allYearsToggle.append('span').text('显示所有年份');

    const venueSelect = controlPanel.append('select')
        .on('change', event => {
            selectedVenue = event.target.value;
            draw();
        });
    venueSelect.selectAll('option')
        .data(venues)
        .join('option')
        .attr('value', d => d)
        .text(d => (d === 'ALL' ? '全部会议' : d));

    const anchorRow = controlPanel.append('div').attr('class', 'control-row');
    const anchorHeader = anchorRow.append('div').attr('class', 'control-row-head');
    anchorHeader.append('label').text('语义锚点');
    const anchorValue = anchorHeader.append('span').attr('class', 'control-value').text(anchorCount);
    anchorRow.append('input')
        .attr('class', 'control-slider')
        .attr('type', 'range')
        .attr('min', 6)
        .attr('max', 20)
        .attr('step', 1)
        .property('value', anchorCount)
        .on('input', event => {
            anchorCount = Number(event.target.value);
            anchorValue.text(anchorCount);
            draw();
        });

    const smoothingRow = controlPanel.append('div').attr('class', 'control-row');
    const smoothingHeader = smoothingRow.append('div').attr('class', 'control-row-head');
    smoothingHeader.append('label').text('语义平滑');
    const smoothingValue = smoothingHeader.append('span').attr('class', 'control-value').text(`${Math.round(smoothingFactor * 100)}%`);
    smoothingRow.append('input')
        .attr('class', 'control-slider')
        .attr('type', 'range')
        .attr('min', 0)
        .attr('max', 1)
        .attr('step', 0.05)
        .property('value', smoothingFactor)
        .on('input', event => {
            smoothingFactor = Number(event.target.value);
            smoothingValue.text(`${Math.round(smoothingFactor * 100)}%`);
            draw();
        });

    const controlButtons = controlPanel.append('div').attr('class', 'flow-reset-row');
    controlButtons.append('button')
        .attr('class', 'flow-button tiny')
        .text('重置视图')
        .on('click', () => {
            transform = d3.zoomIdentity;
            d3.select(stagePanel.node()).transition().duration(350).call(zoom.transform, transform);
        });

    const legendBlock = controlPanel.append('div').attr('class', 'landscape-legend');
    legendBlock.append('p').text('颜色 = 年份分布 | 线条 = 论文密度');

    // 移除语义图例的生成逻辑，因为颜色不再代表语义
    // const semanticLegendGrid = legendBlock.append('div').attr('class', 'landscape-legend-grid');
    // ...

    // 改为生成年份渐变图例
    const gradientWrap = legendBlock.append('div').attr('class', 'landscape-legend-gradient');
    const gradientStops = 10;
    const yearSpan = maxYear - minYear;

    // 生成渐变条
    const gradientBar = gradientWrap.append('div')
        .style('height', '12px')
        .style('width', '100%')
        .style('border-radius', '6px')
        .style('background', `linear-gradient(to right, ${d3.range(gradientStops).map(i => {
            const t = i / (gradientStops - 1);
            // 注意：interpolateSpectral 通常是 0=红(旧), 1=蓝(新)，或者反过来
            // 这里我们希望左边是旧年份，右边是新年份
            // 我们的 yearColor 逻辑是：(maxYear - value) / (maxYear - minYear)
            // 当 value = minYear -> (max-min)/(max-min) = 1
            // 当 value = maxYear -> 0/(max-min) = 0
            // 所以 0 对应 maxYear, 1 对应 minYear
            // 我们希望左边(minYear)对应 1，右边(maxYear)对应 0
            return interpolator(1 - t);
        }).join(',')
            })`);

    // 生成年份标签
    const labelRow = gradientWrap.append('div')
        .style('display', 'flex')
        .style('justify-content', 'space-between')
        .style('margin-top', '4px')
        .style('font-size', '11px')
        .style('color', '#94a3b8');

    labelRow.append('span').text(minYear);
    labelRow.append('span').text(Math.floor((minYear + maxYear) / 2));
    labelRow.append('span').text(maxYear);

    /* Removed Year Gradient Legend
    const gradientWrap = legendBlock.append('div').attr('class', 'landscape-legend-gradient');
    // ... (gradient code removed) ...
    */

    // Keep era chips but maybe styling only
    /*
    const eraLegend = legendBlock.append('div').attr('class', 'landscape-era-chips');
    // ...
    */

    const summaryList = controlPanel.append('ul').attr('class', 'landscape-summary');
    const digestBlock = controlPanel.append('div').attr('class', 'landscape-digest');
    digestBlock.append('p')
        .attr('class', 'digest-tip')
        .text('语义脉络速览');
    const digestGrid = digestBlock.append('div').attr('class', 'landscape-digest-grid');
    hoverCard = controlPanel.append('div')
        .attr('class', 'landscape-hover')
        .html(defaultHoverHtml);
    const pointKey = point => point.id || `${point.title}-${point.year}`;

    const zoom = d3.zoom()
        .scaleExtent([0.5, 4])
        .on('zoom', event => {
            transform = event.transform;
            draw();
        });

    const stageSelection = d3.select(stagePanel.node());
    stageSelection.call(zoom).on('dblclick.zoom', null);

    const stageNode = stagePanel.node();
    const applySize = () => {
        const { width, height } = stageNode.getBoundingClientRect();
        if (!width || !height) return;
        canvas.width = width;
        canvas.height = height;
        overlay.attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
        try {
            draw();
        } catch (e) {
            console.error("Draw failed:", e);
        }
    };

    let resizeObserver = null;
    if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(applySize);
        resizeObserver.observe(stageNode);
    }

    applySize();

    function filteredData() {
        return dataset.filter(d => {
            const yearMatch = showAllYears || (Number.isFinite(d.year) && d.year === selectedYear);
            const venueMatch = selectedVenue === 'ALL' || d.venue === selectedVenue;
            return yearMatch && venueMatch;
        });
    }

    function getSemanticAnchors(data) {
        const weightOf = entry => Math.pow((entry.citations || 1) + 1, 1 + smoothingFactor * 0.8);
        const grouped = d3.rollups(
            data,
            values => {
                const totalWeight = d3.sum(values, weightOf);
                const avgX = totalWeight ? d3.sum(values, v => weightOf(v) * v.x) / totalWeight : d3.mean(values, v => v.x);
                const avgY = totalWeight ? d3.sum(values, v => weightOf(v) * v.y) / totalWeight : d3.mean(values, v => v.y);
                const totalCites = d3.sum(values, v => v.citations || 0);
                const sampleCount = values.length;
                const avgCites = sampleCount ? totalCites / sampleCount : 0;
                const coverageScore = sampleCount ? Math.pow(sampleCount, 1.18) : 0;
                const citationScore = Math.log1p(avgCites || 0) * 4;
                return {
                    x: avgX,
                    y: avgY,
                    count: sampleCount,
                    importance: totalCites,
                    score: coverageScore + citationScore,
                    keywords: d3.rollups(values, v => v.length, v => secondaryKeywordOf(v))
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 3)
                        .map(d => d[0])
                };
            },
            semanticLabelOf
        );

        return grouped
            .map(([name, meta]) => ({ name, ...meta }))
            .filter(d => d.name !== 'Others' && d.name !== 'Uncategorized Research' && d.name !== 'General Computer Vision')
            .sort((a, b) => (b.score - a.score) || (b.count - a.count) || (b.importance - a.importance))
            .slice(0, anchorCount);
    }

    function draw() {
        if (!canvas.width || !canvas.height) return;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const data = filteredData();
        const xScale = d3.scaleLinear().domain(xExtent).range([padding, canvas.width - padding]);
        const yScale = d3.scaleLinear().domain(yExtent).range([canvas.height - padding, padding]);
        const projectX = value => transform.applyX(xScale(value));
        const projectY = value => transform.applyY(yScale(value));

        drawQuadrantBackdrop(ctx, canvas.width, canvas.height, projectX, projectY);
        const anchors = getSemanticAnchors(data);
        drawDensityContours(data, projectX, projectY);
        drawNodes(data, projectX, projectY);
        renderProfessionalLabels(anchors, data, projectX, projectY);
        updateSummary(anchors);
        updateDigest(data, anchors);
        updateStageBadge(data, anchors);
    }

    function drawDensityContours(data, projectX, projectY) {
        if (data.length < 5) return;

        // Safety check for D3 modules
        if (typeof d3.contourDensity !== 'function' || typeof d3.geoPath !== 'function') {
            console.warn('d3-contour or d3-geo not loaded, skipping density contours');
            return;
        }

        const projected = data.map(point => ({
            x: projectX(point.x),
            y: projectY(point.y),
            weight: Math.max(1, point.citations || 1)
        })).filter(p => (
            Number.isFinite(p.x) && Number.isFinite(p.y) &&
            p.x >= -100 && p.x <= canvas.width + 100 &&
            p.y >= -100 && p.y <= canvas.height + 100
        ));

        if (!projected.length) return;

        try {
            const density = d3.contourDensity()
                .x(d => d.x)
                .y(d => d.y)
                .weight(d => d.weight)
                .size([canvas.width, canvas.height])
                .bandwidth(Math.max(25, 90 / transform.k))
                .thresholds(d3.range(0.02, 0.18, 0.02));

            const contours = density(projected);
            if (!contours || !contours.length) return;

            ctx.save();
            const geoPath = d3.geoPath(null, ctx);
            contours.forEach(contour => {
                const alpha = Math.min(0.45, 0.08 + contour.value * 2.2);
                ctx.beginPath();
                geoPath(contour);
                ctx.fillStyle = `rgba(56, 189, 248, ${alpha * 0.6})`;
                ctx.strokeStyle = `rgba(226, 232, 240, ${Math.min(0.8, alpha + 0.15)})`;
                ctx.lineWidth = 1.2;
                ctx.fill();
                ctx.stroke();
            });
            ctx.restore();
        } catch (err) {
            console.error('Error drawing density contours:', err);
            ctx.restore();
        }
    }

    function drawNodes(data, projectX, projectY) {
        const highlightCount = Math.min(60, data.length);
        const highlights = d3.sort([...data], (a, b) => (b.citations || 0) - (a.citations || 0)).slice(0, highlightCount);
        const highlightKeys = new Set(highlights.map(pointKey));

        pointerCache = [];
        data.forEach(point => {
            const screenX = projectX(point.x);
            const screenY = projectY(point.y);
            const baseRadius = radiusScale(point.citations || 1);
            const radius = Math.max(2, baseRadius * (0.7 + transform.k * 0.3));

            ctx.beginPath();
            const tone = yearColor(point.year);
            ctx.fillStyle = tone;
            ctx.globalAlpha = 0.85;
            ctx.arc(screenX, screenY, radius, 0, Math.PI * 2);
            ctx.fill();

            if (highlightKeys.has(pointKey(point))) {
                ctx.globalAlpha = 1;
                const darkerTone = (() => {
                    const base = d3.color(tone);
                    if (!base) return null;
                    const tweaked = base.darker(0.8);
                    return tweaked.formatHex ? tweaked.formatHex() : tweaked.toString();
                })();
                ctx.strokeStyle = darkerTone || 'rgba(248, 250, 252, 0.9)';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.arc(screenX, screenY, radius + 2, 0, Math.PI * 2);
                ctx.stroke();
            }

            pointerCache.push({ ...point, screenX, screenY, radius });
        });

        ctx.globalAlpha = 1;
    }

    function renderProfessionalLabels(anchors, data, projectX, projectY) {
        const fontScale = d3.scaleLinear()
            .domain([0, d3.max(anchors, d => (d.score ?? d.importance)) || 1])
            .range([13, 24]);
        const showDetailed = transform.k >= 1.5;

        const islandPayload = showDetailed
            ? []
            : anchors.slice(0, Math.min(6, anchors.length)).map(anchor => ({
                ...anchor,
                label: (anchor.keywords?.[0] || anchor.name || '语义岛').toUpperCase(),
                screenX: projectX(anchor.x),
                screenY: projectY(anchor.y)
            }));

        const islandNodes = islandLayer.selectAll('.semantic-island').data(islandPayload, d => d.name);
        const islandEnter = islandNodes.enter().append('g').attr('class', 'semantic-island');
        islandEnter.append('rect').attr('class', 'chip-bg');
        islandEnter.append('text').attr('class', 'chip-text').attr('text-anchor', 'middle').attr('dy', '0.35em');

        const islandMerge = islandEnter.merge(islandNodes);
        islandMerge.attr('transform', d => `translate(${d.screenX}, ${d.screenY})`);
        islandMerge.select('.chip-text')
            .text(d => d.label)
            .style('font-size', `${Math.max(13, 18 / Math.sqrt(Math.max(1, transform.k)))}px`);
        islandMerge.each(function () {
            const group = d3.select(this);
            const textNode = group.select('text').node();
            const bbox = textNode ? textNode.getBBox() : null;
            if (!bbox) return;
            group.select('.chip-bg')
                .attr('x', bbox.x - 24)
                .attr('y', bbox.y - 12)
                .attr('width', bbox.width + 48)
                .attr('height', bbox.height + 24)
                .attr('rx', 24)
                .attr('ry', 24);
        });
        islandNodes.exit().remove();

        if (!showDetailed) {
            anchorLayer.selectAll('.semantic-anchor-chip').remove();
            paperLayer.selectAll('.paper-chip').remove();
            return;
        }

        const anchorNodes = anchorLayer.selectAll('.semantic-anchor-chip').data(anchors, d => d.name);
        const anchorEnter = anchorNodes.enter().append('g').attr('class', 'semantic-anchor-chip');
        anchorEnter.append('rect').attr('class', 'chip-bg');
        anchorEnter.append('text').attr('class', 'chip-text').attr('text-anchor', 'middle').attr('dy', '0.35em');

        const anchorMerged = anchorEnter.merge(anchorNodes);
        anchorMerged.attr('transform', d => `translate(${projectX(d.x)}, ${projectY(d.y)})`);
        anchorMerged.select('.chip-text')
            .text(d => `${(d.keywords?.[0] || d.name).toUpperCase()} · ${numberFormat(d.count)}`)
            .style('font-size', d => `${fontScale(d.score ?? d.importance) / Math.sqrt(transform.k)}px`);

        anchorMerged.each(function () {
            const group = d3.select(this);
            const textNode = group.select('text').node();
            const bbox = textNode ? textNode.getBBox() : null;
            if (!bbox) return;
            group.select('.chip-bg')
                .attr('x', bbox.x - 18)
                .attr('y', bbox.y - 10)
                .attr('width', bbox.width + 36)
                .attr('height', bbox.height + 20)
                .attr('rx', 18)
                .attr('ry', 18);
        });
        anchorNodes.exit().remove();

        const viewWidth = canvas.width;
        const viewHeight = canvas.height;
        const annotated = data.map(d => ({
            ...d,
            screenX: projectX(d.x),
            screenY: projectY(d.y)
        })).filter(d => (
            d.screenX >= 0 && d.screenX <= viewWidth &&
            d.screenY >= 0 && d.screenY <= viewHeight
        ));

        const spotlight = d3.sort(annotated, (a, b) => (b.citations || 0) - (a.citations || 0)).slice(0, 6);
        const paperNodes = paperLayer.selectAll('.paper-chip').data(spotlight, d => d.id);
        const paperEnter = paperNodes.enter().append('g').attr('class', 'paper-chip');
        paperEnter.append('rect').attr('class', 'chip-bg');
        paperEnter.append('text').attr('class', 'chip-text').attr('text-anchor', 'middle').attr('dy', '0.35em');

        const paperMerged = paperEnter.merge(paperNodes);
        paperMerged.attr('transform', d => `translate(${d.screenX}, ${d.screenY - 18})`);
        paperMerged.select('.chip-text')
            .text(d => `${d.title} · 引用 ${numberFormat(d.citations || 0)}`)
            .style('font-size', `${Math.max(11, 13 / Math.sqrt(transform.k))}px`);

        paperMerged.each(function () {
            const group = d3.select(this);
            const textNode = group.select('text').node();
            const bbox = textNode ? textNode.getBBox() : null;
            if (!bbox) return;
            group.select('.chip-bg')
                .attr('x', bbox.x - 14)
                .attr('y', bbox.y - 8)
                .attr('width', bbox.width + 28)
                .attr('height', bbox.height + 16)
                .attr('rx', 14)
                .attr('ry', 14);
        });

        paperNodes.exit().remove();
    }

    function updateSummary(anchors) {
        if (!anchors.length) {
            summaryList.html('<li>暂无语义锚点</li>');
            return;
        }
        summaryList.selectAll('li')
            .data(anchors.slice(0, 4))
            .join('li')
            .text(anchor => `${anchor.name} · ${numberFormat(anchor.importance)} 引力 · ${anchor.keywords.join(' / ')}`);
    }

    function updateDigest(data, anchors) {
        if (!digestGrid) return;
        if (!data.length) {
            digestGrid.selectAll('.digest-card').remove();
            digestGrid.selectAll('.digest-empty')
                .data([1])
                .join('div')
                .attr('class', 'digest-empty')
                .text('暂无样本，尝试切换年份或会议');
            return;
        }

        digestGrid.selectAll('.digest-empty').remove();
        const medianCitations = d3.median(data, d => d.citations || 0) || 0;
        const scopedYears = data.map(d => d.year).filter(Number.isFinite);
        const yearWindow = scopedYears.length
            ? `${d3.min(scopedYears)} – ${d3.max(scopedYears)}`
            : (showAllYears ? '全周期' : `${selectedYear}`);
        const anchorLeader = anchors[0];

        // Calculate anchor share with defensive check
        let anchorShare = 0;
        if (anchorLeader && data.length > 0) {
            anchorShare = Math.round((anchorLeader.count / data.length) * 100);
        }

        const conceptCounts = new Map();
        data.forEach(entry => {
            // Deduplicate concepts per paper to ensure total % <= 100%
            const uniqueConcepts = new Set();
            const blacklist = new Set(['Uncategorized Research', 'Others', 'General Computer Vision']);

            const addIfValid = term => {
                if (term && !blacklist.has(term)) uniqueConcepts.add(term);
            };

            addIfValid(entry.semantic_primary);
            addIfValid(entry.semantic_cluster);
            (entry.concepts || []).slice(0, 1).forEach(addIfValid);

            uniqueConcepts.forEach(term => {
                conceptCounts.set(term, (conceptCounts.get(term) || 0) + 1);
            });
        });

        const conceptEntries = Array.from(conceptCounts.entries())
            .sort((a, b) => b[1] - a[1]);

        const conceptLeader = conceptEntries[0] || [null, 0];
        const conceptShare = data.length
            ? Math.round((conceptLeader[1] / data.length) * 100)
            : 0;

        const digestPayload = [
            {
                label: '样本规模',
                value: `${numberFormat(data.length)} 篇`,
                detail: `中位引用 ${numberFormat(Math.round(medianCitations))} · ${yearWindow}`
            },
            {
                label: '主导语义',
                value: anchorLeader ? (anchorLeader.keywords?.[0] || anchorLeader.name) : '待观察',
                detail: anchorLeader ? `吸引 ~${anchorShare}% 样本` : '放大图面以提取锚点'
            },
            {
                label: '热点关键词',
                value: conceptLeader[0] || '暂无',
                detail: conceptLeader[0] ? `覆盖 ~${conceptShare}% · ${numberFormat(conceptLeader[1])} 篇` : '等待更多样本'
            }
        ];

        const cards = digestGrid.selectAll('.digest-card')
            .data(digestPayload, d => d.label);
        const cardEnter = cards.enter().append('div').attr('class', 'digest-card');
        cardEnter.append('div').attr('class', 'digest-label');
        cardEnter.append('div').attr('class', 'digest-value');
        cardEnter.append('div').attr('class', 'digest-detail');

        cardEnter.merge(cards)
            .select('.digest-label')
            .text(d => d.label);
        cardEnter.merge(cards)
            .select('.digest-value')
            .text(d => d.value);
        cardEnter.merge(cards)
            .select('.digest-detail')
            .text(d => d.detail);

        cards.exit().remove();
    }

    function updateStageBadge(data, anchors) {
        const focusAnchor = anchors[0];
        const badgeYear = showAllYears ? '全部年份' : `${selectedYear}`;
        const badgeAnchor = focusAnchor ? `${focusAnchor.name} 占优` : '待出现锚点';
        stageBadge.text(`${badgeYear} · ${data.length} 篇 · ${badgeAnchor}`);
    }

    function drawQuadrantBackdrop(c, width, height, projectX, projectY) {
        c.save();
        const left = projectX(xExtent[0]);
        const right = projectX(xExtent[1]);
        const top = projectY(yExtent[1]);
        const bottom = projectY(yExtent[0]);
        const axisXValue = (xExtent[0] <= 0 && xExtent[1] >= 0) ? 0 : d3.mean(xExtent);
        const axisYValue = (yExtent[0] <= 0 && yExtent[1] >= 0) ? 0 : d3.mean(yExtent);
        const centerX = projectX(axisXValue);
        const centerY = projectY(axisYValue);

        c.strokeStyle = 'rgba(148, 163, 184, 0.15)'; // 调亮一点网格线
        c.lineWidth = 1;
        for (let x = left - (left % 50); x <= right; x += 50) {
            c.beginPath();
            c.moveTo(x, top);
            c.lineTo(x, bottom);
            c.stroke();
        }
        for (let y = top - (top % 50); y <= bottom; y += 50) {
            c.beginPath();
            c.moveTo(left, y);
            c.lineTo(right, y);
            c.stroke();
        }

        c.strokeStyle = 'rgba(148, 163, 184, 0.45)'; // 调亮中轴线
        c.setLineDash([4, 4]);
        c.beginPath();
        c.moveTo(left, centerY);
        c.lineTo(right, centerY);
        c.stroke();
        c.beginPath();
        c.moveTo(centerX, top);
        c.lineTo(centerX, bottom);
        c.stroke();
        c.setLineDash([]);

        c.fillStyle = 'rgba(226, 232, 240, 0.78)';
        c.font = `${12 / Math.sqrt(transform.k)}px "Space Grotesk", "Inter", sans-serif`;
        c.fillText('Theoretical Research', left + 18, top + 24);
        c.fillText('Industrial SOTA', right - 128, bottom - 16);
        c.fillText('Academic Frontier', right - 150, top + 24);
        c.fillText('Applied Labs', left + 18, bottom - 16);

        c.restore();
    }

    function findNearestPoint(event) {
        if (!pointerCache.length) return null;
        const [mx, my] = d3.pointer(event, canvas);
        let best = null;
        let bestDistance = Infinity;
        pointerCache.forEach(point => {
            const distance = Math.hypot(point.screenX - mx, point.screenY - my);
            const hitRadius = Math.max(point.radius + 6, 12);
            if (distance < hitRadius && distance < bestDistance) {
                best = point;
                bestDistance = distance;
            }
        });
        return best;
    }

    function showTooltip(point, event) {
        const [mx, my] = d3.pointer(event, stagePanel.node());
        tooltip
            .classed('hidden', false)
            .style('left', `${mx + 12}px`)
            .style('top', `${my}px`)
            .html(`
                <strong>${point.title}</strong>
                <div>${point.year || '未知年份'} · ${point.venue || '未知 venue'}</div>
                <div>引用：${(point.citations || 0).toLocaleString()}</div>
                <div>语义簇：${semanticLabelOf(point)}</div>
                <div>关键词：${(point.concepts || []).slice(0, 3).join(' / ') || '—'}</div>
            `);
    }

    function hideTooltip() {
        tooltip.classed('hidden', true);
    }

    function updateHoverCard(point) {
        if (!hoverCard) return;
        if (!point) {
            hoverCard.classed('active', false).html(defaultHoverHtml);
            return;
        }
        hoverCard.classed('active', true).html(`
            <h3>${point.title}</h3>
            <p class="hover-meta">${point.year || '年份未知'} · ${point.venue || '未知 venue'} · 引用 ${numberFormat(point.citations || 0)}</p>
            <p class="hover-topic">语义簇：${semanticLabelOf(point)}</p>
            <p>${(point.concepts || []).slice(0, 5).join(' / ') || '暂无关键词'}</p>
        `);
    }

    const handleMove = event => {
        const target = findNearestPoint(event);
        if (target) {
            showTooltip(target, event);
            canvas.style.cursor = 'pointer';
            if (!selectedPaper) {
                updateHoverCard(target);
            }
        } else {
            hideTooltip();
            canvas.style.cursor = 'default';
            if (!selectedPaper) {
                updateHoverCard(null);
            }
        }
    };

    const handleLeave = () => {
        hideTooltip();
        canvas.style.cursor = 'default';
        if (!selectedPaper) {
            updateHoverCard(null);
        }
    };

    const handleClick = event => {
        const target = findNearestPoint(event);
        if (target) {
            selectedPaper = target;
            updateHoverCard(target);
            dispatcher.call('paperSelectedSync', canvas, target);
        } else {
            selectedPaper = null;
            updateHoverCard(null);
        }
    };

    canvas.addEventListener('mousemove', handleMove);
    canvas.addEventListener('mouseleave', handleLeave);
    canvas.addEventListener('click', handleClick);

    const externalFilterHandler = payload => {
        const incomingYear = Number(payload?.year);
        if (Number.isFinite(incomingYear) && payload.source !== 'landscape' && !showAllYears) {
            selectedYear = incomingYear;
            syncYearControls();
            draw();
        }
    };

    dispatcher.on('viewUpdate.landscape', externalFilterHandler);

    return () => {
        if (resizeObserver) {
            resizeObserver.disconnect();
        }
        canvas.removeEventListener('mousemove', handleMove);
        canvas.removeEventListener('mouseleave', handleLeave);
        canvas.removeEventListener('click', handleClick);
        dispatcher.on('viewUpdate.landscape', null);
    };
}