const STORAGE_KEYS = {
  watchlist: "tdSequential.watchlist",
  csv: "tdSequential.csv",
  alerts: "tdSequential.alerts",
};

const DEFAULT_WATCHLIST = ["AAPL", "MSFT", "NVDA", "TSLA"];
const DEFAULT_EMPTY_COPY = "Charge un CSV ou colle des données pour afficher les signaux TD Sequential.";
const INDEX_PRESETS = {
  sp500: ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "BRK.B", "LLY", "JPM", "XOM", "V", "UNH", "MA", "COST"],
  nasdaq100: ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "COST", "NFLX", "AMD", "ADBE", "QCOM", "INTC", "CSCO", "INTU"],
  tsx60: ["RY.TO", "TD.TO", "SHOP.TO", "CNR.TO", "CP.TO", "ENB.TO", "BNS.TO", "BMO.TO", "SU.TO", "CNQ.TO", "BCE.TO", "TRP.TO", "ATD.TO", "MFC.TO", "WCN.TO"],
  commodities: ["GC=F", "SI=F", "PL=F", "HG=F", "CL=F", "BZ=F", "NG=F", "RB=F", "HO=F", "ZC=F", "ZS=F", "ZW=F", "KC=F", "SB=F", "CC=F", "CT=F", "LE=F", "HE=F"],
  fx: ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCAD=X", "AUDUSD=X", "USDCHF=X", "NZDUSD=X", "USDMXN=X", "EURCAD=X", "EURGBP=X", "EURAUD=X", "CADJPY=X"],
  rates: ["^IRX", "^FVX", "^TNX", "^TYX", "ZQ=F", "ZT=F", "ZF=F", "ZN=F", "ZB=F", "SR3=F"],
  custom: [],
};
const INDEX_REMOTE_SOURCES = {
  sp500: "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
  nasdaq100: "https://thaywebsearch.github.io/nasdaq100-list/nasdaq100-table.csv",
  tsx60: "https://en.wikipedia.org/w/api.php?action=parse&page=S%26P%2FTSX_60&prop=text&format=json&origin=*",
};
let lastResults = new Map();
let alertPermission = localStorage.getItem(STORAGE_KEYS.alerts) === "granted";
let monitorTimer = null;
let summaryFilter = "all";
let currentWatchlist = [];

