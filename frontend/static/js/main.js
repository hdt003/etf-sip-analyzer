// Buy the Dip Analyzer — Main JS (NaN-safe, real data only)
let selectedModalSymbol = null;
let selectedModalName = null;
let selectedModalType = null;

// All known tabs
const ALL_TABS = ["tab-peak", "tab-indices", "tab-alerts", "tab-sip"];

document.addEventListener("DOMContentLoaded", () => {
    loadPeakAnalysis();
    setupDirectSearchAutocomplete();
    setupModalSearchAutocomplete();
    runSipCalculator();
});

// ─── Loader ───────────────────────────────────────────────
function showLoader(msg = "FETCHING LIVE DATA...") {
    const el = document.getElementById("futuristic-loader");
    const txt = document.getElementById("futuristic-loader-text");
    if (txt) txt.innerText = msg;
    if (el) el.classList.remove("hidden");
}
function hideLoader() {
    const el = document.getElementById("futuristic-loader");
    if (el) el.classList.add("hidden");
}

// ─── Tab Switching ────────────────────────────────────────
function switchTab(tabId) {
    ALL_TABS.forEach(t => {
        document.getElementById(t)?.classList.add("hidden");
        const btn = document.getElementById(`btn-${t}`);
        if (btn) {
            btn.classList.remove("bg-blue-600", "text-white");
            btn.classList.add("text-slate-400", "hover:bg-slate-800");
        }
    });

    document.getElementById(tabId)?.classList.remove("hidden");
    const activeBtn = document.getElementById(`btn-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.remove("text-slate-400", "hover:bg-slate-800");
        activeBtn.classList.add("bg-blue-600", "text-white");
    }

    // Lazy-load data for Indices and Alerts tabs
    if (tabId === "tab-indices") loadIndices();
    if (tabId === "tab-alerts") loadAlerts();
}

// ─── Helper: safe number formatting ───────────────────────
function fmtNav(val) {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "—";
    return `₹${parseFloat(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
}
function fmtIdx(val) {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "—";
    return parseFloat(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtPct(val) {
    if (val === null || val === undefined || isNaN(val)) return "—";
    return `${parseFloat(val) >= 0 ? "+" : ""}${parseFloat(val).toFixed(2)}%`;
}

// ─── 1. Peak Analysis Tables ──────────────────────────────
async function loadPeakAnalysis() {
    showLoader("CALCULATING PEAK NAV MATRIX & BUY SCORES...");
    try {
        const res = await fetch("/api/v1/peak-analysis");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const items = await res.json();
        renderPeakTables(items);
    } catch (e) {
        const etfTbody = document.getElementById("etf-analysis-tbody");
        const mfTbody = document.getElementById("mf-analysis-tbody");
        const errHtml = `<tr><td colspan="7" class="px-4 py-6 text-center text-rose-400 text-xs">Error loading data: ${e.message}</td></tr>`;
        if (etfTbody) etfTbody.innerHTML = errHtml;
        if (mfTbody) mfTbody.innerHTML = errHtml;
    } finally {
        hideLoader();
    }
}

function renderPeakTables(items) {
    const etfTbody = document.getElementById("etf-analysis-tbody");
    const mfTbody = document.getElementById("mf-analysis-tbody");
    if (!etfTbody || !mfTbody) return;

    etfTbody.innerHTML = "";
    mfTbody.innerHTML = "";

    const etfs = items.filter(x => x.asset_type === "ETF");
    const mfs = items.filter(x => x.asset_type === "MUTUAL_FUND");

    if (etfs.length === 0) {
        etfTbody.innerHTML = `<tr><td colspan="7" class="px-4 py-8 text-center text-slate-500 text-xs">
            No ETFs tracked yet.<br><span class="text-emerald-400">Search an ETF (e.g. HDFCSILVER) above to fetch & add</span>
        </td></tr>`;
    } else {
        etfs.forEach(item => etfTbody.appendChild(createRowHTML(item)));
    }

    if (mfs.length === 0) {
        mfTbody.innerHTML = `<tr><td colspan="7" class="px-4 py-8 text-center text-slate-500 text-xs">
            No Mutual Funds tracked yet.<br><span class="text-blue-400">Search a Mutual Fund (e.g. SBI Small Cap) above to fetch & add</span>
        </td></tr>`;
    } else {
        mfs.forEach(item => mfTbody.appendChild(createRowHTML(item)));
    }
}

function createRowHTML(item, isRetryRow = false) {
    const isError = item.color_status === "Error";
    let dipBadge = "badge-green";
    if (item.color_status === "Yellow") dipBadge = "badge-yellow";
    if (item.color_status === "Red")    dipBadge = "badge-red";
    if (isError)                         dipBadge = "badge-red";

    let scoreBadge = "badge-blue";
    if (item.buy_score >= 60) scoreBadge = "badge-green";
    else if (item.buy_score <= 40) scoreBadge = "badge-red";

    const todayPct = parseFloat(item.today_change_pct || 0);
    const todayColor = todayPct >= 0 ? "text-emerald-400" : "text-rose-400";
    const todaySign = todayPct >= 0 ? "▲" : "▼";

    const symEsc = item.symbol_or_code.replace(/'/g, "\\'");

    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-800/70 hover:bg-slate-800/30 transition-colors";
    tr.setAttribute("data-symbol", item.symbol_or_code);
    tr.setAttribute("data-type", item.asset_type);

    if (isError) {
        tr.innerHTML = `
            <td class="px-3 py-2.5 col-name">
                <div class="font-semibold text-slate-400 text-xs leading-tight">${item.name}</div>
                <div class="text-[10px] text-slate-600 font-mono mt-0.5">${item.symbol_or_code}</div>
            </td>
            <td colspan="4" class="px-3 py-2.5">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="badge-red text-[10px] px-2 py-0.5 rounded font-bold">⚠ Fetch Error</span>
                    <span class="text-[10px] text-slate-500 leading-tight max-w-[160px] md:max-w-xs truncate" title="${item.score_reasons || ''}">${item.score_reasons || 'Connection timeout'}</span>
                    <button
                        onclick="retryRow('${symEsc}', this)"
                        class="retry-btn flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 rounded text-[10px] font-bold transition-all"
                        title="Retry fetching this row">
                        <span class="retry-icon">🔄</span> Retry
                    </button>
                </div>
            </td>
            <td class="px-3 py-2.5"></td>
            <td class="px-3 py-2.5">
                <button onclick="removeHolding('${symEsc}')" class="text-slate-600 hover:text-rose-400 transition-colors text-sm" title="Remove">✕</button>
            </td>
        `;
    } else {
        tr.innerHTML = `
            <td class="px-3 md:px-4 py-3 col-name">
                <div class="font-semibold text-slate-200 text-xs leading-tight">${item.name}</div>
                <div class="text-[10px] text-slate-500 font-mono mt-0.5">${item.symbol_or_code}</div>
            </td>
            <td class="px-3 md:px-4 py-3 text-slate-100 font-semibold text-xs whitespace-nowrap col-price">${fmtNav(item.current_price)}</td>
            <td class="px-3 md:px-4 py-3 whitespace-nowrap col-today">
                <span class="${todayColor} text-xs font-semibold">${todaySign} ${Math.abs(todayPct).toFixed(2)}%</span>
            </td>
            <td class="px-3 md:px-4 py-3 text-slate-300 text-xs whitespace-nowrap col-ath">${fmtNav(item.ath_or_peak_nav)}</td>
            <td class="px-3 md:px-4 py-3 whitespace-nowrap col-down">
                <span class="${dipBadge} text-xs px-2.5 py-1 rounded-full font-bold">-${item.down_pct}%</span>
            </td>
            <td class="px-3 md:px-4 py-3 col-score">
                <span class="${scoreBadge} text-[10px] px-2 py-0.5 rounded-full font-semibold">${item.buy_score}/100 · ${item.buy_recommendation}</span>
                <div class="text-[10px] text-slate-500 mt-1 leading-tight hidden md:block">${item.score_reasons}</div>
            </td>
            <td class="px-3 md:px-4 py-3 col-remove">
                <button onclick="removeHolding('${symEsc}')" class="text-slate-500 hover:text-rose-400 transition-colors text-sm" title="Remove">✕</button>
            </td>
        `;
    }
    return tr;
}

// ─── Remove holding ───────────────────────────────────────
async function removeHolding(symbol) {
    try {
        const res = await fetch("/api/v1/holdings");
        const holdings = await res.json();
        const h = holdings.find(x => x.symbol_or_code === symbol);
        if (!h) return;
        await fetch(`/api/v1/holdings/${h.id}`, { method: "DELETE" });
        await loadPeakAnalysis();
    } catch (e) {
        console.error("Remove error:", e);
    }
}

// ─── Retry a single error row in-place ────────────────────
async function retryRow(symbol, btnEl) {
    const tr = btnEl.closest("tr");
    if (!tr) return;

    const retryIcon = btnEl.querySelector(".retry-icon");
    if (retryIcon) retryIcon.textContent = "⏳";
    btnEl.disabled = true;
    btnEl.classList.add("opacity-60");

    try {
        const res = await fetch(`/api/v1/prices/analyze/${encodeURIComponent(symbol)}`);
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        const newRow = createRowHTML(data);
        tr.replaceWith(newRow);
    } catch (err) {
        if (retryIcon) retryIcon.textContent = "🔄";
        btnEl.disabled = false;
        btnEl.classList.remove("opacity-60");
        btnEl.title = `Last error: ${err.message}`;
        btnEl.classList.add("border-rose-500/40", "text-rose-400");
        btnEl.classList.remove("border-amber-500/30", "text-amber-400");
    }
}

// ─── 2. Direct API Fetcher ────────────────────────────────
async function fetchAndAnalyzeDirectly(code = null) {
    const inputEl = document.getElementById("direct-api-input");
    const inputVal = code || (inputEl ? inputEl.value.trim() : "");
    if (!inputVal) return;

    const dd = document.getElementById("direct-search-dropdown");
    if (dd) dd.classList.add("hidden");

    let symbol = inputVal;
    const m = inputVal.match(/\(([^)]+)\)$/);
    if (m) symbol = m[1];

    showLoader(`QUERYING MFAPI FOR [ ${symbol.toUpperCase()} ]...`);
    const resultContainer = document.getElementById("direct-fetch-result");

    try {
        const res = await fetch(`/api/v1/prices/analyze/${encodeURIComponent(symbol)}`);
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        renderDirectResult(data);
    } catch (err) {
        if (resultContainer) {
            resultContainer.innerHTML = `<div style="grid-column:1/-1;color:#f87171;font-size:11px;padding:8px 0;">⚠ ${err.message}</div>`;
            resultContainer.style.display = "grid";
        }
    } finally {
        hideLoader();
    }
}

function renderDirectResult(data) {
    const container = document.getElementById("direct-fetch-result");
    if (!container) return;

    let badgeCls = "badge-green";
    if (data.color_status === "Yellow") badgeCls = "badge-yellow";
    if (data.color_status === "Red")    badgeCls = "badge-red";

    const todayPct = parseFloat(data.today_change_pct || 0);
    const todayColor = todayPct >= 0 ? "text-emerald-400" : "text-rose-400";
    const todaySign = todayPct >= 0 ? "▲" : "▼";

    let scoreBadgeCls = "badge-blue";
    if (data.buy_score >= 60) scoreBadgeCls = "badge-green";
    else if (data.buy_score <= 40) scoreBadgeCls = "badge-red";

    container.innerHTML = `
        <div style="grid-column:span 2;">
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Scheme / Asset</div>
            <div style="font-weight:700;color:#f1f5f9;font-size:12px;margin-top:3px;line-height:1.3;">${data.name}</div>
            <div style="font-size:10px;color:#94a3b8;font-family:monospace;margin-top:2px;">${data.symbol_or_code} · ${data.asset_type} · ${data.data_source}</div>
        </div>
        <div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;">Current NAV</div>
            <div style="font-weight:700;color:#f1f5f9;font-size:13px;margin-top:3px;">${fmtNav(data.current_price)}</div>
            <div style="font-size:11px;font-weight:600;" class="${todayColor}">${todaySign} ${Math.abs(todayPct).toFixed(2)}% today</div>
        </div>
        <div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;">ATH / Peak NAV</div>
            <div style="font-weight:700;color:#f1f5f9;font-size:13px;margin-top:3px;">${fmtNav(data.ath_or_peak_nav)}</div>
            ${data.ath_date ? `<div style="font-size:10px;color:#64748b;">${data.ath_date}</div>` : ""}
        </div>
        <div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;">Dip &amp; Score</div>
            <div style="display:flex;align-items:center;gap:6px;margin-top:5px;flex-wrap:wrap;">
                <span class="${badgeCls}" style="font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">-${data.down_pct}%</span>
                <span class="${scoreBadgeCls}" style="font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">${data.buy_score}/100</span>
            </div>
            <div style="font-size:10px;color:#64748b;margin-top:3px;">${data.buy_recommendation}</div>
        </div>
    `;
    container.style.display = "grid";
    if (window.innerWidth >= 640) {
        container.style.gridTemplateColumns = "2fr 1fr 1fr 1fr";
    } else {
        container.style.gridTemplateColumns = "repeat(2,1fr)";
    }
}

// ─── 3. Market Indices Tab ────────────────────────────────
let indicesLoaded = false;

async function loadIndices() {
    // Only show full loader on first load; use button spin on refresh
    const grid = document.getElementById("indices-grid");
    const tbody = document.getElementById("indices-tbody");
    const btn = document.getElementById("btn-refresh-indices");

    if (!indicesLoaded) {
        // Show skeleton cards
        if (grid) grid.innerHTML = `
            <div class="index-card-skeleton"></div>
            <div class="index-card-skeleton"></div>
            <div class="index-card-skeleton"></div>
            <div class="index-card-skeleton"></div>
        `;
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-8 text-center text-slate-500 text-xs">Fetching live index data...</td></tr>`;
    }

    if (btn) { btn.disabled = true; btn.textContent = "⏳ Loading..."; }

    try {
        const res = await fetch("/api/v1/indices");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderIndexCards(data);
        renderIndexTable(data);
        indicesLoaded = true;
    } catch (e) {
        if (grid) grid.innerHTML = `<div style="grid-column:1/-1" class="text-center text-rose-400 text-xs py-10">⚠ Failed to load indices: ${e.message}</div>`;
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-6 text-center text-rose-400 text-xs">Error: ${e.message}</td></tr>`;
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = "🔄 Refresh Indices"; }
    }
}

function _indexColorClasses(idx) {
    const colorMap = {
        blue:   { ring: "border-blue-500",   glow: "shadow-blue-500/20",   pill: "badge-blue",   text: "text-blue-400",   bg: "from-blue-600/20 to-blue-500/5" },
        indigo: { ring: "border-indigo-500",  glow: "shadow-indigo-500/20", pill: "badge-blue",   text: "text-indigo-400", bg: "from-indigo-600/20 to-indigo-500/5" },
        violet: { ring: "border-violet-500",  glow: "shadow-violet-500/20", pill: "badge-blue",   text: "text-violet-400", bg: "from-violet-600/20 to-violet-500/5" },
        amber:  { ring: "border-amber-500",   glow: "shadow-amber-500/20",  pill: "badge-yellow", text: "text-amber-400",  bg: "from-amber-600/20 to-amber-500/5" },
    };
    return colorMap[idx.color] || colorMap.blue;
}

function renderIndexCards(data) {
    const grid = document.getElementById("indices-grid");
    if (!grid) return;
    grid.innerHTML = "";

    data.forEach(idx => {
        const cls = _indexColorClasses(idx);
        const isOk = idx.status === "ok";

        const todayPct = parseFloat(idx.today_change_pct || 0);
        const todayColor = todayPct >= 0 ? "text-emerald-400" : "text-rose-400";
        const todaySign = todayPct >= 0 ? "▲" : "▼";
        const todayArrow = todayPct >= 0 ? "↑" : "↓";

        let dipBadge = "badge-green";
        if (idx.color_status === "Yellow") dipBadge = "badge-yellow";
        if (idx.color_status === "Red")    dipBadge = "badge-red";

        const downPct = parseFloat(idx.down_from_ath_pct || 0);
        // Arc bar: 0% down = full green arc, 30% down = full red
        const arcPct = Math.min(100, Math.max(0, 100 - (downPct / 30) * 100));
        const arcColor = dipBadge === "badge-green" ? "#34d399" : dipBadge === "badge-yellow" ? "#fbbf24" : "#f87171";

        const card = document.createElement("div");
        card.className = `index-card glass-card rounded-2xl border-t-4 ${cls.ring} p-5 flex flex-col gap-3 transition-all hover:shadow-lg hover:${cls.glow} cursor-default`;

        card.innerHTML = isOk ? `
            <!-- Top: label + today change -->
            <div class="flex items-start justify-between">
                <div>
                    <div class="text-[10px] font-bold uppercase tracking-widest ${cls.text} mb-0.5">${idx.label}</div>
                    <div class="text-sm font-extrabold text-slate-100 leading-tight">${idx.display_name}</div>
                    <div class="text-[10px] text-slate-500 mt-0.5 font-mono">${idx.ticker}</div>
                </div>
                <div class="text-right">
                    <div class="${todayColor} text-sm font-bold">${todaySign} ${Math.abs(todayPct).toFixed(2)}%</div>
                    <div class="text-[10px] text-slate-500">Today</div>
                </div>
            </div>

            <!-- Current Value (big) -->
            <div class="flex items-end justify-between">
                <div>
                    <div class="text-[10px] text-slate-500 uppercase tracking-wide">Current Value</div>
                    <div class="text-2xl font-extrabold text-slate-100 leading-tight mt-0.5">${fmtIdx(idx.current_value)}</div>
                </div>
                <!-- Mini arc indicator -->
                <div class="relative w-14 h-14 flex items-center justify-center" title="${downPct.toFixed(2)}% from ATH">
                    <svg class="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
                        <circle cx="28" cy="28" r="22" fill="none" stroke="#1e293b" stroke-width="5"/>
                        <circle cx="28" cy="28" r="22" fill="none" stroke="${arcColor}" stroke-width="5"
                            stroke-dasharray="${(arcPct / 100) * 138.2} 138.2"
                            stroke-linecap="round"/>
                    </svg>
                    <div class="absolute text-[9px] font-bold" style="color:${arcColor}">${downPct.toFixed(1)}%</div>
                </div>
            </div>

            <!-- Divider -->
            <div class="border-t border-slate-800/70"></div>

            <!-- ATH row -->
            <div class="grid grid-cols-2 gap-2 text-xs">
                <div class="bg-slate-900/50 rounded-xl p-2.5">
                    <div class="text-slate-500 text-[10px] uppercase tracking-wide">All-Time High</div>
                    <div class="font-bold text-slate-200 mt-0.5">${fmtIdx(idx.ath_value)}</div>
                    <div class="text-[10px] text-slate-600 font-mono mt-0.5">${idx.ath_date || "—"}</div>
                </div>
                <div class="bg-slate-900/50 rounded-xl p-2.5">
                    <div class="text-slate-500 text-[10px] uppercase tracking-wide">Down from ATH</div>
                    <div class="mt-0.5">
                        <span class="${dipBadge} text-xs px-2 py-0.5 rounded-full font-bold">-${downPct.toFixed(2)}%</span>
                    </div>
                    <div class="text-[10px] text-slate-600 mt-1">${idx.color_status === "Green" ? "Near ATH ✓" : "Dip from ATH ↓"}</div>
                </div>
            </div>

            <!-- 52-week range bar -->
            <div>
                <div class="flex justify-between text-[10px] text-slate-500 mb-1">
                    <span>52W Low: ${fmtIdx(idx.low_52w)}</span>
                    <span>52W High: ${fmtIdx(idx.high_52w)}</span>
                </div>
                <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all" style="background:${arcColor};width:${
                        idx.high_52w > idx.low_52w
                            ? Math.min(100, ((idx.current_value - idx.low_52w) / (idx.high_52w - idx.low_52w)) * 100).toFixed(1)
                            : 50
                    }%"></div>
                </div>
            </div>
        ` : `
            <div class="flex flex-col items-center justify-center gap-3 py-5 text-center">
                <div class="text-[10px] font-bold uppercase tracking-widest ${cls.text}">${idx.label}</div>
                <div class="text-sm font-bold text-slate-300 leading-tight">${idx.display_name}</div>
                <div class="flex flex-col items-center gap-2 mt-1">
                    <div class="text-rose-400 text-[11px]">⚠ ${idx.error || "Data unavailable"}</div>
                    <button
                        data-index-key="${idx.key}"
                        onclick="retryIndexCard('${idx.key}', this)"
                        class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 rounded-lg text-[10px] font-bold transition-all">
                        <span class="retry-icon">🔄</span> Retry
                    </button>
                </div>
            </div>
        `;

        grid.appendChild(card);
    });
}

function renderIndexTable(data) {
    const tbody = document.getElementById("indices-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    data.forEach(idx => {
        const cls = _indexColorClasses(idx);
        const isOk = idx.status === "ok";
        const todayPct = parseFloat(idx.today_change_pct || 0);
        const todayColor = todayPct >= 0 ? "text-emerald-400" : "text-rose-400";
        const todaySign = todayPct >= 0 ? "▲" : "▼";
        const downPct = parseFloat(idx.down_from_ath_pct || 0);
        let dipBadge = "badge-green";
        if (idx.color_status === "Yellow") dipBadge = "badge-yellow";
        if (idx.color_status === "Red")    dipBadge = "badge-red";

        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-800/70 hover:bg-slate-800/30 transition-colors";

        if (!isOk) {
            tr.setAttribute("data-index-key", idx.key);
            tr.innerHTML = `
                <td colspan="8" class="px-4 py-3">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="${cls.text} font-semibold text-xs">${idx.display_name}</span>
                        <span class="text-rose-400 text-[11px]">⚠ ${idx.error}</span>
                        <button
                            data-index-key="${idx.key}"
                            onclick="retryIndexCard('${idx.key}', this)"
                            class="flex items-center gap-1 px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 rounded text-[10px] font-bold transition-all">
                            <span class="retry-icon">🔄</span> Retry
                        </button>
                    </div>
                </td>`;
        } else {
            tr.innerHTML = `
                <td class="px-4 py-3">
                    <div class="font-semibold text-slate-200 text-xs">${idx.display_name}</div>
                    <div class="text-[10px] ${cls.text} font-bold">${idx.label}</div>
                </td>
                <td class="px-4 py-3 font-bold text-slate-100 text-xs whitespace-nowrap">${fmtIdx(idx.current_value)}</td>
                <td class="px-4 py-3 whitespace-nowrap">
                    <span class="${todayColor} text-xs font-semibold">${todaySign} ${Math.abs(todayPct).toFixed(2)}%</span>
                </td>
                <td class="px-4 py-3 text-slate-300 text-xs whitespace-nowrap font-semibold">${fmtIdx(idx.ath_value)}</td>
                <td class="px-4 py-3 text-slate-500 text-[11px] font-mono whitespace-nowrap">${idx.ath_date || "—"}</td>
                <td class="px-4 py-3 whitespace-nowrap">
                    <span class="${dipBadge} text-xs px-2.5 py-1 rounded-full font-bold">-${downPct.toFixed(2)}%</span>
                </td>
                <td class="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">${fmtIdx(idx.high_52w)}</td>
                <td class="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">${fmtIdx(idx.low_52w)}</td>
            `;
        }
        tbody.appendChild(tr);
    });
}

// ─── Retry a single failed index card ────────────────────
async function retryIndexCard(indexKey, btnEl) {
    const retryIcon = btnEl.querySelector(".retry-icon");
    if (retryIcon) retryIcon.textContent = "⏳";
    btnEl.disabled = true;

    try {
        const res = await fetch("/api/v1/indices");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const found = data.find(d => d.key === indexKey);
        if (!found) throw new Error("Index not found in response");

        if (found.status !== "ok") {
            throw new Error(found.error || "Still unavailable");
        }

        // Re-render just this card in the grid
        const grid = document.getElementById("indices-grid");
        if (grid) {
            // Find the card with the retry button and replace it
            const oldCard = btnEl.closest(".index-card");
            if (oldCard) {
                // Rebuild full grid (simplest + correct approach)
                renderIndexCards(data);
                renderIndexTable(data);
                return;
            }
        }
        // Fallback: full reload
        renderIndexCards(data);
        renderIndexTable(data);
    } catch (err) {
        if (retryIcon) retryIcon.textContent = "🔄";
        btnEl.disabled = false;
        btnEl.title = `Error: ${err.message}`;
    }
}

// ─── 4. Alerts Tab ────────────────────────────────────────
async function loadAlerts() {
    const container = document.getElementById("alerts-container");
    if (!container) return;
    container.innerHTML = `<div class="text-center text-slate-500 text-xs py-10 animate-pulse">Loading alerts...</div>`;

    try {
        const res = await fetch("/api/v1/alerts");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const alerts = await res.json();
        renderAlerts(alerts);
    } catch (e) {
        container.innerHTML = `<div class="text-center text-rose-400 text-xs py-10">⚠ ${e.message}</div>`;
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById("alerts-container");
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <div class="glass-card rounded-2xl p-10 text-center space-y-3">
                <div class="text-3xl">🔔</div>
                <div class="text-slate-400 text-sm font-semibold">No alerts configured yet</div>
                <div class="text-slate-500 text-xs">Create an alert above to get notified when an asset falls from its peak</div>
            </div>`;
        return;
    }

    container.innerHTML = "";
    alerts.forEach(alert => {
        const card = document.createElement("div");
        card.className = "alert-card glass-card rounded-2xl p-4 flex items-center justify-between gap-3";
        card.setAttribute("id", `alert-${alert.id}`);

        const isActive = alert.is_active;
        const isTriggered = !!alert.last_triggered_at;

        let statusDot = isTriggered
            ? '<span class="w-2 h-2 rounded-full bg-rose-400 inline-block animate-pulse"></span>'
            : isActive
            ? '<span class="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>'
            : '<span class="w-2 h-2 rounded-full bg-slate-600 inline-block"></span>';

        let statusLabel = isTriggered ? "Triggered 🔴" : isActive ? "Active" : "Paused";
        let statusColor = isTriggered ? "text-rose-400" : isActive ? "text-emerald-400" : "text-slate-500";

        const dropLabel = `${alert.drop_percentage}% Drop`;
        const typeLabel = alert.target_type === "PEAK_NAV_DROP" ? "Peak NAV" : "ATH";
        const assetBadge = alert.asset_type === "MUTUAL_FUND"
            ? '<span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded font-bold">MF</span>'
            : '<span class="bg-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded font-bold">ETF</span>';

        card.innerHTML = `
            <div class="flex items-center gap-3 flex-1 min-w-0">
                ${statusDot}
                <div class="min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                        <div class="font-semibold text-slate-200 text-xs truncate">${alert.asset_name || alert.symbol_or_code}</div>
                        ${assetBadge}
                    </div>
                    <div class="text-[10px] text-slate-500 font-mono">${alert.symbol_or_code}</div>
                    <div class="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2 flex-wrap">
                        <span class="badge-yellow text-[10px] px-1.5 py-0.5 rounded font-bold">-${dropLabel} from ${typeLabel}</span>
                        <span class="${statusColor} font-semibold">${statusLabel}</span>
                        ${alert.last_triggered_at ? `<span class="text-slate-600 font-mono text-[10px]">last triggered: ${new Date(alert.last_triggered_at).toLocaleDateString('en-IN')}</span>` : ""}
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
                <!-- Toggle -->
                <button onclick="toggleAlert(${alert.id})"
                    class="px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all ${isActive ? 'border-slate-700 text-slate-400 hover:border-amber-500/50 hover:text-amber-400' : 'border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10'}"
                    title="${isActive ? 'Pause alert' : 'Activate alert'}">
                    ${isActive ? "⏸ Pause" : "▶ Activate"}
                </button>
                <!-- Delete -->
                <button onclick="deleteAlert(${alert.id})"
                    class="px-3 py-1.5 rounded-lg text-[10px] font-bold border border-slate-700 text-slate-500 hover:border-rose-500/40 hover:text-rose-400 transition-all"
                    title="Delete alert">
                    🗑
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

async function toggleAlert(alertId) {
    try {
        const res = await fetch(`/api/v1/alerts/${alertId}/toggle`, { method: "PUT" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadAlerts();
    } catch (e) {
        console.error("Toggle error:", e);
    }
}

async function deleteAlert(alertId) {
    try {
        const res = await fetch(`/api/v1/alerts/${alertId}`, { method: "DELETE" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        // Animate removal
        const card = document.getElementById(`alert-${alertId}`);
        if (card) {
            card.style.transition = "opacity 0.3s, transform 0.3s";
            card.style.opacity = "0";
            card.style.transform = "translateX(20px)";
            setTimeout(() => loadAlerts(), 350);
        } else {
            await loadAlerts();
        }
    } catch (e) {
        console.error("Delete error:", e);
    }
}

async function createAlert() {
    const symbolEl = document.getElementById("alert-symbol");
    const typeEl = document.getElementById("alert-type");
    const statusEl = document.getElementById("alert-create-status");

    const symbol = symbolEl?.value.trim();
    const selectedOption = typeEl?.value || "PRICE_DROP_15";

    if (!symbol) {
        if (statusEl) { statusEl.textContent = "⚠ Please enter a fund symbol or code."; statusEl.className = "text-xs mt-2 text-rose-400"; statusEl.classList.remove("hidden"); }
        return;
    }

    // Parse drop pct from option value: "PRICE_DROP_15" → 15
    const dropPct = parseFloat(selectedOption.replace("PRICE_DROP_", "")) || 15;
    // Determine target type: ETF uses ATH_DROP, MF uses PEAK_NAV_DROP
    // We detect by checking if symbol is numeric (MF code) or alphanumeric (ETF)
    const isNumeric = /^\d+$/.test(symbol);
    const targetType = isNumeric ? "PEAK_NAV_DROP" : "ATH_DROP";
    const assetType = isNumeric ? "MUTUAL_FUND" : "ETF";

    if (statusEl) { statusEl.textContent = "Creating alert..."; statusEl.className = "text-xs mt-2 text-slate-400 animate-pulse"; statusEl.classList.remove("hidden"); }

    try {
        const res = await fetch("/api/v1/alerts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symbol_or_code: symbol,
                asset_name: symbol,
                asset_type: assetType,
                target_type: targetType,
                drop_percentage: dropPct
            })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        if (statusEl) { statusEl.textContent = `✓ Alert created for ${symbol} — ${dropPct}% drop threshold`; statusEl.className = "text-xs mt-2 text-emerald-400"; }
        if (symbolEl) symbolEl.value = "";
        setTimeout(() => {
            if (statusEl) statusEl.classList.add("hidden");
            loadAlerts();
        }, 1500);
    } catch (e) {
        if (statusEl) { statusEl.textContent = `⚠ ${e.message}`; statusEl.className = "text-xs mt-2 text-rose-400"; }
    }
}

// ─── 5. SIP Calculator ────────────────────────────────────
async function runSipCalculator() {
    const inv = parseFloat(document.getElementById("calc-monthly-inv")?.value) || 10000;
    const rate = parseFloat(document.getElementById("calc-rate")?.value) || 12.0;
    const years = parseInt(document.getElementById("calc-years")?.value) || 10;
    try {
        const res = await fetch("/api/v1/calculators/sip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ monthly_investment: inv, expected_return_rate: rate, time_period_years: years })
        });
        const data = await res.json();
        document.getElementById("calc-result-inv").innerText = `₹${data.total_invested.toLocaleString("en-IN")}`;
        document.getElementById("calc-result-returns").innerText = `₹${data.estimated_returns.toLocaleString("en-IN")}`;
        document.getElementById("calc-result-total").innerText = `₹${data.total_value.toLocaleString("en-IN")}`;
    } catch (err) { console.error("Calc error:", err); }
}

// ─── Add Modal ────────────────────────────────────────────
function openAddModal() {
    selectedModalSymbol = null; selectedModalName = null; selectedModalType = null;
    document.getElementById("modal-search-input").value = "";
    document.getElementById("modal-search-dropdown").classList.add("hidden");
    document.getElementById("modal-selected-info").classList.add("hidden");
    document.getElementById("modal-add-btn").disabled = true;
    document.getElementById("modal-status").classList.add("hidden");
    document.getElementById("modal-add-holding").classList.remove("hidden");
}
function closeAddModal() {
    document.getElementById("modal-add-holding").classList.add("hidden");
}

async function addHoldingFromModal() {
    if (!selectedModalSymbol) return;
    const btn = document.getElementById("modal-add-btn");
    const statusEl = document.getElementById("modal-status");
    btn.disabled = true; btn.innerText = "Adding...";
    try {
        const formData = new FormData();
        formData.append("symbol_or_code", selectedModalSymbol);
        formData.append("name", selectedModalName || selectedModalSymbol);
        formData.append("asset_type", selectedModalType || "MUTUAL_FUND");
        formData.append("quantity", "100");
        formData.append("buy_price", "50");

        const res = await fetch("/api/v1/holdings", { method: "POST", body: formData });
        const data = await res.json();

        statusEl.innerText = data.message === "Already tracked" ? "Already in your table!" : `✓ Added: ${data.name}`;
        statusEl.classList.remove("hidden");

        setTimeout(() => {
            closeAddModal();
            loadPeakAnalysis();
        }, 1200);
    } catch (e) {
        statusEl.innerText = `Error: ${e.message}`;
        statusEl.classList.remove("hidden");
        btn.disabled = false; btn.innerText = "Add to Table";
    }
}

// ─── Dropdown builder ─────────────────────────────────────
function buildDropdown(container, results, onSelect) {
    container.innerHTML = "";

    if (!results || !results.length) {
        const empty = document.createElement("div");
        empty.className = "p-3 text-xs text-slate-400";
        empty.innerText = "No schemes found";
        container.appendChild(empty);
        container.classList.remove("hidden");
        return;
    }

    results.forEach(item => {
        const row = document.createElement("div");
        row.style.cssText = "padding:10px 12px;cursor:pointer;border-bottom:1px solid #1e293b;transition:background 0.15s;";
        row.innerHTML = `
            <div style="font-weight:600;color:#e2e8f0;font-size:12px;line-height:1.4;">${item.name}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:3px;">
                <span style="font-family:monospace;font-size:11px;color:#64748b;">${item.symbol_or_code}</span>
                <span style="font-size:10px;background:#1e3a5f;color:#60a5fa;padding:1px 6px;border-radius:4px;font-weight:600;">${item.asset_type}</span>
            </div>`;

        row.addEventListener("mouseenter", () => row.style.background = "#1e293b");
        row.addEventListener("mouseleave", () => row.style.background = "");
        row.addEventListener("mousedown", e => {
            e.preventDefault();
            onSelect(item.symbol_or_code, item.name, item.asset_type);
        });

        container.appendChild(row);
    });

    container.classList.remove("hidden");
}

function setupDirectSearchAutocomplete() {
    const input = document.getElementById("direct-api-input");
    const container = document.getElementById("direct-search-dropdown");
    if (!input || !container) return;

    let timer;
    input.addEventListener("input", e => {
        clearTimeout(timer);
        const q = e.target.value.trim();
        if (q.length < 2) { container.classList.add("hidden"); return; }
        timer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/v1/search?q=${encodeURIComponent(q)}`);
                const results = await res.json();
                buildDropdown(container, results, (sym, name, type) => {
                    input.value = name;
                    container.classList.add("hidden");
                    fetchAndAnalyzeDirectly(sym);
                });
            } catch (err) { console.error(err); }
        }, 300);
    });

    input.addEventListener("blur", () => setTimeout(() => container.classList.add("hidden"), 150));
    input.addEventListener("focus", e => {
        if (e.target.value.trim().length >= 2) container.classList.remove("hidden");
    });
}

function setupModalSearchAutocomplete() {
    const input = document.getElementById("modal-search-input");
    const container = document.getElementById("modal-search-dropdown");
    if (!input || !container) return;

    let timer;
    input.addEventListener("input", e => {
        clearTimeout(timer);
        const q = e.target.value.trim();
        if (q.length < 2) { container.classList.add("hidden"); return; }
        timer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/v1/search?q=${encodeURIComponent(q)}`);
                const results = await res.json();
                buildDropdown(container, results, (sym, name, type) => {
                    selectedModalSymbol = sym;
                    selectedModalName = name;
                    selectedModalType = type;
                    input.value = name;
                    container.classList.add("hidden");
                    document.getElementById("modal-selected-name").innerText = name;
                    document.getElementById("modal-selected-code").innerText = `Code: ${sym} · ${type}`;
                    document.getElementById("modal-selected-info").classList.remove("hidden");
                    document.getElementById("modal-add-btn").disabled = false;
                });
            } catch (err) { console.error(err); }
        }, 300);
    });

    input.addEventListener("blur", () => setTimeout(() => container.classList.add("hidden"), 150));
}
