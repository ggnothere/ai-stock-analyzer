/**
 * AI Stock Analyzer - Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const analyzeForm = document.getElementById('analyzeForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const btnLoading = analyzeBtn.querySelector('.btn-loading');
    const resultsSection = document.getElementById('resultsSection');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    const apiStatus = document.getElementById('apiStatus');

    // Progress bar elements
    const progressSection = document.getElementById('progressSection');
    const progressBar = document.getElementById('progressBar');
    const progressStep = document.getElementById('progressStep');
    const progressPercent = document.getElementById('progressPercent');
    const progressDetail = document.getElementById('progressDetail');

    let progressTimer = null;

    // Check API keys on load
    checkApiKeys();

    // Progress steps with timing
    const PROGRESS_STEPS = [
        { percent: 5, step: '📡 连接数据源', detail: '正在连接 Alpha Vantage API...', delay: 500 },
        { percent: 15, step: '📡 获取数据', detail: '正在下载股票历史数据...', delay: 2000 },
        { percent: 30, step: '📊 计算指标', detail: '正在计算 RSI、MACD、布林带等技术指标...', delay: 1500 },
        { percent: 40, step: '📈 生成图表', detail: '正在绘制 K 线图和指标图...', delay: 2000 },
        { percent: 55, step: '🤖 AI 分析中', detail: '正在将数据和图表发送给 Gemini...', delay: 3000 },
        { percent: 65, step: '🤖 AI 分析中', detail: 'Gemini 正在分析技术形态...', delay: 5000 },
        { percent: 75, step: '🤖 AI 分析中', detail: 'Gemini 正在生成分析报告...', delay: 8000 },
        { percent: 85, step: '🤖 AI 分析中', detail: '即将完成，请稍候...', delay: 10000 },
        { percent: 90, step: '🤖 AI 分析中', detail: '正在等待 AI 响应...', delay: 15000 },
        { percent: 93, step: '🤖 AI 分析中', detail: '分析内容较多，请耐心等待...', delay: 20000 },
    ];

    // Form submission
    analyzeForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const symbol = document.getElementById('symbol').value.trim().toUpperCase();
        const period = document.getElementById('period').value;
        const model = document.getElementById('model').value;

        if (!symbol) {
            showError('请输入股票代码');
            return;
        }

        // Show loading state
        setLoading(true);
        hideError();
        startProgress(symbol);

        try {
            // Set 2 minute timeout for the request
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000);

            // Helper to make the fetch call
            const doFetch = () => fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({ symbol, period, model }),
                signal: controller.signal
            });

            let response;
            try {
                response = await doFetch();
            } catch (fetchErr) {
                // Auto-retry once on network error (Failed to fetch / connection reset)
                if (fetchErr.name !== 'AbortError') {
                    console.log('[Retry] Network error, retrying in 2s...', fetchErr.message);
                    await new Promise(r => setTimeout(r, 2000));
                    response = await doFetch();
                } else {
                    throw fetchErr;
                }
            }

            clearTimeout(timeoutId);

            // Check HTTP status first
            if (!response.ok) {
                let errorMsg = `服务器错误 (${response.status})`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errData = await response.json();
                        errorMsg = errData.error || errorMsg;
                    } else {
                        const text = await response.text();
                        // Extract useful error info from HTML
                        const match = text.match(/<title>(.*?)<\/title>/i) || text.match(/<h1>(.*?)<\/h1>/i);
                        if (match) errorMsg += `: ${match[1]}`;
                        console.error('Server HTML response:', text.substring(0, 500));
                    }
                } catch (e) { /* ignore parse errors */ }
                throw new Error(errorMsg);
            }

            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Non-JSON response:', text.substring(0, 500));
                throw new Error('服务器返回了非JSON响应，可能是服务器内部错误，请查看服务器日志');
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || '分析失败');
            }

            // Complete progress
            completeProgress();

            // Display results after a short delay for progress animation
            setTimeout(() => {
                hideProgress();
                displayResults(data);
            }, 600);

        } catch (error) {
            hideProgress();
            if (error.name === 'AbortError') {
                showError('请求超时（2分钟），分析时间可能较长，请稍后重试。');
            } else if (error.message === 'Failed to fetch' || error instanceof TypeError) {
                showError('网络连接失败，请检查：\n1. 服务器是否在运行\n2. 网络连接是否正常\n3. 如使用VPN请尝试切换节点');
            } else {
                showError(error.message || '未知错误，请刷新页面后重试');
            }
        } finally {
            setLoading(false);
        }
    });

    /**
     * Start progress bar animation
     */
    function startProgress(symbol) {
        progressSection.style.display = 'block';
        resultsSection.style.display = 'none';
        progressBar.style.width = '0%';
        progressBar.className = 'progress-bar';

        let currentStep = 0;

        function advanceProgress() {
            if (currentStep >= PROGRESS_STEPS.length) return;

            const step = PROGRESS_STEPS[currentStep];
            progressBar.style.width = step.percent + '%';
            progressStep.textContent = step.step;
            progressPercent.textContent = step.percent + '%';
            progressDetail.textContent = step.detail.replace('股票', symbol || '股票');

            currentStep++;
            if (currentStep < PROGRESS_STEPS.length) {
                progressTimer = setTimeout(advanceProgress, PROGRESS_STEPS[currentStep].delay);
            }
        }

        // Start first step
        advanceProgress();
    }

    /**
     * Complete progress to 100%
     */
    function completeProgress() {
        if (progressTimer) {
            clearTimeout(progressTimer);
            progressTimer = null;
        }
        progressBar.style.width = '100%';
        progressBar.classList.add('complete');
        progressStep.textContent = '✅ 分析完成';
        progressPercent.textContent = '100%';
        progressDetail.textContent = '正在渲染结果...';
    }

    /**
     * Hide progress bar
     */
    function hideProgress() {
        if (progressTimer) {
            clearTimeout(progressTimer);
            progressTimer = null;
        }
        progressSection.style.display = 'none';
    }

    /**
     * Check which API keys are configured
     */
    async function checkApiKeys() {
        try {
            const response = await fetch('/api/check-keys');
            const data = await response.json();

            apiStatus.innerHTML = `
                <span class="status-item">
                    <span class="status-dot ${data.gemini ? 'active' : 'inactive'}"></span>
                    Gemini ${data.gemini ? '✓' : '✗'}
                </span>
                <span class="status-item">
                    <span class="status-dot ${data.alpha_vantage ? 'active' : 'inactive'}"></span>
                    Alpha Vantage ${data.alpha_vantage ? '✓' : '✗'}
                </span>
            `;
        } catch (error) {
            console.error('Failed to check API keys:', error);
        }
    }

    /**
     * Display analysis results
     */
    function displayResults(data) {
        resultsSection.style.display = 'flex';

        // Stock info
        const currency = data.stock_info.currency === 'CNY' ? '¥' : '$';
        document.getElementById('stockSymbol').textContent = data.symbol;
        document.getElementById('stockName').textContent = data.stock_info.name || data.symbol;
        document.getElementById('stockPrice').textContent = `${currency}${data.stats.latest_close}`;

        // Price change
        const changeEl = document.getElementById('stockChange');
        const change = data.stats.period_change;
        changeEl.textContent = `${change >= 0 ? '+' : ''}${change}%`;
        changeEl.className = `change ${change >= 0 ? 'positive' : 'negative'}`;

        // Indicators
        const indicators = data.indicators;

        const rsiEl = document.getElementById('rsiValue');
        rsiEl.textContent = indicators.rsi_14 != null ? indicators.rsi_14 : 'N/A';
        rsiEl.className = `indicator-value ${indicators.rsi_14 != null ? getRSIClass(indicators.rsi_14) : ''}`;

        document.getElementById('ma20Value').textContent = indicators.ma_20 != null ? `${currency}${indicators.ma_20}` : 'N/A';
        document.getElementById('ma50Value').textContent = indicators.ma_50 != null ? `${currency}${indicators.ma_50}` : 'N/A';

        const macdEl = document.getElementById('macdValue');
        macdEl.textContent = indicators.macd != null ? indicators.macd.toFixed(2) : 'N/A';
        macdEl.className = `indicator-value ${indicators.macd != null ? (indicators.macd >= 0 ? 'bullish' : 'bearish') : ''}`;

        // Charts (multi-timeframe)
        const chartPlaceholder = document.getElementById('chartPlaceholder');
        const chartUrls = data.chart_urls || {};

        // Load all available charts
        const tfMap = {
            daily: document.getElementById('chartImageDaily'),
            weekly: document.getElementById('chartImageWeekly'),
            monthly: document.getElementById('chartImageMonthly')
        };

        let hasAnyChart = false;
        for (const [tf, imgEl] of Object.entries(tfMap)) {
            if (chartUrls[tf]) {
                imgEl.src = chartUrls[tf] + '?t=' + Date.now();
                imgEl.dataset.loaded = 'true';
                hasAnyChart = true;
            } else {
                imgEl.dataset.loaded = 'false';
            }
        }

        if (hasAnyChart) {
            chartPlaceholder.style.display = 'none';
            // Show daily chart by default
            showChart('daily');
        }

        // Setup tab click handlers
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.onclick = function () {
                const tf = this.dataset.tf;
                showChart(tf);
            };
        });

        // AI Analysis
        document.getElementById('modelUsed').textContent = data.analysis.model || data.model;

        const analysisContent = document.getElementById('analysisContent');
        if (data.analysis.success) {
            analysisContent.innerHTML = formatMarkdown(data.analysis.analysis);
        } else {
            analysisContent.innerHTML = `<p class="error-text">分析出错: ${data.analysis.error}</p>`;
        }

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Show chart by timeframe
     */
    function showChart(tf) {
        // Update tabs
        document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
        const activeTab = document.querySelector(`.chart-tab[data-tf="${tf}"]`);
        if (activeTab) activeTab.classList.add('active');

        // Update images
        document.querySelectorAll('.chart-img').forEach(img => {
            img.style.display = 'none';
            img.classList.remove('active');
        });

        const targetImg = document.getElementById('chartImage' + tf.charAt(0).toUpperCase() + tf.slice(1));
        if (targetImg && targetImg.dataset.loaded === 'true') {
            targetImg.style.display = 'block';
            targetImg.classList.add('active');
        } else {
            // Show placeholder for unavailable timeframe
            const placeholder = document.getElementById('chartPlaceholder');
            placeholder.style.display = 'flex';
            placeholder.textContent = `${tf === 'weekly' ? '周' : '月'}K线数据不足，无法生成图表`;
        }
    }

    /**
     * Get CSS class based on RSI value
     */
    function getRSIClass(rsi) {
        if (rsi >= 70) return 'bearish';
        if (rsi <= 30) return 'bullish';
        return 'neutral';
    }

    /**
     * Simple markdown to HTML converter
     */
    function formatMarkdown(text) {
        if (!text) return '';

        let html = text
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Code
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // Lists
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
            // Paragraphs
            .replace(/\n\n/g, '</p><p>')
            // Line breaks
            .replace(/\n/g, '<br>');

        // Wrap in paragraph
        html = '<p>' + html + '</p>';

        // Clean up list items
        html = html.replace(/<\/li><br>/g, '</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
        html = html.replace(/<\/ul><ul>/g, '');

        return html;
    }

    /**
     * Show/hide loading state
     */
    function setLoading(loading) {
        analyzeBtn.disabled = loading;
        btnText.style.display = loading ? 'none' : 'inline-flex';
        btnLoading.style.display = loading ? 'inline-flex' : 'none';
    }

    /**
     * Show error message
     */
    function showError(message) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        resultsSection.style.display = 'none';
    }

    /**
     * Hide error message
     */
    function hideError() {
        errorMessage.style.display = 'none';
    }
});
