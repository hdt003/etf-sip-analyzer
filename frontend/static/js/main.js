// Buy the Dip Analyzer — Main JS (NaN-safe, real data only)
let selectedModalSymbol = null;
let selectedModalName = null;
let selectedModalType = null;

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

// ─── Tab Switching (2 tabs only) ──────────────────────────
function switchTab(tabId) {
    ["tab-peak", "tab-sip"].forEach(t => {
        document.getElementById(t)?.classList.add("hidden");
        const btn = document.getElementById(`btn-${t}`);
        if (btn) { btn.classList.remove("bg-blue-600", "text-white"); btn.classList.add("text-slate-400", "hover:bg-slate-800"); }
    });
    document.getElementById(tabId)?.classList.remove("hidden");
    const activeBtn = document.getElementById(`btn-${tabId}`);
    if (activeBtn) { activeBtn.classList.remove("text-slate-400", "hover:bg-slate-800"); activeBtn.classList.add("bg-blue-600", "text-white"); }
}

// ─── Helper: safe number formatting ───────────────────────
function fmtNav(val) {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "—";
    return `₹${parseFloat(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
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
    if (item.buy_score >= 80) scoreBadge = "badge-green";
    else if (item.buy_score <= 40) scoreBadge = "badge-red";

    const todayPct = parseFloat(item.today_change_pct || 0);
    const todayColor = todayPct >= 0 ? "text-emerald-400" : "text-rose-400";
    const todaySign = todayPct >= 0 ? "▲" : "▼";

    // Escape symbol safely for use in onclick attributes
    const symEsc = item.symbol_or_code.replace(/'/g, "\\'");

    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-800/70 hover:bg-slate-800/30 transition-colors";
    tr.setAttribute("data-symbol", item.symbol_or_code);
    tr.setAttribute("data-type", item.asset_type);

    if (isError) {
        // Compact error row with inline retry button
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
    // Find the row element
    const tr = btnEl.closest("tr");
    if (!tr) return;

    // Show inline spinner on the button
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

        // Build fresh row and replace the old error row
        const newRow = createRowHTML(data);
        tr.replaceWith(newRow);
    } catch (err) {
        // Restore retry button with error hint
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

    // Close dropdown before showing loader
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
                <span class="badge-blue" style="font-size:11px;padding:2px 7px;border-radius:4px;font-weight:700;">${data.buy_score}/100</span>
            </div>
            <div style="font-size:10px;color:#64748b;margin-top:3px;">${data.buy_recommendation}</div>
        </div>
    `;
    // Show using inline style (the div uses display:grid via inline style)
    container.style.display = "grid";
    // On desktop expand to 5 columns
    if (window.innerWidth >= 640) {
        container.style.gridTemplateColumns = "2fr 1fr 1fr 1fr";
    } else {
        container.style.gridTemplateColumns = "repeat(2,1fr)";
    }
}

// ─── 3. SIP Calculator ────────────────────────────────────
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

// ─── Dropdown builder — uses addEventListener (NOT inline onclick) ───
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

        // Use mousedown (fires before blur which hides dropdown)
        row.addEventListener("mousedown", e => {
            e.preventDefault();   // prevent input losing focus before click fires
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
