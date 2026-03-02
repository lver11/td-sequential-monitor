import streamlit as st
import yfinance as yf
import pandas as pd
import io

def get_td_data(df):
    if df is None or len(df) < 20: return 0, 0, "Neutre"
    closes = df['Close'].dropna()
    highs = df['High'].dropna()
    lows = df['Low'].dropna()
    if len(closes) < 20: return 0, 0, "Neutre"
    
    setup_count, direction = 0, "Neutre"
    for i in range(len(closes)-1, 4, -1):
        if closes.iloc[i] > closes.iloc[i-4]:
            if direction == "Achat": break
            direction, setup_count = "Vente", setup_count + 1
        elif closes.iloc[i] < closes.iloc[i-4]:
            if direction == "Vente": break
            direction, setup_count = "Achat", setup_count + 1
        else: break
            
    countdown_count = 0
    for i in range(len(closes)-1, max(0, len(closes)-30), -1):
        if direction == "Vente" and closes.iloc[i] >= highs.iloc[i-2]: countdown_count += 1
        elif direction == "Achat" and closes.iloc[i] <= lows.iloc[i-2]: countdown_count += 1
    return setup_count, min(countdown_count, 13), direction

st.set_page_config(layout="wide", page_title="CIO TD Monitor")
st.title("🏛️ CIO Terminal - TD Sequential")

tickers_input = st.sidebar.text_area("Titres", "AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,AMD,ADBE")
list_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if st.button('Lancer le Scan'):
    results = []
    with st.spinner('Analyse en cours...'):
        for symbol in list_tickers:
            try:
                df = yf.download(symbol, period="6mo", interval="1d", progress=False)
                if not df.empty:
                    s, c, d = get_td_data(df)
                    results.append({
                        "Ticker": symbol, 
                        "Prix": float(df['Close'].iloc[-1]), 
                        "Setup": int(s), 
                        "Countdown": int(c), 
                        "Tendance": d
                    })
            except: continue
    
    if results:
        df_res = pd.DataFrame(results)
        # Correction de l'erreur de style : on vérifie si les colonnes existent
        st.dataframe(df_res.style.background_gradient(cmap='OrRd', subset=['Setup', 'Countdown']), use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button(label="📥 Export Excel", data=output.getvalue(), file_name="TD_Report.xlsx")
    else:
        st.warning("Aucune donnée trouvée. Vérifiez les symboles.")
