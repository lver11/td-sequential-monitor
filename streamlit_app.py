import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(page_title="TD Sequential Monitor", layout="wide")


PRESETS = {
    "S&P 500 - exemples": "AAPL\nMSFT\nNVDA\nAMZN\nMETA\nGOOGL\nAVGO\nCOST\nJPM\nXOM",
    "Nasdaq-100 - exemples": "AAPL\nMSFT\nNVDA\nAMZN\nMETA\nGOOGL\nAMD\nNFLX\nADBE\nQCOM",
    "S&P/TSX 60 - exemples": "RY.TO\nTD.TO\nSHOP.TO\nCNR.TO\nCP.TO\nENB.TO\nBNS.TO\nBMO.TO\nCNQ.TO\nSU.TO",
    "Matières premières": "GC=F\nSI=F\nCL=F\nBZ=F\nNG=F\nHG=F\nZC=F\nZS=F",
    "Devises": "EURUSD=X\nGBPUSD=X\nUSDJPY=X\nUSDCAD=X\nAUDUSD=X\nUSDCHF=X",
    "Taux": "^IRX\n^FVX\n^TNX\n^TYX\nZQ=F\nZN=F",
}


def td_analyze(frame):
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    if len(frame) < 5:
        return None
    buy_setup = sell_setup = 0
    active = None
    buy_count = sell_count = 0
    setup_values = []
    countdown_values = []
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
        setup_values.append((active, setup))
        countdown_values.append(("Buy" if buy_count else "Sell" if sell_count else None, max(buy_count, sell_count)))
    last_direction, setup = setup_values[-1]
    count_direction, countdown = countdown_values[-1]
    if countdown == 13:
        signal = f"{count_direction} countdown 13"
    elif setup:
        signal = f"{last_direction} setup {setup}"
    else:
        signal = "Aucun setup confirmé"
    return {
        "Clôture": round(float(frame["Close"].iloc[-1]), 2),
        "Setup": f"{last_direction} {setup}" if setup else "—",
        "Countdown": f"{count_direction} {countdown}" if countdown else "—",
        "Signal": signal,
        "Date": frame.index[-1].strftime("%Y-%m-%d"),
    }


st.title("TD Sequential Monitor")
st.caption("Scanner multi-actifs Tom DeMark : actions, indices, matières premières, devises et taux.")

with st.sidebar:
    st.header("Univers")
    preset = st.selectbox("Modèle", ["Personnalisé", *PRESETS.keys()])
    default_symbols = PRESETS.get(preset, "AAPL\nMSFT\nNVDA\nTSLA")
    symbols_text = st.text_area("Un symbole par ligne", default_symbols, height=250)
    period = st.selectbox("Historique", ["6mo", "1y", "2y", "5y"], index=1)
    interval = st.selectbox("Intervalle", ["1d", "1wk", "1mo"])
    scan_button = st.button("Lancer le scan", type="primary", use_container_width=True)

symbols = list(dict.fromkeys(line.strip().upper() for line in symbols_text.splitlines() if line.strip()))
st.metric("Titres suivis", len(symbols))

if scan_button:
    rows = []
    progress = st.progress(0)
    status = st.empty()
    for index, symbol in enumerate(symbols, start=1):
        status.write(f"Chargement de {symbol}...")
        try:
            data = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            result = td_analyze(data)
            rows.append({"Titre": symbol, **(result or {"Clôture": "—", "Setup": "—", "Countdown": "—", "Signal": "Données manquantes", "Date": "—"})})
        except Exception:
            rows.append({"Titre": symbol, "Clôture": "—", "Setup": "—", "Countdown": "—", "Signal": "Données manquantes", "Date": "—"})
        progress.progress(index / len(symbols))
    status.write("Analyse terminée.")
    result_frame = pd.DataFrame(rows)
    st.subheader("Résumé des signaux")
    st.dataframe(result_frame, use_container_width=True, hide_index=True)
    csv = result_frame.to_csv(index=False).encode("utf-8")
    st.download_button("Exporter le résumé CSV", csv, "td-sequential-signaux.csv", "text/csv")
else:
    st.info("Choisis un univers puis clique sur « Lancer le scan ».")
