// web/src/views/ai_panel.js
export function renderAiPanel(container, state, dispatcher) {
    const wrapper = container.append('div').attr('class', 'panel ai-panel-view');
    wrapper.append('h2').text('AI 深度解读');

    const configContainer = wrapper.append('div').attr('class', 'ai-config-container');
    const tip = wrapper.append('p').attr('class', 'ai-tip').text('在其他视图选择节点或论文，AI 将于此处生成上下文摘要。');

    const selectionBox = wrapper.append('div').attr('class', 'ai-card ai-selection');
    const selectionHead = selectionBox.append('div').attr('class', 'ai-selection-head');
    const statusPill = selectionHead.append('span').attr('class', 'ai-status-pill').attr('data-state', 'idle').text('待命');

    // Config UI Elements (Hidden by default or shown based on state)
    let configMode = false;
    let currentConfig = JSON.parse(localStorage.getItem('cv_explorer_ai_config') || '{"model": "mock", "apiKey": ""}');

    const configBtn = selectionHead.append('button')
        .attr('class', 'ai-config-btn')
        .text('⚙️ 设置')
        .on('click', toggleConfigMode);

    const selectionHint = selectionHead.append('span').attr('class', 'ai-selection-hint').text('等待用户交互...');

    // Configuration Panel (Initially hidden)
    const configPanel = wrapper.append('div')
        .attr('class', 'ai-config-panel hidden');

    configPanel.append('h3').text('AI API 配置');

    const formGroup = configPanel.append('div').attr('class', 'ai-form-group');
    formGroup.append('label').text('模型服务商');
    const modelSelect = formGroup.append('select').attr('class', 'ai-input');
    const models = [
        { value: 'mock', label: 'Mock (演示模式)' },
        { value: 'deepseek', label: 'DeepSeek' },
        { value: 'chatgpt', label: 'ChatGPT (OpenAI)' },
        { value: 'gemini', label: 'Gemini (Google)' },
        { value: 'doubao', label: '豆包 (ByteDance)' }
    ];
    modelSelect.selectAll('option')
        .data(models).join('option')
        .attr('value', d => d.value).text(d => d.label);

    const keyGroup = configPanel.append('div').attr('class', 'ai-form-group');
    keyGroup.append('label').text('API Key');
    const keyInput = keyGroup.append('input')
        .attr('type', 'password')
        .attr('class', 'ai-input')
        .attr('placeholder', '输入您的 API Key (仅本地存储)');

    const actionRow = configPanel.append('div').attr('class', 'ai-action-row');
    actionRow.append('button').attr('class', 'ai-btn primary').text('保存并使用').on('click', saveConfig);
    actionRow.append('button').attr('class', 'ai-btn ghost').text('清除配置').on('click', clearConfig);
    // Removed "Cancel" button as requested by user


    const selectionBody = selectionBox.append('div').attr('class', 'ai-selection-body');
    const selectionTitle = selectionBody.append('h3').attr('class', 'ai-selection-title');
    const selectionMeta = selectionBody.append('p').attr('class', 'ai-meta');
    const selectionText = selectionBody.append('p').attr('class', 'ai-selection-text');
    const chipRow = selectionBody.append('div').attr('class', 'ai-chip-row');

    const summaryBlock = wrapper.append('div').attr('class', 'ai-summary');

    // ... (Keep existing summary block code: venueTotals, venueSection, keywordBlock etc.)
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

    // Initialize UI state
    // Force immediate sync with config values if available
    if (currentConfig.model && currentConfig.model !== 'mock') {
        modelSelect.property('value', currentConfig.model);
        if (currentConfig.apiKey) {
            keyInput.property('value', currentConfig.apiKey);
        }
    }
    updateConfigUI();

    function toggleConfigMode() {
        configMode = !configMode;
        configPanel.classed('hidden', !configMode);
        selectionBox.classed('hidden', configMode);

        if (configMode) {
            // Always refresh inputs from state when opening
            modelSelect.property('value', currentConfig.model);
            keyInput.property('value', currentConfig.apiKey || '');
        }
    }

    function saveConfig() {
        const model = modelSelect.property('value');
        const apiKey = keyInput.property('value').trim();

        if (model !== 'mock' && !apiKey) {
            setStatus('请输入 API Key', 'error');
            return;
        }

        currentConfig = { model, apiKey };
        try {
            localStorage.setItem('cv_explorer_ai_config', JSON.stringify(currentConfig));
            console.log('[AI Config] Saved to localStorage:', currentConfig.model);
        } catch (e) {
            console.error('[AI Config] Failed to save:', e);
            setStatus('保存失败', 'error');
            return;
        }

        updateConfigUI();
        toggleConfigMode();

        // Visual feedback
        setStatus('配置已更新', 'ready');
        setTimeout(() => setStatus('待命', 'idle'), 2000);
    }

    function clearConfig() {
        localStorage.removeItem('cv_explorer_ai_config');
        currentConfig = { model: 'mock', apiKey: '' };
        updateConfigUI();
        toggleConfigMode();
        setStatus('配置已清除', 'idle');
    }

    function updateConfigUI() {
        const isMock = currentConfig.model === 'mock';
        const label = models.find(m => m.value === currentConfig.model)?.label || 'Mock';

        configBtn.text(isMock ? '⚙️ 配置 API' : `⚙️ ${label}`);
        configBtn.classed('active', !isMock);

        // Update global AI panel hint if exists
        const globalPanel = d3.select("#global-ai-panel .panel-header");
        if (!globalPanel.empty()) {
            globalPanel.attr('title', `当前模型: ${label}`);
        }
    }

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
        let summary = buildSummary(payload);

        // 1. Pre-render KaTeX formulas BEFORE Markdown parsing
        // This prevents 'marked' from consuming backslashes in \[ \] and \( \)
        if (window.katex) {
            // Replace block math \[ ... \]
            summary = summary.replace(/\\\[([\s\S]*?)\\\]/g, (_, tex) => {
                try {
                    return window.katex.renderToString(tex, { displayMode: true, throwOnError: false });
                } catch (e) {
                    console.warn('KaTeX error (block):', e);
                    return `\\[${tex}\\]`;
                }
            });

            // Replace inline math \( ... \)
            summary = summary.replace(/\\\(([\s\S]*?)\\\)/g, (_, tex) => {
                try {
                    return window.katex.renderToString(tex, { displayMode: false, throwOnError: false });
                } catch (e) {
                    console.warn('KaTeX error (inline):', e);
                    return `\\(${tex}\\)`;
                }
            });
        }

        // 2. Render Markdown using 'marked' library
        if (window.marked) {
            selectionText.classed('is-typing', false)
                .html(window.marked.parse(summary))
                .style('opacity', 0)
                .transition().duration(500).style('opacity', 1);
        } else {
            // Fallback if marked is not loaded
            typewrite(selectionText, summary);
        }

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

        // Check if we already have a cached summary for this exact item
        // AND the user hasn't explicitly requested a regeneration (e.g., via button)
        if (payload.cached && payload.summary && payload.summary.length > 50) {
            console.log("[AI View] Using cached summary for:", payload.title);
            showResult(payload);
            return;
        }

        showLoadingState(payload);

        // 使用后端 API (相对路径以适配 Vercel)
        const apiUrl = '/api/analyze';

        // 模拟延迟或实际请求
        pendingTimer = setTimeout(async () => {
            try {
                // 构造请求数据
                const requestData = {
                    text: payload.title || payload.label || '未命名主题',
                    model: currentConfig.model,
                    api_key: currentConfig.apiKey, // Send stored API Key
                    prompt_type: payload.prompt_type, // Support custom prompt types
                    context: {
                        year: payload.year,
                        venue: payload.venue,
                        citations: payload.citations,
                        value: payload.value,
                        source: payload.source,
                        target: payload.target,
                        // Pass extra context for scholars/papers
                        desc: payload.summary, // Using summary as desc for scholar
                        authors: payload.authors,
                        concepts: payload.concepts
                    }
                };

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestData)
                });

                if (!response.ok) {
                    throw new Error(`Server Error: ${response.status}`);
                }

                const data = await response.json();

                if (data.error) {
                    typewrite(selectionText, `错误: ${data.error}`);
                    setStatus('错误', 'error');
                    return;
                }

                // 合并后端返回的数据
                const resultPayload = {
                    ...payload,
                    summary: data.summary,
                    concepts: data.keywords || [],
                    cached: true // Mark as cached
                };

                // Update global state with the generated summary to prevent re-generation
                // We need to use a special event or direct update to avoid infinite loops if we were to emit 'paperSelected'
                if (state) state.selection = resultPayload;

                showResult(resultPayload);

            } catch (error) {
                console.error("AI Service Error:", error);
                // 降级处理
                if (currentConfig.model === 'mock') {
                    console.warn("Backend unavailable, using local mock fallback.");
                    const fallbackSummary = buildSummary(payload);
                    const fallbackPayload = { ...payload, summary: fallbackSummary + " (Local Fallback)" };
                    showResult(fallbackPayload);
                } else {
                    typewrite(selectionText, "连接 AI 服务失败。请检查后端服务或网络连接。");
                    setStatus('离线', 'error');
                }
            } finally {
                pendingTimer = null;
            }
        }, 500);
    }

    showIdleState();
    const handler = payload => renderSelection(payload);
    dispatcher.on('paperSelected.aiView', handler);

    // Restore previous selection if available
    if (state.selection) {
        console.log("[AI View] Restoring selection:", state.selection.title);
        renderSelection(state.selection);
    }

    return () => {
        dispatcher.on('paperSelected.aiView', null);
        if (typingTimer) clearInterval(typingTimer);
        if (pendingTimer) clearTimeout(pendingTimer);
    };
}
