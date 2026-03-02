import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import io

def get_td_data(df):
    if len(df) < 20: return 0, 0, "Neutre"
    closes, highs, lows = df['Close'], df['High'], df['Low']
    setup_count, direction = 0, "Neutre"
    for i in range(len(df)-1, 4, -1):
        if closes.iloc[i] > closes.iloc[i-4]:
            if direction == "Achat": break
            direction, setup_count = "Vente", setup_count + 1
        elif closes.iloc[i] < closes.iloc[i-4]:
            if direction == "Vente": break
            direction, setup_count = "Achat", setup_count + 1
        else: break
    countdown_count = 0
    for i in range(len(df)-1, max(0, len(df)-30), -1):
        if direction == "Vente" and closes.iloc[i] >= highs.iloc[i-2]: countdown_count += 1
        elif direction == "Achat" and closes.iloc[i] <= lows.iloc[i-2]: countdown_count += 1
    return setup_count, min(countdown_count, 13), direction

st.set_page_config(layout="wide", page_title="CIO TD Monitor")
st.title("🏛️ CIO Terminal - TD Sequential")

tickers_input = st.sidebar.text_area("Titres (séparés par virgules)", "AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,BRK-B,LLY,AVGO,V,JPM,XOM,MA,UNH,PG,COST,HD,JNJ,ABBV,CRM,NFLX,AMD,ADBE,WMT")
list_tickers = [t.strip().upper() for t in tickers_input.split(",")]

if st.button('Lancer le Scan'):
    results = []
    for symbol in list_tickers:
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if df.empty: continue
            s, c, d = get_td_data(df)
            results.append({"Ticker": symbol, "Prix": round(df['Close'].iloc[-1], 2), "Setup (9)": s, "Countdown (13)": c, "Tendance": d})
        except: continue
    df_res = pd.DataFrame(results)
    st.dataframe(df_res.style.background_gradient(cmap='OrRd', subset=['Setup (9)', 'Countdown (13)']), use_container_width=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_res.to_excel(writer, index=False)
    st.download_button(label="📥 Export Excel", data=output.getvalue(), file_name="TD_Report.xlsx")