const sampleSeries = {
  AAPL: [
    { date: "2026-08-18", open: 220.5, high: 223.1, low: 219.4, close: 221.8, volume: 61230000 },
    { date: "2026-08-19", open: 221.9, high: 224.0, low: 221.1, close: 223.2, volume: 58812000 },
    { date: "2026-08-20", open: 223.0, high: 224.8, low: 222.4, close: 224.1, volume: 57533000 },
    { date: "2026-08-21", open: 224.1, high: 225.6, low: 223.3, close: 224.9, volume: 56077000 },
    { date: "2026-08-22", open: 225.1, high: 226.2, low: 224.2, close: 225.7, volume: 54122000 },
    { date: "2026-08-25", open: 225.8, high: 227.3, low: 225.0, close: 226.6, volume: 52711000 },
    { date: "2026-08-26", open: 226.6, high: 228.1, low: 225.8, close: 227.4, volume: 51945000 },
    { date: "2026-08-27", open: 227.2, high: 228.7, low: 226.4, close: 228.2, volume: 50766000 },
    { date: "2026-08-28", open: 228.4, high: 229.4, low: 227.4, close: 228.7, volume: 50022000 },
    { date: "2026-08-29", open: 228.6, high: 229.8, low: 227.8, close: 229.1, volume: 49377000 },
    { date: "2026-09-01", open: 229.1, high: 230.2, low: 228.2, close: 229.7, volume: 48522000 },
    { date: "2026-09-02", open: 229.7, high: 230.8, low: 228.9, close: 230.3, volume: 47388000 },
    { date: "2026-09-03", open: 230.2, high: 231.4, low: 229.4, close: 230.9, volume: 46123000 },
    { date: "2026-09-04", open: 230.8, high: 232.0, low: 230.0, close: 231.5, volume: 45261000 },
    { date: "2026-09-05", open: 231.5, high: 232.7, low: 230.7, close: 232.1, volume: 44732000 },
  ],
  MSFT: [
    { date: "2026-08-18", open: 415.6, high: 417.8, low: 414.0, close: 416.9, volume: 21234000 },
    { date: "2026-08-19", open: 416.8, high: 418.5, low: 415.4, close: 417.3, volume: 20678000 },
    { date: "2026-08-20", open: 417.2, high: 419.0, low: 416.0, close: 418.2, volume: 20411000 },
    { date: "2026-08-21", open: 418.4, high: 420.4, low: 417.4, close: 419.6, volume: 20244000 },
    { date: "2026-08-22", open: 419.8, high: 421.6, low: 418.8, close: 420.8, volume: 19855000 },
    { date: "2026-08-25", open: 420.9, high: 422.1, low: 419.7, close: 421.5, volume: 19561000 },
    { date: "2026-08-26", open: 421.4, high: 423.0, low: 420.5, close: 422.7, volume: 19322000 },
    { date: "2026-08-27", open: 422.8, high: 424.1, low: 421.9, close: 423.4, volume: 19187000 },
    { date: "2026-08-28", open: 423.6, high: 424.8, low: 422.7, close: 424.2, volume: 19033000 },
    { date: "2026-08-29", open: 424.0, high: 425.2, low: 423.0, close: 424.8, volume: 18894000 },
    { date: "2026-09-01", open: 424.9, high: 425.8, low: 423.7, close: 425.1, volume: 18766000 },
    { date: "2026-09-02", open: 425.3, high: 426.4, low: 424.0, close: 424.4, volume: 18644000 },
    { date: "2026-09-03", open: 424.6, high: 425.4, low: 423.1, close: 423.5, volume: 18488000 },
    { date: "2026-09-04", open: 423.7, high: 424.2, low: 421.9, close: 422.0, volume: 18230000 },
    { date: "2026-09-05", open: 422.1, high: 422.9, low: 420.4, close: 421.2, volume: 17976000 },
  ],
  NVDA: [
    { date: "2026-08-18", open: 141.2, high: 144.0, low: 140.7, close: 143.2, volume: 74210000 },
    { date: "2026-08-19", open: 143.1, high: 145.4, low: 142.2, close: 144.5, volume: 73350000 },
    { date: "2026-08-20", open: 144.7, high: 146.1, low: 143.8, close: 145.3, volume: 72124000 },
    { date: "2026-08-21", open: 145.4, high: 147.2, low: 144.5, close: 146.8, volume: 71866000 },
    { date: "2026-08-22", open: 146.7, high: 148.0, low: 145.5, close: 147.4, volume: 70633000 },
    { date: "2026-08-25", open: 147.5, high: 149.2, low: 146.4, close: 148.9, volume: 69822000 },
    { date: "2026-08-26", open: 149.0, high: 150.5, low: 148.1, close: 149.8, volume: 69043000 },
    { date: "2026-08-27", open: 149.7, high: 151.0, low: 148.8, close: 150.6, volume: 68811000 },
    { date: "2026-08-28", open: 150.7, high: 151.8, low: 149.9, close: 151.1, volume: 67644000 },
    { date: "2026-08-29", open: 151.0, high: 152.5, low: 150.4, close: 152.0, volume: 66912000 },
    { date: "2026-09-01", open: 152.1, high: 153.0, low: 151.3, close: 152.4, volume: 66087000 },
    { date: "2026-09-02", open: 152.4, high: 153.8, low: 151.8, close: 153.1, volume: 65322000 },
    { date: "2026-09-03", open: 153.2, high: 154.1, low: 152.2, close: 152.7, volume: 64911000 },
    { date: "2026-09-04", open: 152.8, high: 153.5, low: 151.0, close: 151.6, volume: 64533000 },
    { date: "2026-09-05", open: 151.7, high: 152.1, low: 149.8, close: 150.2, volume: 64122000 },
  ],
  TSLA: [
    { date: "2026-08-18", open: 223.4, high: 226.0, low: 221.7, close: 224.8, volume: 98012000 },
    { date: "2026-08-19", open: 224.9, high: 227.1, low: 223.2, close: 225.7, volume: 96234000 },
    { date: "2026-08-20", open: 225.8, high: 228.0, low: 224.1, close: 227.3, volume: 95511000 },
    { date: "2026-08-21", open: 227.2, high: 229.4, low: 226.0, close: 228.2, volume: 94223000 },
    { date: "2026-08-22", open: 228.3, high: 230.0, low: 227.0, close: 229.1, volume: 93766000 },
    { date: "2026-08-25", open: 229.2, high: 231.3, low: 228.2, close: 230.4, volume: 93088000 },
    { date: "2026-08-26", open: 230.5, high: 232.1, low: 229.1, close: 231.2, volume: 91843000 },
    { date: "2026-08-27", open: 231.3, high: 233.1, low: 230.0, close: 232.4, volume: 90566000 },
    { date: "2026-08-28", open: 232.5, high: 233.8, low: 231.2, close: 232.0, volume: 89777000 },
    { date: "2026-08-29", open: 232.1, high: 233.0, low: 229.9, close: 230.8, volume: 88944000 },
    { date: "2026-09-01", open: 230.7, high: 231.4, low: 228.7, close: 229.6, volume: 88122000 },
    { date: "2026-09-02", open: 229.5, high: 230.0, low: 227.5, close: 228.2, volume: 87654000 },
    { date: "2026-09-03", open: 228.1, high: 229.0, low: 226.2, close: 227.0, volume: 86999000 },
    { date: "2026-09-04", open: 227.1, high: 227.8, low: 224.9, close: 225.3, volume: 86543000 },
    { date: "2026-09-05", open: 225.2, high: 226.1, low: 223.0, close: 223.8, volume: 86111000 },
  ],
};

