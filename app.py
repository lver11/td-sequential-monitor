if st.button('Lancer le Scan'):
    results = []
    # On crée une barre de progression pour voir l'avancement
    progress_bar = st.progress(0)
    
    for index, symbol in enumerate(list_tickers):
        try:
            # On ajoute un message pour savoir quel titre est analysé
            st.write(f"Analyse de {symbol}...")
            
            # On force la récupération sur une période fixe
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="6mo")
            
            if not df.empty:
                s, c, d = get_td_data(df)
                results.append({
                    "Ticker": symbol, 
                    "Prix": float(df['Close'].iloc[-1]), 
                    "Setup": int(s), 
                    "Countdown": int(c), 
                    "Tendance": d
                })
        except Exception as e:
            st.error(f"Erreur sur {symbol}: {e}")
            continue
        
        # Mise à jour de la barre de progression
        progress_bar.progress((index + 1) / len(list_tickers))
    
    if results:
        df_res = pd.DataFrame(results)
        st.success("Analyse terminée !")
        st.dataframe(df_res.style.background_gradient(cmap='OrRd', subset=['Setup', 'Countdown']), use_container_width=True)
    else:
        st.warning("Toujours aucune donnée. Essayez avec un seul symbole (ex: AAPL) pour tester.")
