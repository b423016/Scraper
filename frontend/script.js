/**
 * TrustScrape — Frontend Logic
 * Connects to the FastAPI backend and renders scraping results.
 */

// ═══ State ════════════════════════════════════════════════════════════════
const state = {
    apiBase: window.location.origin || 'http://localhost:8000',
    connected: false,
    results: [],
    processing: false,
};

// ═══ DOM References ═══════════════════════════════════════════════════════
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    apiBaseUrl:       $('#apiBaseUrl'),
    testConnectionBtn: $('#testConnectionBtn'),
    statusDot:        $('#statusDot'),
    statusText:       $('#statusText'),

    tabSingle:        $('#tabSingle'),
    tabBatch:         $('#tabBatch'),
    singleTab:        $('#singleTab'),
    batchTab:         $('#batchTab'),

    singleUrlInput:   $('#singleUrlInput'),
    scrapeSingleBtn:  $('#scrapeSingleBtn'),
    batchUrlInput:    $('#batchUrlInput'),
    scrapeBatchBtn:   $('#scrapeBatchBtn'),
    urlCount:         $('#urlCount'),

    progressSection:  $('#progressSection'),
    progressLabel:    $('#progressLabel'),
    progressPercent:  $('#progressPercent'),
    progressFill:     $('#progressFill'),
    progressLog:      $('#progressLog'),

    summaryGrid:      $('#summaryGrid'),
    totalSources:     $('#totalSources'),
    avgTrust:         $('#avgTrust'),
    blogCount:        $('#blogCount'),
    ytCount:          $('#ytCount'),
    pmCount:          $('#pmCount'),
    resultsGrid:      $('#resultsGrid'),
    emptyState:       $('#emptyState'),

    refreshResultsBtn: $('#refreshResultsBtn'),
    downloadJsonBtn:  $('#downloadJsonBtn'),
};


// ═══ Initialization ═══════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    // Auto-detect backend URL if served from the same host
    if (window.location.protocol.startsWith('http')) {
        dom.apiBaseUrl.value = window.location.origin;
        state.apiBase = window.location.origin;
    }
    setupEventListeners();
    testConnection();
});


function setupEventListeners() {
    // API config
    dom.apiBaseUrl.addEventListener('change', () => {
        state.apiBase = dom.apiBaseUrl.value.replace(/\/+$/, '');
        testConnection();
    });
    dom.testConnectionBtn.addEventListener('click', testConnection);

    // Tabs
    dom.tabSingle.addEventListener('click', () => switchTab('single'));
    dom.tabBatch.addEventListener('click', () => switchTab('batch'));

    // Scraping
    dom.scrapeSingleBtn.addEventListener('click', scrapeSingle);
    dom.scrapeBatchBtn.addEventListener('click', scrapeBatch);

    // Enter key on single URL input
    dom.singleUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') scrapeSingle();
    });

    // Batch URL counter
    dom.batchUrlInput.addEventListener('input', updateUrlCount);

    // Results
    dom.refreshResultsBtn.addEventListener('click', loadResults);
    dom.downloadJsonBtn.addEventListener('click', downloadJson);

    // Smooth scroll for nav links
    $$('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const id = link.getAttribute('href');
            document.querySelector(id)?.scrollIntoView({ behavior: 'smooth' });
            $$('.nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // Get Started button
    $('#getStartedBtn')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelector('#scraper')?.scrollIntoView({ behavior: 'smooth' });
    });
}


// ═══ Connection ═══════════════════════════════════════════════════════════

async function testConnection() {
    state.apiBase = dom.apiBaseUrl.value.replace(/\/+$/, '');
    try {
        const resp = await fetch(`${state.apiBase}/api/health`, { signal: AbortSignal.timeout(5000) });
        if (resp.ok) {
            state.connected = true;
            dom.statusDot.classList.add('connected');
            dom.statusText.textContent = 'Connected';
            loadResults();
        } else {
            throw new Error('Bad response');
        }
    } catch {
        state.connected = false;
        dom.statusDot.classList.remove('connected');
        dom.statusText.textContent = 'Disconnected';
    }
}


// ═══ Tabs ═════════════════════════════════════════════════════════════════

function switchTab(tab) {
    if (tab === 'single') {
        dom.tabSingle.classList.add('active');
        dom.tabBatch.classList.remove('active');
        dom.singleTab.classList.add('active');
        dom.batchTab.classList.remove('active');
    } else {
        dom.tabBatch.classList.add('active');
        dom.tabSingle.classList.remove('active');
        dom.batchTab.classList.add('active');
        dom.singleTab.classList.remove('active');
    }
}

function updateUrlCount() {
    const lines = dom.batchUrlInput.value.split('\n').filter(l => l.trim());
    dom.urlCount.textContent = `${lines.length} URL${lines.length !== 1 ? 's' : ''}`;
}


