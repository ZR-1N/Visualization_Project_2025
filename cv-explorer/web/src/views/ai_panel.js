// web/src/views/ai_panel.js
export function renderAiPanel(container, state, dispatcher) {
    const wrapper = container.append('div').attr('class', 'panel ai-panel-view');
    wrapper.append('h2').text('AI 深度解读');
    wrapper.append('p').attr('class', 'ai-tip').text('在其他视图选择节点或论文，AI 将于此处生成上下文摘要。');

    const selectionBox = wrapper.append('div').attr('class', 'ai-card ai-selection');
    const selectionHead = selectionBox.append('div').attr('class', 'ai-selection-head');
    const statusPill = selectionHead.append('span').attr('class', 'ai-status-pill').attr('data-state', 'idle').text('待命');
    const selectionHint = selectionHead.append('span').attr('class', 'ai-selection-hint').text('等待用户交互...');

    const selectionBody = selectionBox.append('div').attr('class', 'ai-selection-body');
    const selectionTitle = selectionBody.append('h3').attr('class', 'ai-selection-title');
    const selectionMeta = selectionBody.append('p').attr('class', 'ai-meta');
    const selectionText = selectionBody.append('p').attr('class', 'ai-selection-text');
    const chipRow = selectionBody.append('div').attr('class', 'ai-chip-row');

    const summaryBlock = wrapper.append('div').attr('class', 'ai-summary');

    const venueTotals = Object.entries(state.summary?.venues || {})
        .map(([venue, series]) => ({
            venue,
            total: Object.values(series).reduce((sum, value) => sum + (value || 0), 0)
        }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 5);

    const venueSection = summaryBlock.append('div').attr('class', 'ai-summary-block');
    venueSection.append('h3').text('十年产出 Top Venues');
    const venueGrid = venueSection.append('div').attr('class', 'ai-venue-grid');
    const venueCards = venueGrid.selectAll('.metric-card')
        .data(venueTotals)
        .join('div')
        .attr('class', 'metric-card compact');

    venueCards.append('div')
        .attr('class', 'metric-label')
        .text((d, i) => `#${i + 1} ${d.venue}`);
    venueCards.append('div')
        .attr('class', 'metric-value')
        .text(d => d.total.toLocaleString());
    venueCards.append('div')
        .attr('class', 'metric-subtitle')
        .text('累计发表');

    const keywordBlock = summaryBlock.append('div').attr('class', 'ai-summary-block');
    keywordBlock.append('h3').text('近年热门关键词');
    const latestYear = state.filters?.year;
    const keywordData = Object.entries(state.summary?.keywords?.[latestYear] || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    const keywordWall = keywordBlock.append('div').attr('class', 'ai-chip-wall');
    keywordWall.selectAll('span')
        .data(keywordData)
        .join('span')
        .attr('class', 'ai-chip')
        .text(d => `${d[0]} · ${d[1]}`);

    let typingTimer = null;
    let pendingTimer = null;

    function setStatus(text, state) {
        statusPill.text(text).attr('data-state', state);
    }

    function typewrite(selection, text, speed = 18) {
        if (typingTimer) {
            clearInterval(typingTimer);
            typingTimer = null;
        }
        selection.classed('is-typing', true).text('');
        let index = 0;
        typingTimer = setInterval(() => {
            selection.text(text.slice(0, index + 1));
            index += 1;
            if (index >= text.length) {
                clearInterval(typingTimer);
                typingTimer = null;
                selection.classed('is-typing', false);
            }
        }, speed);
    }

    function formatNumber(value) {
        const num = Number(value);
        return Number.isFinite(num) ? num.toLocaleString() : value;
    }

    function buildMeta(payload) {
        const tokens = [];
        if (payload.year) tokens.push(payload.year);
        if (payload.venue) tokens.push(payload.venue);
        if (payload.problem && payload.method) tokens.push(`${payload.problem} → ${payload.method}`);
        if (payload.citations != null) tokens.push(`引用 ${formatNumber(payload.citations)}`);
        if (payload.value != null) {
            const weight = Number(payload.value);
            tokens.push(`权重 ${Number.isFinite(weight) ? Math.round(weight) : payload.value}`);
        }
        return tokens.join(' · ') || '暂无上下文';
    }

    function buildSummary(payload) {
        if (payload.summary) return payload.summary;
        const fragments = [];
        if (payload.problem && payload.method) {
            fragments.push(`${payload.problem} 与 ${payload.method} 的组合在近年表现活跃。`);
        }
        if (payload.venue) {
            fragments.push(`相关成果多见于 ${payload.venue}。`);
        }
        if (payload.value != null) {
            const weight = Number(payload.value);
            const val = Number.isFinite(weight) ? Math.round(weight) : payload.value;
            fragments.push(`该流向聚合权重约为 ${val}。`);
        }
        const topicText = (payload.concepts || payload.keywords || []).slice(0, 3).join('、');
        if (topicText) {
            fragments.push(`关键词聚焦在 ${topicText} 等主题。`);
        }
        return fragments.length ? fragments.join(' ') : '暂无更多描述，尝试选择另一条路径或论文。';
    }

    function updateChips(keywords, isGhost = false) {
        const data = keywords && keywords.length ? keywords : ['等待', 'AI', '洞察'];
        const chips = chipRow.selectAll('span')
            .data(data, (d, i) => (typeof d === 'string' ? `${d}-${i}` : d.label || d));

        chips.join(enter => enter.append('span').attr('class', 'ai-chip'))
            .text(d => (typeof d === 'string' ? d : d.label || d))
            .classed('ghost', isGhost);
    }

    function showIdleState() {
        setStatus('待命', 'idle');
        selectionHint.text('等待用户交互...');
        selectionTitle.text('等待选择');
        selectionMeta.text('在概览或语义景观中点击节点以触发 AI');
        selectionText.classed('is-typing', false).text('AI 会在此处生成精选摘要、关键词与上下文。');
        chipRow.selectAll('span').remove();
    }

    function showLoadingState(payload) {
        setStatus('生成中', 'loading');
        selectionHint.text('AI 正在整理上下文...');
        selectionTitle.text(payload.title || payload.label || '自定义选择');
        selectionMeta.text(buildMeta(payload));
        selectionText.classed('is-typing', true).text('AI 正在撰写洞察...');
        updateChips(['分析', '上下文', '关联'], true);
    }

    function showResult(payload) {
        setStatus('已生成', 'ready');
        selectionHint.text('可重新选择其他节点以刷新洞察');
        const summary = buildSummary(payload);
        typewrite(selectionText, summary);
        const chips = (payload.concepts || payload.keywords || []).slice(0, 5).map(label => ({ label }));
        updateChips(chips);
    }

    function renderSelection(payload) {
        if (pendingTimer) {
            clearTimeout(pendingTimer);
            pendingTimer = null;
        }
        if (!payload) {
            showIdleState();
            return;
        }
        showLoadingState(payload);
        pendingTimer = setTimeout(() => {
            showResult(payload);
            pendingTimer = null;
        }, 480);
    }

    showIdleState();
    const handler = payload => renderSelection(payload);
    dispatcher.on('paperSelected.aiView', handler);

    return () => {
        dispatcher.on('paperSelected.aiView', null);
        if (typingTimer) clearInterval(typingTimer);
        if (pendingTimer) clearTimeout(pendingTimer);
    };
}