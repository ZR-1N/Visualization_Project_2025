// web/src/router.js
import { renderOverview } from './views/overview.js';
import { renderLandscape } from './views/landscape.js';
import { renderFlow } from './views/flow.js';
import { renderAiPanel } from './views/ai_panel.js';
import { renderWordCloud } from './views/word_cloud.js';
import { renderLeaderboard } from './views/leaderboard.js';

export function initRouter(containerSelector, dispatcher, state) {
    const routes = {
        'overview': renderOverview,
        'landscape': renderLandscape,
        'flow': renderFlow,
        'wordcloud': renderWordCloud,
        'ai': renderAiPanel,
        'leaderboard': renderLeaderboard
    };

    const mount = d3.select(containerSelector);
    let activeView = null;
    let cleanup = null;
    let currentParams = {};

    function navigateTo(viewName, params = {}) {
        if (!routes[viewName]) {
            console.warn(`未找到视图: ${viewName}`);
            return;
        }

        mount.classed('is-transitioning', true);
        if (typeof cleanup === 'function') {
            cleanup();
        }

        mount.html("");
        activeView = viewName;
        currentParams = params;

        try {
            const maybeCleanup = routes[viewName](mount, state, dispatcher, params);
            cleanup = typeof maybeCleanup === 'function' ? maybeCleanup : null;
        } catch (error) {
            console.error(`Error rendering view ${viewName}:`, error);
            mount.html(`<div class="empty-state" style="color: #f87171;">
                <h3>视图加载失败</h3>
                <p>${error.message}</p>
                <pre style="text-align: left; font-size: 11px; background: rgba(0,0,0,0.3); padding: 10px;">${error.stack}</pre>
            </div>`);
        } finally {
            requestAnimationFrame(() => {
                mount.classed('is-transitioning', false);
            });
        }
        return activeView;
    }

    function refresh() {
        if (activeView) {
            navigateTo(activeView, currentParams);
        }
    }

    return {
        navigateTo,
        refresh,
        getCurrentView: () => activeView
    };
}