// ═══ Scraping ═════════════════════════════════════════════════════════════

async function scrapeSingle() {
    const url = dom.singleUrlInput.value.trim();
    if (!url) return;

    if (!state.connected) {
        logMessage('Backend not connected. Check your API URL.', 'error');
        return;
    }

    setProcessing(true);
    showProgress('Scraping URL…', 0);
    logMessage(`Starting: ${url}`, 'info');

    try {
        showProgress('Extracting & scoring…', 30);
        const resp = await fetch(`${state.apiBase}/api/scrape/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        showProgress('Done!', 100);
        logMessage(`✓ Processed: ${data.result.title || url}  (trust=${data.result.trust_score})`, 'success');

        state.results.push(data.result);
        renderResults(state.results);
        dom.singleUrlInput.value = '';

    } catch (err) {
        logMessage(`✗ Error: ${err.message}`, 'error');
        showProgress('Failed', 0);
    } finally {
        setProcessing(false);
    }
}


async function scrapeBatch() {
    const lines = dom.batchUrlInput.value.split('\n').map(l => l.trim()).filter(l => l);
    if (!lines.length) return;

    if (!state.connected) {
        logMessage('Backend not connected. Check your API URL.', 'error');
        return;
    }

    setProcessing(true);
    showProgress(`Processing ${lines.length} URLs…`, 0);
    logMessage(`Batch scraping ${lines.length} URLs…`, 'info');

    try {
        showProgress('Sending request…', 10);

        const resp = await fetch(`${state.apiBase}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: lines }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }

        showProgress('Processing results…', 80);
        const data = await resp.json();

        showProgress('Complete!', 100);
        logMessage(`✓ Processed ${data.processed}/${data.total_urls} URLs (${data.failed} failed)`, 'success');

        data.results.forEach(r => {
            logMessage(`  → ${r.title || r.source_url}  trust=${r.trust_score}`, 'success');
        });

        state.results = data.results;
        renderResults(state.results);

    } catch (err) {
        logMessage(`✗ Batch error: ${err.message}`, 'error');
        showProgress('Failed', 0);
    } finally {
        setProcessing(false);
    }
}


// ═══ Results ══════════════════════════════════════════════════════════════

async function loadResults() {
    if (!state.connected) return;

    try {
        const resp = await fetch(`${state.apiBase}/api/results`);
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.results && data.results.length) {
            state.results = data.results;
            renderResults(state.results);
        }
    } catch {
        // Silently fail
    }
}


function renderResults(results) {
    if (!results.length) {
        dom.emptyState.style.display = '';
        dom.summaryGrid.classList.add('hidden');
        return;
    }

    dom.emptyState.style.display = 'none';
    dom.summaryGrid.classList.remove('hidden');

    // Summary
    const blogCount = results.filter(r => r.source_type === 'blog').length;
    const ytCount = results.filter(r => r.source_type === 'youtube').length;
    const pmCount = results.filter(r => r.source_type === 'pubmed').length;
    const avgTrust = results.reduce((sum, r) => sum + (r.trust_score || 0), 0) / results.length;

    dom.totalSources.textContent = results.length;
    dom.avgTrust.textContent = avgTrust.toFixed(2);
    dom.blogCount.textContent = blogCount;
    dom.ytCount.textContent = ytCount;
    dom.pmCount.textContent = pmCount;

    // Cards
    const cardsHtml = results.map((r, i) => buildResultCard(r, i)).join('');
    dom.resultsGrid.innerHTML = cardsHtml;

    // Animate trust rings
    requestAnimationFrame(() => {
        $$('.trust-score-ring .ring-fill').forEach(ring => {
            const score = parseFloat(ring.dataset.score) || 0;
            const offset = 157 - (157 * score);
            ring.style.strokeDashoffset = offset;
        });

        $$('.trust-factor-fill').forEach(bar => {
            bar.style.width = bar.dataset.width;
        });
    });

    // Expand button listeners
    $$('.expand-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const details = btn.parentElement.querySelector('.result-card-details');
            btn.classList.toggle('expanded');
            details.classList.toggle('visible');
            btn.querySelector('span').textContent = btn.classList.contains('expanded') ? 'Hide Details' : 'Show Details';
        });
    });
}


