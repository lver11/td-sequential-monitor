import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(page_title="TD Sequential Monitor", layout="wide", initial_sidebar_state="expanded")

PRESETS = {
    "S&P 500 - exemples": "AAPL\nMSFT\nNVDA\nAMZN\nMETA\nGOOGL\nAVGO\nCOST\nJPM\nXOM",
    "Nasdaq-100 - exemples": "AAPL\nMSFT\nNVDA\nAMZN\nMETA\nGOOGL\nAMD\nNFLX\nADBE\nQCOM",
    "S&P/TSX 60 - exemples": "RY.TO\nTD.TO\nSHOP.TO\nCNR.TO\nCP.TO\nENB.TO\nBNS.TO\nBMO.TO\nCNQ.TO\nSU.TO",
    "Matières premières": "GC=F\nSI=F\nCL=F\nBZ=F\nNG=F\nHG=F\nZC=F\nZS=F",
    "Devises": "EURUSD=X\nGBPUSD=X\nUSDJPY=X\nUSDCAD=X\nAUDUSD=X\nUSDCHF=X",
    "Taux": "^IRX\n^FVX\n^TNX\n^TYX\nZQ=F\nZN=F",
}

st.markdown(
    """
    <style>
    .stApp { background: #0e131a; color: #f4efe4; }
    [data-testid="stSidebar"] { background: #161d27; }
    h1, h2, h3 { font-family: Georgia, serif; color: #f4efe4; }
    .hero { padding: 1rem 0 1.2rem; border-bottom: 1px solid rgba(142,164,184,.18); margin-bottom: 1.2rem; }
    .kicker { color: #c58a3a; text-transform: uppercase; letter-spacing: .12em; font-size: .76rem; }
    .hero p, .muted { color: #a8b1bf; }
    </style>
    <div class="hero">
      <div class="kicker">TD Sequential scanner</div>
      <h1>Signaux Tom DeMark sur une watchlist éditable</h1>
      <p>Actions, indices, matières premières, devises et taux avec résumé des setups 9 et countdowns 13.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def parse_symbols(text):
    return list(dict.fromkeys(line.strip().upper() for line in text.splitlines() if line.strip()))


@st.cache_data(ttl=900, show_spinner=False)
def download_data(symbol, period, interval):
    data = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(subset=["Open", "High", "Low", "Close"])


def analyze(frame):
    if len(frame) < 5:
        return None
    buy_setup = sell_setup = buy_count = sell_count = 0
    active = None
    latest_setup = (None, 0)
    latest_countdown = (None, 0)
    for i in range(len(frame)):
        close = float(frame["Close"].iloc[i])
        buy = i >= 4 and close < float(frame["Close"].iloc[i - 4])
        sell = i >= 4 and close > float(frame["Close"].iloc[i - 4])
        if buy:
            buy_setup += 1
            sell_setup = 0
            active = "Buy"
        elif sell:
            sell_setup += 1
            buy_setup = 0
            active = "Sell"
        else:
            buy_setup = sell_setup = 0
        setup = buy_setup if buy_setup else sell_setup
        if setup == 9:
            buy_count = sell_count = 0
        if active == "Buy" and i >= 2 and close <= float(frame["Low"].iloc[i - 2]):
            buy_count = min(13, buy_count + 1)
        if active == "Sell" and i >= 2 and close >= float(frame["High"].iloc[i - 2]):
            sell_count = min(13, sell_count + 1)
        latest_setup = (active, setup)
        latest_countdown = ("Buy", buy_count) if buy_count else (("Sell", sell_count) if sell_count else (None, 0))
    setup_direction, setup = latest_setup
    count_direction, countdown = latest_countdown
    if countdown == 13:
        signal = f"{count_direction} countdown 13"
    elif setup:
        signal = f"{setup_direction} setup {setup}"
    else:
        signal = "Aucun setup confirmé"
    return {
        "Clôture": round(float(frame["Close"].iloc[-1]), 2),
        "Setup": f"{setup_direction} {setup}" if setup else "—",
        "Countdown": f"{count_direction} {countdown}" if countdown else "—",
        "Signal": signal,
        "Date": frame.index[-1].strftime("%Y-%m-%d"),
        "Series": frame,
    }


def run_scan(symbols, period, interval):
    rows = []
    details = {}
    progress = st.progress(0)
    status = st.empty()
    for index, symbol in enumerate(symbols, start=1):
        status.write(f"Récupération de {symbol}...")
        try:
            data = download_data(symbol, period, interval)
            result = analyze(data)
        except Exception:
            result = None
        if result:
            details[symbol] = result
            rows.append({"Titre": symbol, **{key: value for key, value in result.items() if key != "Series"}})
        else:
            rows.append({"Titre": symbol, "Clôture": "—", "Setup": "—", "Countdown": "—", "Signal": "Données manquantes", "Date": "—"})
        progress.progress(index / max(len(symbols), 1))
    status.write("Analyse terminée.")
    progress.empty()
    return pd.DataFrame(rows), details


with st.sidebar:
    st.header("Watchlist")
    preset = st.selectbox("Univers", ["Personnalisé", *PRESETS.keys()])
    default_symbols = PRESETS.get(preset, "AAPL\nMSFT\nNVDA\nTSLA")
    symbols_text = st.text_area("Un titre par ligne", default_symbols, height=180)
    st.caption("Titres canadiens : suffixe `.TO`, par exemple `SHOP.TO`.")
    st.header("Marché")
    period = st.selectbox("Historique", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("Intervalle", ["1d", "1wk", "1mo"])
    scan_button = st.button("Lancer le scan", type="primary", use_container_width=True)
    st.header("Alertes")
    st.checkbox("Afficher les signaux 9 / 13", value=True, key="show_alerts")
    st.caption("Les alertes Streamlit apparaissent après chaque scan. Pour des notifications navigateur en arrière-plan, utilise la version locale.")

symbols = parse_symbols(symbols_text)
if scan_button or "scan_results" not in st.session_state:
    st.session_state.scan_results, st.session_state.scan_details = run_scan(symbols, period, interval)
else:
    st.session_state.scan_results = st.session_state.scan_results[st.session_state.scan_results["Titre"].isin(symbols)]

result_frame = st.session_state.scan_results
details = st.session_state.get("scan_details", {})
st.metric("Titres suivis", len(symbols))

st.subheader("Résumé des signaux")
metric_cols = st.columns(4)
metric_cols[0].metric("Titres affichés", len(result_frame))
metric_cols[1].metric("Signaux BUY", int(result_frame["Signal"].str.contains("Buy", na=False).sum()))
metric_cols[2].metric("Signaux SELL", int(result_frame["Signal"].str.contains("Sell", na=False).sum()))
metric_cols[3].metric("Setup / countdown 9-13", int(result_frame["Signal"].str.contains("9|13", na=False).sum()))

filter_value = st.radio("Filtrer", ["Tous", "Buy", "Sell", "9 / 13"], horizontal=True)
filtered = result_frame.copy()
if filter_value == "Buy":
    filtered = filtered[filtered["Signal"].str.contains("Buy", na=False)]
elif filter_value == "Sell":
    filtered = filtered[filtered["Signal"].str.contains("Sell", na=False)]
elif filter_value == "9 / 13":
    filtered = filtered[filtered["Signal"].str.contains("9|13", na=False)]
st.dataframe(filtered, use_container_width=True, hide_index=True)
st.download_button("Exporter le résumé CSV", result_frame.to_csv(index=False).encode("utf-8"), "td-sequential-signaux.csv", "text/csv")

st.subheader("Détails par titre")
for symbol in symbols:
    result = details.get(symbol)
    with st.expander(symbol, expanded=False):
        if not result:
            st.warning("Données manquantes pour ce titre.")
            continue
        cols = st.columns(4)
        cols[0].metric("Clôture", result["Clôture"])
        cols[1].metric("Setup", result["Setup"])
        cols[2].metric("Countdown", result["Countdown"])
        cols[3].metric("Date", result["Date"])
        st.line_chart(result["Series"]["Close"], height=180)