const els = {
  watchlistInput: document.getElementById("watchlistInput"),
  csvInput: document.getElementById("csvInput"),
  csvFile: document.getElementById("csvFile"),
  saveWatchlist: document.getElementById("saveWatchlist"),
  addExample: document.getElementById("addExample"),
  scanNow: document.getElementById("scanNow"),
  loadSample: document.getElementById("loadSample"),
  fetchMarket: document.getElementById("fetchMarket"),
  marketInterval: document.getElementById("marketInterval"),
  marketRange: document.getElementById("marketRange"),
  marketStatus: document.getElementById("marketStatus"),
  enableAlerts: document.getElementById("enableAlerts"),
  alertStatus: document.getElementById("alertStatus"),
  exportResults: document.getElementById("exportResults"),
  insightBar: document.getElementById("insightBar"),
  insightText: document.getElementById("insightText"),
  indexUniverse: document.getElementById("indexUniverse"),
  indexInput: document.getElementById("indexInput"),
  indexFile: document.getElementById("indexFile"),
  addIndexSymbols: document.getElementById("addIndexSymbols"),
  replaceWithIndex: document.getElementById("replaceWithIndex"),
  indexStatus: document.getElementById("indexStatus"),
  fetchIndexComposition: document.getElementById("fetchIndexComposition"),
  clearResults: document.getElementById("clearResults"),
  resetWatchlist: document.getElementById("resetWatchlist"),
  resultsGrid: document.getElementById("resultsGrid"),
  resultsEmpty: document.getElementById("resultsEmpty"),
  resultCardTemplate: document.getElementById("resultCardTemplate"),
  globalSignal: document.getElementById("globalSignal"),
  globalSignalMeta: document.getElementById("globalSignalMeta"),
  watchlistCount: document.getElementById("watchlistCount"),
  seriesCount: document.getElementById("seriesCount"),
  latestDate: document.getElementById("latestDate"),
  summarySection: document.getElementById("summarySection"),
  summaryTableBody: document.getElementById("summaryTableBody"),
  summaryEmpty: document.getElementById("summaryEmpty"),
};

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatVolume(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function renderPriceChart(svg, series) {
  const points = series.slice(-42);
  if (!points.length) return;
  const values = points.map((bar) => bar.close);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 520;
  const height = 96;
  const padding = 6;
  const coords = values.map((value, index) => {
    const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  svg.innerHTML = `<line x1="0" y1="95" x2="520" y2="95"></line><polyline points="${coords.join(" ")}"></polyline><circle cx="${coords.at(-1).split(",")[0]}" cy="${coords.at(-1).split(",")[1]}" r="4"></circle>`;
}

function setAlertUi() {
  const supported = "Notification" in window;
  if (!supported) {
    els.alertStatus.textContent = "Non disponible";
    els.enableAlerts.textContent = "Notifications non supportées";
    els.enableAlerts.disabled = true;
    return;
  }
  const active = alertPermission && Notification.permission === "granted";
  els.alertStatus.textContent = active ? "Actives" : "Inactives";
  els.enableAlerts.textContent = active ? "Alertes activées · surveillance active" : "Activer les alertes";
}

function startAlertMonitoring() {
  if (monitorTimer || !alertPermission || !("Notification" in window)) return;
  monitorTimer = window.setInterval(() => {
    if (document.visibilityState === "visible") fetchMarketData({ background: true });
  }, 5 * 60 * 1000);
  els.alertStatus.textContent = "Actives · toutes les 5 min";
}

function notifySignals(results) {
  const fresh = [];
  for (const [symbol, analysis] of results) {
    const before = lastResults.get(symbol)?.summary?.signal;
    const signal = analysis.summary.signal;
    const actionable = /setup 9|countdown 13/.test(signal);
    if (actionable && signal !== before) fresh.push(`${symbol}: ${signal}`);
  }
  if (!fresh.length) return;
  const message = fresh.join(" · ");
  els.insightText.textContent = `Signal détecté: ${message}`;
  els.insightBar.hidden = false;
  if (alertPermission && "Notification" in window && Notification.permission === "granted") {
    new Notification("TD Sequential", { body: message });
  }
}

function toCsv(results) {
  const rows = [["symbol", "date", "close", "setup", "countdown", "signal", "perfection", "volume"]];
  for (const [symbol, analysis] of results) {
    const summary = analysis.summary;
    rows.push([
      symbol,
      analysis.latest.date,
      analysis.latest.close,
      summary.setupCount || "",
      summary.countdownCount || "",
      summary.signal,
      summary.perfection,
      formatVolume(analysis.latest.volume),
    ]);
  }
  return rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
}

function exportResults() {
  if (!lastResults.size) {
    showError("Aucun résultat à exporter. Lance d’abord un scan.");
    return;
  }
  const blob = new Blob([toCsv(lastResults)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `td-sequential-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function parseWatchlist(text) {
  const seen = new Set();
  return text
    .split(/\r?\n/)
    .map((line) => line.trim().toUpperCase())
    .filter(Boolean)
    .filter((symbol) => {
      if (seen.has(symbol)) return false;
      seen.add(symbol);
      return true;
    });
}

function parseIndexSymbols(text) {
  const headers = new Set(["SYMBOL", "TICKER", "TICKER SYMBOL", "CODE", "COMPANY", "NAME"]);
  const seen = new Set();
  const symbols = [];
  for (const rawLine of text.replace(/^\uFEFF/, "").split(/\r?\n/)) {
    const fields = rawLine.split(/[;,\t]/).map((value) => value.replaceAll('"', "").trim());
    const candidates = fields.length > 1 ? fields : rawLine.trim().split(/\s+/);
    const symbol = candidates.find((value) => {
      const normalized = value.toUpperCase();
      return normalized && !headers.has(normalized) && /^[A-Z^][A-Z0-9^=./-]{0,11}$/.test(normalized);
    });
    if (!symbol) continue;
    const normalized = symbol.toUpperCase();
    if (!seen.has(normalized)) {
      seen.add(normalized);
      symbols.push(normalized);
    }
  }
  return symbols;
}

function updateIndexStatus() {
  const count = parseIndexSymbols(els.indexInput.value).length;
  els.indexStatus.textContent = `${count} symbole${count === 1 ? "" : "s"} chargé${count === 1 ? "" : "s"}`;
}

async function fetchIndexComposition() {
  const key = els.indexUniverse.value;
  const source = INDEX_REMOTE_SOURCES[key];
  if (!source) {
    els.indexStatus.textContent = "Choisis un indice action pour actualiser sa composition";
    return;
  }
  els.fetchIndexComposition.disabled = true;
  els.indexStatus.textContent = "Récupération en ligne...";
  try {
    const response = await fetch(source);
    if (!response.ok) throw new Error(`Source indisponible (${response.status})`);
    let text = await response.text();
    if (key === "tsx60") {
      const payload = JSON.parse(text);
      const html = payload.parse?.text?.["*"] || "";
      const documentFragment = new DOMParser().parseFromString(html, "text/html");
      const symbols = [...documentFragment.querySelectorAll("table tr")]
        .map((row) => row.querySelector("td")?.textContent?.trim().replace(/\[.*?\]/g, ""))
        .filter((symbol) => symbol && /^[A-Z][A-Z0-9.-]{0,7}$/.test(symbol))
        .map((symbol) => `${symbol}.TO`);
      text = symbols.join("\n");
    }
    els.indexInput.value = text;
    updateIndexStatus();
    els.indexStatus.textContent += " · source actualisée";
  } catch (error) {
    els.indexStatus.textContent = error instanceof Error ? error.message : "Impossible de charger la composition";
  } finally {
    els.fetchIndexComposition.disabled = false;
  }
}

function loadIndexPreset() {
  const key = els.indexUniverse.value;
  els.indexInput.value = INDEX_PRESETS[key].join("\n");
  updateIndexStatus();
}

function mergeIndexIntoWatchlist(replace = false) {
  const indexSymbols = parseIndexSymbols(els.indexInput.value);
  if (!indexSymbols.length) {
    els.indexStatus.textContent = "Aucun symbole valide";
    return;
  }
  const current = replace ? [] : parseWatchlist(els.watchlistInput.value);
  els.watchlistInput.value = Array.from(new Set([...current, ...indexSymbols])).join("\n");
  els.watchlistCount.textContent = String(parseWatchlist(els.watchlistInput.value).length);
  localStorage.setItem(STORAGE_KEYS.watchlist, els.watchlistInput.value);
  els.indexStatus.textContent = `${indexSymbols.length} symboles ajoutés à la watchlist`;
  scan();
}

function parseCsv(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) return [];

  const header = lines[0].split(",").map((value) => value.trim().toLowerCase());
  const required = ["symbol", "date", "open", "high", "low", "close"];
  const missing = required.filter((key) => !header.includes(key));
  if (missing.length) {
    throw new Error(`CSV invalide. Colonnes manquantes: ${missing.join(", ")}`);
  }

  const indexes = Object.fromEntries(header.map((key, index) => [key, index]));
  const rows = [];

  for (const line of lines.slice(1)) {
    const values = line.split(",").map((value) => value.trim());
    if (values.length < required.length) continue;

    const symbol = (values[indexes.symbol] || "").toUpperCase();
    const date = values[indexes.date];
    const open = Number(values[indexes.open]);
    const high = Number(values[indexes.high]);
    const low = Number(values[indexes.low]);
    const close = Number(values[indexes.close]);
    const volume = indexes.volume === undefined ? null : Number(values[indexes.volume]);

    if (!symbol || !date || [open, high, low, close].some((n) => Number.isNaN(n))) continue;
    rows.push({ symbol, date, open, high, low, close, volume: Number.isNaN(volume) ? null : volume });
  }

  return rows;
}

function groupBySymbol(rows) {
  const map = new Map();
  for (const row of rows) {
    if (!map.has(row.symbol)) map.set(row.symbol, []);
    map.get(row.symbol).push(row);
  }
  for (const series of map.values()) {
    series.sort((a, b) => a.date.localeCompare(b.date));
  }
  return map;
}

function tdLabel(direction) {
  if (direction === "buy") return "Buy";
  if (direction === "sell") return "Sell";
  return "Neutre";
}

function evaluatePerfection(series, direction, setupEndIndex) {
  if (setupEndIndex < 8) return "En attente";

  if (direction === "buy") {
    const low6 = series[setupEndIndex - 3]?.low;
    const low7 = series[setupEndIndex - 2]?.low;
    const low8 = series[setupEndIndex - 1]?.low;
    const low9 = series[setupEndIndex]?.low;
    if ([low6, low7, low8, low9].some((value) => value === undefined)) return "En attente";
    return low8 <= Math.min(low6, low7) || low9 <= Math.min(low6, low7) ? "Oui" : "Non";
  }

  const high6 = series[setupEndIndex - 3]?.high;
  const high7 = series[setupEndIndex - 2]?.high;
  const high8 = series[setupEndIndex - 1]?.high;
  const high9 = series[setupEndIndex]?.high;
  if ([high6, high7, high8, high9].some((value) => value === undefined)) return "En attente";
  return high8 >= Math.max(high6, high7) || high9 >= Math.max(high6, high7) ? "Oui" : "Non";
}

function analyzeSeries(series) {
  const bars = series.map((bar) => ({
    ...bar,
    setup: null,
    countdown: null,
    stage: "neutral",
  }));

  let buySetup = 0;
  let sellSetup = 0;
  let activeDirection = null;
  let activeSetupEnd = null;
  let buyCountdown = 0;
  let sellCountdown = 0;
  let lastValidation = "—";

  for (let i = 0; i < bars.length; i += 1) {
    const current = bars[i];
    const buyCondition = i >= 4 && current.close < bars[i - 4].close;
    const sellCondition = i >= 4 && current.close > bars[i - 4].close;

    if (buyCondition) {
      buySetup += 1;
      sellSetup = 0;
    } else if (sellCondition) {
      sellSetup += 1;
      buySetup = 0;
    } else {
      buySetup = 0;
      sellSetup = 0;
    }

    if (buySetup > 0) {
      current.setup = { direction: "buy", count: buySetup };
      current.stage = "buy";
      if (buySetup === 9) {
        activeDirection = "buy";
        activeSetupEnd = i;
        buyCountdown = 0;
        lastValidation = current.date;
      }
    }

    if (sellSetup > 0) {
      current.setup = { direction: "sell", count: sellSetup };
      current.stage = "sell";
      if (sellSetup === 9) {
        activeDirection = "sell";
        activeSetupEnd = i;
        sellCountdown = 0;
        lastValidation = current.date;
      }
    }

    if (activeDirection === "buy" && i > activeSetupEnd && i >= 2 && current.close <= bars[i - 2].low) {
      buyCountdown = Math.min(13, buyCountdown + 1);
      current.countdown = { direction: "buy", count: buyCountdown };
      current.stage = "buy";
      if (buyCountdown === 13) {
        lastValidation = current.date;
      }
    }

    if (activeDirection === "sell" && i > activeSetupEnd && i >= 2 && current.close >= bars[i - 2].high) {
      sellCountdown = Math.min(13, sellCountdown + 1);
      current.countdown = { direction: "sell", count: sellCountdown };
      current.stage = "sell";
      if (sellCountdown === 13) {
        lastValidation = current.date;
      }
    }
  }

  const latest = bars[bars.length - 1];
  const setupCount = latest.setup?.count ?? (activeDirection === "buy" ? buySetup : activeDirection === "sell" ? sellSetup : 0);
  const countdownCount =
    latest.countdown?.count ?? (activeDirection === "buy" ? buyCountdown : activeDirection === "sell" ? sellCountdown : 0);
  const setupDirection = latest.setup?.direction ?? activeDirection;
  const countdownDirection = latest.countdown?.direction ?? (buyCountdown > 0 ? "buy" : sellCountdown > 0 ? "sell" : null);
  const setupEndIndex = activeSetupEnd ?? bars.length - 1;

  let signal = "Aucun setup confirmé";
  let signalTone = "wait";
  if (countdownCount === 13 && countdownDirection) {
    signal = `${tdLabel(countdownDirection)} countdown 13`;
    signalTone = countdownDirection;
  } else if (setupCount === 9 && setupDirection) {
    signal = `${tdLabel(setupDirection)} setup 9`;
    signalTone = setupDirection;
  } else if (setupCount > 0 && setupDirection) {
    signal = `${tdLabel(setupDirection)} setup ${setupCount}`;
    signalTone = setupDirection;
  }

  return {
    bars,
    latest,
    summary: {
      signal,
      signalTone,
      setupCount,
      countdownCount,
      setupDirection,
      countdownDirection,
      perfection: activeDirection ? evaluatePerfection(bars, activeDirection, setupEndIndex) : "En attente",
      lastValidation,
    },
  };
}

function renderBarChip(bar) {
  const chip = document.createElement("div");
  chip.className = `bar-chip is-${bar.stage}`;

  const strong = document.createElement("strong");
  strong.textContent = bar.setup?.count
    ? `${bar.setup.direction === "buy" ? "B" : "S"}${bar.setup.count}`
    : bar.countdown?.count
      ? `${bar.countdown.direction === "buy" ? "b" : "s"}${bar.countdown.count}`
      : "·";

  const label = document.createElement("span");
  label.textContent = bar.date.slice(5);

  chip.append(strong, label);
  return chip;
}

function renderResults(results) {
  const entries = Array.from(results.entries());
  entries.sort((a, b) => a[0].localeCompare(b[0]));

  els.resultsGrid.innerHTML = "";
  renderSummary(results, currentWatchlist);

  if (!entries.length) {
    els.resultsGrid.hidden = true;
    els.resultsEmpty.hidden = false;
    els.resultsEmpty.textContent = DEFAULT_EMPTY_COPY;
    els.globalSignal.textContent = "Aucun signal chargé";
    els.globalSignalMeta.textContent = "Ajoute des données pour lancer l’analyse.";
    els.seriesCount.textContent = "0";
    els.latestDate.textContent = "—";
    return;
  }

  els.resultsGrid.hidden = false;
  els.resultsEmpty.hidden = true;
  els.seriesCount.textContent = String(entries.length);

  let strongest = null;

  for (const [symbol, analysis] of entries) {
    const template = els.resultCardTemplate.content.cloneNode(true);
    const card = template.querySelector(".result-card");
    const badge = template.querySelector(".badge");
    const signalStrip = template.querySelector(".signal-strip");

    template.querySelector(".symbol").textContent = symbol;
    template.querySelector(".date-range").textContent = `${analysis.series[0].date} → ${analysis.latest.date}`;
    template.querySelector(".price").textContent = formatNumber(analysis.latest.close);
    template.querySelector(".setup").textContent = analysis.summary.setupCount
      ? `${tdLabel(analysis.summary.setupDirection)} ${analysis.summary.setupCount}`
      : "Aucun";
    template.querySelector(".countdown").textContent = analysis.summary.countdownCount
      ? `${tdLabel(analysis.summary.countdownDirection)} ${analysis.summary.countdownCount}`
      : "Aucun";
    template.querySelector(".perfection").textContent = analysis.summary.perfection;
    template.querySelector(".direction").textContent = tdLabel(analysis.summary.setupDirection);
    template.querySelector(".validation").textContent = analysis.summary.lastValidation;
    template.querySelector(".signal-text").textContent = analysis.summary.signal;
    template.querySelector(".timeline-caption").textContent = `${analysis.series.length} barres`;
    template.querySelector(".chart-caption").textContent = `${formatNumber(Math.min(...analysis.series.map((bar) => bar.close)))} → ${formatNumber(Math.max(...analysis.series.map((bar) => bar.close)))}`;
    renderPriceChart(template.querySelector(".price-chart"), analysis.series);

    badge.textContent = analysis.summary.signal;
    badge.classList.remove("is-buy", "is-sell", "is-wait");
    signalStrip.classList.remove("is-buy", "is-sell");

    if (analysis.summary.signalTone === "buy") {
      badge.classList.add("is-buy");
      signalStrip.classList.add("is-buy");
    } else if (analysis.summary.signalTone === "sell") {
      badge.classList.add("is-sell");
      signalStrip.classList.add("is-sell");
    } else {
      badge.classList.add("is-wait");
    }

    const barsWrap = template.querySelector(".timeline-bars");
    analysis.bars.slice(-18).forEach((bar) => barsWrap.appendChild(renderBarChip(bar)));

    const cardSummary = `${symbol}: ${analysis.summary.signal}`;
    if (!strongest || analysis.summary.signalTone !== "wait") {
      strongest = { ...analysis, symbol, cardSummary };
    }

    els.resultsGrid.appendChild(template);
  }

  if (strongest) {
    els.globalSignal.textContent = strongest.summary.signal;
    els.globalSignalMeta.textContent = `${strongest.symbol} | clôture ${formatNumber(
      strongest.latest.close,
    )} | setup ${strongest.summary.setupCount} | countdown ${strongest.summary.countdownCount}`;
    els.latestDate.textContent = strongest.latest.date;
  } else {
    const latestAnalysis = entries[entries.length - 1][1];
    els.globalSignal.textContent = latestAnalysis.summary.signal;
    els.globalSignalMeta.textContent = `Dernière série mise à jour: ${entries[entries.length - 1][0]}`;
    els.latestDate.textContent = latestAnalysis.latest.date;
  }
}

function showError(message) {
  if (lastResults.size) {
    els.insightText.textContent = `Données conservées: ${message}`;
    els.insightBar.hidden = false;
    return;
  }
  els.resultsGrid.innerHTML = "";
  els.resultsGrid.hidden = true;
  els.resultsEmpty.hidden = false;
  els.resultsEmpty.textContent = message;
  els.summarySection.hidden = true;
  els.globalSignal.textContent = "Analyse interrompue";
  els.globalSignalMeta.textContent = message;
}

function renderSummary(results, watchlist = currentWatchlist) {
  const symbols = Array.from(new Set([...watchlist, ...results.keys()])).sort((a, b) => a.localeCompare(b));
  const entries = symbols.map((symbol) => [symbol, results.get(symbol) || null]);
  els.summaryTableBody.innerHTML = "";
  els.summarySection.hidden = !entries.length;
  if (!entries.length) return;

  const visibleEntries = entries.filter(([, analysis]) => {
    if (!analysis) return summaryFilter === "all";
    const tone = analysis.summary.signalTone;
    if (summaryFilter === "buy") return tone === "buy";
    if (summaryFilter === "sell") return tone === "sell";
    if (summaryFilter === "actionable") return /setup 9|countdown 13/.test(analysis.summary.signal);
    return true;
  });

  for (const [symbol, analysis] of visibleEntries) {
    const row = document.createElement("tr");
    const values = analysis
      ? [
          symbol,
          formatNumber(analysis.latest.close),
          analysis.summary.setupCount ? `${tdLabel(analysis.summary.setupDirection)} ${analysis.summary.setupCount}` : "—",
          analysis.summary.countdownCount ? `${tdLabel(analysis.summary.countdownDirection)} ${analysis.summary.countdownCount}` : "—",
          analysis.summary.signal,
          analysis.latest.date,
        ]
      : [symbol, "—", "—", "—", "Données manquantes", "—"];
    values.forEach((value, index) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (index === 0) cell.className = "summary-symbol";
      if (index === 4) cell.className = `summary-signal is-${analysis?.summary.signalTone || "wait"}`;
      row.appendChild(cell);
    });
    els.summaryTableBody.appendChild(row);
  }
  els.summaryEmpty.hidden = visibleEntries.length > 0;
}

function buildCsv(dataRows) {
  const rows = ["symbol,date,open,high,low,close,volume"];
  for (const bar of dataRows) {
    rows.push([bar.symbol, bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume ?? ""].join(","));
  }
  return rows.join("\n");
}

function buildSampleCsv() {
  return buildCsv(Object.entries(sampleSeries).flatMap(([symbol, series]) => series.map((bar) => ({ symbol, ...bar }))));
}

function loadStoredInputs() {
  const storedWatchlist = localStorage.getItem(STORAGE_KEYS.watchlist);
  const storedCsv = localStorage.getItem(STORAGE_KEYS.csv);

  els.watchlistInput.value = storedWatchlist || DEFAULT_WATCHLIST.join("\n");
  els.csvInput.value = storedCsv || buildSampleCsv();
}

function saveInputs() {
  localStorage.setItem(STORAGE_KEYS.watchlist, els.watchlistInput.value);
  localStorage.setItem(STORAGE_KEYS.csv, els.csvInput.value);
}

async function fetchYahooSeries(symbol, range, interval) {
  const localProxy = window.location.protocol.startsWith("http")
    ? `/api/chart?symbol=${encodeURIComponent(symbol)}&range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}`
    : null;
  const hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"];
  let payload = null;
  let lastError = null;
  const urls = [
    ...(localProxy ? [localProxy] : []),
    ...hosts.map((host) => {
      const url = new URL(`https://${host}/v8/finance/chart/${encodeURIComponent(symbol)}`);
      url.searchParams.set("range", range);
      url.searchParams.set("interval", interval);
      url.searchParams.set("events", "history");
      return url;
    }),
  ];
  for (const url of urls) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`${symbol}: fournisseur indisponible (${response.status})`);
      payload = await response.json();
      break;
    } catch (error) {
      lastError = error;
    }
  }
  if (!payload) {
    const reason = lastError instanceof TypeError
      ? "le navigateur bloque la requête réseau"
      : lastError instanceof Error ? lastError.message : "source indisponible";
    throw new Error(`${symbol}: ${reason}`);
  }
  const result = payload.chart?.result?.[0];
  if (!result?.timestamp?.length) throw new Error(`${symbol}: aucune donnée retournée`);
  const quote = result.indicators?.quote?.[0];
  const timestamps = result.timestamp;
  return timestamps.map((timestamp, index) => ({
    date: new Date(timestamp * 1000).toISOString().slice(0, 10),
    open: quote.open[index],
    high: quote.high[index],
    low: quote.low[index],
    close: quote.close[index],
    volume: quote.volume?.[index] ?? null,
  })).filter((bar) => [bar.open, bar.high, bar.low, bar.close].every((value) => Number.isFinite(value)));
}

