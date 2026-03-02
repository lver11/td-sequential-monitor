import streamlit as st
import yfinance as yf
import pandas as pd
import io

# Configuration de la page
st.set_page_config(layout="wide", page_title="CIO TD Monitor")

def get_td_data(df):
    """Calcule les séquences TD Setup et Countdown."""
    if df is None or len(df) < 20: 
        return 0, 0, "Neutre"
    
    # Nettoyage des données
    df = df.copy()
    closes = df['Close']
    highs = df['High']
    lows = df['Low']
    
    # 1. Calcul du Setup (9)
    setup_count = 0
    direction = "Neutre"
    for i in range(len(df)-1, 4, -1):
        if closes.iloc[i] > closes.iloc[i-4]:
            if direction == "Achat": break
            direction = "Vente"
            setup_count += 1
        elif closes.iloc[i] < closes.iloc[i-4]:
            if direction == "Vente": break
            direction = "Achat"
            setup_count += 1
        else:
            break

    # 2. Calcul du Countdown (13)
    countdown_count = 0
    for i in range(len(df)-1, max(0, len(df)-30), -1):
        if direction == "Vente" and closes.iloc[i] >= highs.iloc[i-2]:
            countdown_count += 1
        elif direction == "Achat" and closes.iloc[i] <= lows.iloc[i-2]:
            countdown_count += 1
            
    return setup_count, min(countdown_count, 13), direction

# Interface Utilisateur
st.title("🏛️ CIO Terminal - TD Sequential")

# Sidebar pour les titres
tickers_default = "AAPL, MSFT, GOOGL, TSLA, NVDA, AMZN, META, NFLX, AMD, ADBE"
tickers_input = st.sidebar.text_area("Symboles boursiers (séparés par virgules)", tickers_default)
list_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if st.button('Lancer le Scan du Portefeuille'):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for index, symbol in enumerate(list_tickers):
        status_text.text(f"Récupération de {symbol}...")
        try:
            # Utilisation de Ticker pour plus de fiabilité
            tk = yf.Ticker(symbol)
            df = tk.history(period="1y") # 1 an pour avoir assez de recul
            
            if not df.empty:
                s, c, d = get_td_data(df)
                results.append({
                    "Ticker": symbol, 
                    "Prix": round(float(df['Close'].iloc[-1]), 2), 
                    "Setup": int(s), 
                    "Countdown": int(c), 
                    "Tendance": d
                })
        except Exception as e:
            st.error(f"Erreur sur {symbol}: {str(e)}")
            continue
        
        progress_bar.progress((index + 1) / len(list_tickers))
    
    status_text.text("Analyse terminée.")
    
    if results:
        df_res = pd.DataFrame(results)
        
        # Affichage du tableau avec coloration
        st.subheader("Résultats de l'analyse d'épuisement")
        st.dataframe(
            df_res.style.background_gradient(cmap='OrRd', subset=['Setup', 'Countdown']),
            use_container_width=True
        )
        
        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_res.to_excel(writer, index=False, sheet_name='Analyse_TD')
        
        st.download_button(
            label="📥 Télécharger le rapport Excel",
            data=output.getvalue(),
            file_name="Rapport_TD_Sequential.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("Aucune donnée n'a pu être récupérée. Vérifiez votre connexion ou les symboles.")