function buildResultCard(result, index) {
    const score = result.trust_score || 0;
    const scoreColor = score >= 0.7 ? '#34d399' : score >= 0.4 ? '#fbbf24' : '#fb7185';
    const signals = result.trust_signals || {};

    const tags = (result.topic_tags || [])
        .map(tag => `<span class="topic-tag">${escapeHtml(tag)}</span>`)
        .join('');

    const chunks = (result.content_chunks || [])
        .map((c, i) => `
            <div class="chunk-item">
                <span class="chunk-index">#${i + 1}</span>
                ${escapeHtml(c)}
            </div>
        `)
        .join('');

    const totalChunks = (result.content_chunks || []).length;
    const wordCount = (result.content_chunks || []).reduce((sum, c) => sum + c.split(/\s+/).length, 0);

    return `
    <div class="result-card" style="animation-delay: ${index * 0.1}s">
        <div class="result-card-header">
            <div class="result-card-left">
                <span class="source-badge ${result.source_type}">${result.source_type}</span>
                <span class="result-title" title="${escapeHtml(result.title || result.source_url)}">${escapeHtml(result.title || result.source_url)}</span>
            </div>
            <div class="trust-score-badge">
                <div class="trust-score-ring">
                    <svg width="56" height="56" viewBox="0 0 56 56">
                        <circle class="ring-bg" cx="28" cy="28" r="25" fill="none" stroke-width="4"/>
                        <circle class="ring-fill" data-score="${score}" cx="28" cy="28" r="25" fill="none" stroke="${scoreColor}" stroke-width="4" stroke-linecap="round"/>
                    </svg>
                    <span class="trust-score-value" style="color: ${scoreColor}">${score.toFixed(2)}</span>
                </div>
            </div>
        </div>

        <div class="result-card-body">
            <div class="result-meta">
                <div class="meta-item">
                    <span class="meta-label">Author</span>
                    <span class="meta-value">${escapeHtml(result.author || 'unknown')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Date</span>
                    <span class="meta-value">${escapeHtml(result.published_date || 'unknown')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Language</span>
                    <span class="meta-value">${escapeHtml(result.language || 'unknown')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Region</span>
                    <span class="meta-value">${escapeHtml(result.region || 'unknown')}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Chunks</span>
                    <span class="meta-value">${totalChunks}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Words</span>
                    <span class="meta-value">${wordCount.toLocaleString()}</span>
                </div>
            </div>

            ${tags ? `<div class="topic-tags">${tags}</div>` : ''}

            <div class="trust-breakdown">
                ${buildTrustFactor('Author', signals.author_credibility)}
                ${buildTrustFactor('Quality', signals.content_quality)}
                ${buildTrustFactor('Domain', signals.domain_authority)}
                ${buildTrustFactor('Recency', signals.recency_score)}
                ${buildTrustFactor('Disclaimer', signals.medical_disclaimer_score)}
            </div>
        </div>

        <button class="expand-btn">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 5l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span>Show Details</span>
        </button>

        <div class="result-card-details">
            ${result.description ? `
                <div style="margin-bottom: 16px;">
                    <h4 style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 8px;">Description</h4>
                    <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">${escapeHtml(result.description)}</p>
                </div>
            ` : ''}
            ${chunks ? `
                <div class="chunks-section">
                    <h4>Content Chunks (${totalChunks} total — ${wordCount.toLocaleString()} words)</h4>
                    ${chunks}
                </div>
            ` : ''}
            <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
                <a href="${escapeHtml(result.source_url)}" target="_blank" rel="noopener" style="font-size: 13px; color: var(--accent-cyan); text-decoration: underline;">View Source →</a>
                <span style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">JSON: output/scraped_data.json</span>
            </div>
        </div>
    </div>`;
}


function buildTrustFactor(label, value) {
    const val = value ?? 0;
    const pct = Math.round(val * 100);
    const color = val >= 0.7 ? 'var(--accent-emerald)' : val >= 0.4 ? 'var(--accent-amber)' : 'var(--accent-rose)';

    return `
    <div class="trust-factor">
        <div class="trust-factor-label">${label}</div>
        <div class="trust-factor-bar">
            <div class="trust-factor-fill" data-width="${pct}%" style="width: 0%; background: ${color};"></div>
        </div>
        <div class="trust-factor-value" style="color: ${color}">${val.toFixed(2)}</div>
    </div>`;
}


// ═══ UI Helpers ═══════════════════════════════════════════════════════════

function setProcessing(active) {
    state.processing = active;
    dom.scrapeSingleBtn.disabled = active;
    dom.scrapeBatchBtn.disabled = active;
}


function showProgress(label, percent) {
    dom.progressSection.classList.remove('hidden');
    dom.progressLabel.textContent = label;
    dom.progressPercent.textContent = `${percent}%`;
    dom.progressFill.style.width = `${percent}%`;
}


function logMessage(msg, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    dom.progressLog.prepend(entry);
}


function downloadJson() {
    if (!state.results.length) return;

    const blob = new Blob([JSON.stringify(state.results, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'scraped_data.json';
    a.click();
    URL.revokeObjectURL(url);
}


function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