async function fetchMarketData(options = {}) {
  const watchlist = parseWatchlist(els.watchlistInput.value);
  if (!watchlist.length) {
    showError("Ajoute au moins un symbole avant d’actualiser le marché.");
    return;
  }
  if (!options.background) els.fetchMarket.disabled = true;
  els.marketStatus.textContent = options.background ? "Surveillance en cours..." : "Chargement...";
  try {
    const range = els.marketRange.value;
    const interval = els.marketInterval.value;
    const rows = [];
    const errors = [];
    for (const symbol of watchlist) {
      try {
        const series = await fetchYahooSeries(symbol, range, interval);
        series.forEach((bar) => rows.push({ symbol, ...bar }));
      } catch (error) {
        errors.push(error instanceof Error ? error.message : `${symbol}: erreur inconnue`);
      }
    }
    if (!rows.length) throw new Error(errors.join(" | ") || "Aucune donnée de marché reçue.");
    els.csvInput.value = buildCsv(rows);
    saveInputs();
    els.marketStatus.textContent = `${rows.length} barres reçues${options.background ? " · surveillance active" : ""}`;
    scan();
    if (errors.length) {
      els.marketStatus.textContent = `${rows.length} barres reçues · ${errors.length} symbole(s) ignoré(s)`;
      els.insightText.textContent = `Données partielles: ${errors.join(" | ")}`;
      els.insightBar.hidden = false;
    }
  } catch (error) {
    els.marketStatus.textContent = "Échec de l’actualisation";
    const detail = error instanceof Error ? error.message : "Impossible de charger le marché.";
    showError(`${detail}. Essaie d’ouvrir l’application via un serveur local, ou importe un CSV OHLC.`);
  } finally {
    if (!options.background) els.fetchMarket.disabled = false;
  }
}

function scan() {
  try {
    const watchlist = parseWatchlist(els.watchlistInput.value);
    currentWatchlist = watchlist;
    const rows = parseCsv(els.csvInput.value);
    const grouped = groupBySymbol(rows);
    const results = new Map();

    watchlist.forEach((symbol) => {
      const series = grouped.get(symbol);
      if (!series || series.length < 5) return;
      results.set(symbol, { ...analyzeSeries(series), series });
    });

    els.watchlistCount.textContent = String(watchlist.length);
    if (lastResults.size) notifySignals(results);
    renderResults(results);
    lastResults = results;
    saveInputs();
  } catch (error) {
    showError(error instanceof Error ? error.message : "Erreur inconnue pendant l'analyse.");
  }
}

function resetWatchlist() {
  els.watchlistInput.value = DEFAULT_WATCHLIST.join("\n");
  scan();
}

function addExampleSymbols() {
  const current = parseWatchlist(els.watchlistInput.value);
  const next = Array.from(new Set([...current, "SPY", "QQQ", "IWM"]));
  els.watchlistInput.value = next.join("\n");
  scan();
}

function loadSample() {
  els.csvInput.value = buildSampleCsv();
  scan();
}

async function importCsvFile(file) {
  const text = await file.text();
  els.csvInput.value = text;
  scan();
}

els.saveWatchlist.addEventListener("click", scan);
els.scanNow.addEventListener("click", scan);
els.loadSample.addEventListener("click", loadSample);
els.fetchMarket.addEventListener("click", fetchMarketData);
els.exportResults.addEventListener("click", exportResults);
els.enableAlerts.addEventListener("click", async () => {
  if (!("Notification" in window)) return;
  const permission = await Notification.requestPermission();
  alertPermission = permission === "granted";
  localStorage.setItem(STORAGE_KEYS.alerts, alertPermission ? "granted" : "denied");
  setAlertUi();
  if (alertPermission) startAlertMonitoring();
});
document.querySelectorAll("[data-summary-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    summaryFilter = button.dataset.summaryFilter;
    document.querySelectorAll("[data-summary-filter]").forEach((candidate) => {
      candidate.classList.toggle("is-active", candidate === button);
    });
    renderSummary(lastResults);
  });
});
els.indexUniverse.addEventListener("change", loadIndexPreset);
els.fetchIndexComposition.addEventListener("click", fetchIndexComposition);
els.indexInput.addEventListener("input", updateIndexStatus);
els.addIndexSymbols.addEventListener("click", () => mergeIndexIntoWatchlist(false));
els.replaceWithIndex.addEventListener("click", () => mergeIndexIntoWatchlist(true));
els.indexFile.addEventListener("change", async (event) => {
  const [file] = event.target.files || [];
  if (!file) return;
  els.indexInput.value = await file.text();
  updateIndexStatus();
});
els.clearResults.addEventListener("click", () => {
  els.resultsGrid.innerHTML = "";
  els.resultsGrid.hidden = true;
  els.resultsEmpty.hidden = false;
  els.resultsEmpty.textContent = DEFAULT_EMPTY_COPY;
  els.globalSignal.textContent = "Aucun signal chargé";
  els.globalSignalMeta.textContent = "Ajoute des données pour lancer l’analyse.";
  els.seriesCount.textContent = "0";
  els.latestDate.textContent = "—";
  els.summarySection.hidden = true;
});
els.resetWatchlist.addEventListener("click", resetWatchlist);
els.addExample.addEventListener("click", addExampleSymbols);
els.csvFile.addEventListener("change", async (event) => {
  const [file] = event.target.files || [];
  if (!file) return;
  await importCsvFile(file);
});

els.watchlistInput.addEventListener("input", () => {
  els.watchlistCount.textContent = String(parseWatchlist(els.watchlistInput.value).length);
});

els.csvInput.addEventListener("input", () => {
  try {
    const rows = parseCsv(els.csvInput.value);
    const latestDate = rows.reduce((max, row) => (row.date > max ? row.date : max), "—");
    els.latestDate.textContent = latestDate === "—" ? "—" : latestDate;
  } catch {
    els.latestDate.textContent = "—";
  }
});

loadStoredInputs();
loadIndexPreset();
setAlertUi();
els.watchlistCount.textContent = String(parseWatchlist(els.watchlistInput.value).length);
scan();
if (alertPermission && "Notification" in window && Notification.permission === "granted") startAlertMonitoring();
