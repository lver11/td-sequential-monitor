"""
TD Sequential – Multi-Asset Scanner
====================================
Signaux DeMark 9 et 13 sur actions, ETF, taux, commodities.
Usage:
  python td_sequential_app.py                    # lance le dashboard web
  python td_sequential_app.py --report           # génère un rapport HTML dans workspace/reports/
  python td_sequential_app.py --symbols AAPL,CL=F --export td_signals.csv

Signaux detectados:
  BUY Setup 9  : 9 bougies baissières consécutives après un comptage haussier
  SELL Setup 9 : 9 bougies haussières consécutives après un comptage baissier
  BUY  Count 13: 13 barres confirmées (pas de stop) → signal d'achat
  SELL Count 13: 13 barres confirmées → signal de vente
  Exhaustion   : Le setup est invalidé (close < close 4 barres avant pour BUY,
                 close > close 4 barres avant pour SELL)
"""

import os, sys, json, textwrap
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ──────────────────────────────────────────────
#  PARAMÈTRES GLOBAUX (ajustables)
# ──────────────────────────────────────────────
class Config:
    LOOKBACK_BARS  = 60       # nombre de barres pour le calcul
    CLOSE_OVERRIDE = 5        # barres de close nécessaires pour invalider un setup
    MIN_SETUP_BARS = 9        # taille minimum d'un setup TD
    COUNT_TRIGGER  = 13       # barres pour Count 13 (signal fort)

Configurable = {             # accessible depuis CLI / web
    "lookback_bars" : 60,
    "close_override" : 5,
    "min_setup_bars" : 9,
    "count_trigger"  : 13,
}

# ──────────────────────────────────────────────
#  UNIVERS DES ACTIFS
# ──────────────────────────────────────────────
UNIVERSE = {
    # ── Actions USA ──────────────────────────────────────────────────
    "Actions US": {
        "AAPL" : "Apple Inc.",
        "MSFT" : "Microsoft",
        "GOOGL": "Alphabet",
        "AMZN" : "Amazon",
        "NVDA" : "Nvidia",
        "META" : "Meta Platforms",
        "TSLA" : "Tesla",
        "AMD"  : "AMD",
        "NFLX" : "Netflix",
        "SPY"  : "SPDR S&P 500 ETF",
        "QQQ"  : "Invesco QQQ",
        "JPM"  : "JPMorgan Chase",
        "GS"   : "Goldman Sachs",
    },
    # ── ETF ──────────────────────────────────────────────────────────
    "ETF": {
        "SPY"  : "SPDR S&P 500",
        "QQQ"  : "Nasdaq-100",
        "IWM"  : "iShares Russell 2000",
        "EFA"  : "iShares MSCI EAFE",
        "EEM"  : "iShares MSCI EM",
        "TLT"  : "iShares 20Y Treasury",
        "IEF"  : "iShares 7-10Y Treasury",
        "LQD"  : "iShares Investment Grade Corp",
        "HYG"  : "iShares High Yield Corp",
        "GLD"  : "SPDR Gold Shares",
        "SLV"  : "iShares Silver Trust",
        "XLE"  : "Energy Select Sector SPDR",
        "XLF"  : "Financial Select Sector SPDR",
        "XLK"  : "Tech Select Sector SPDR",
        "ARKK": "ARK Innovation ETF",
        "VTI" : "Vanguard Total Stock Market",
        "VEA" : "Vanguard FTSE Developed Markets",
        "BND" : "Vanguard Total Bond Market",
    },
    # ── Taux d'intérêt (形式的 = taux courts / longs) ──────────────────
    "Taux d'intérêt": {
        "^IRX" : "Treasury Bill 13 sem.",
        "^FVX" : "Treasury Note 5Y",
        "^TNX" : "Treasury Note 10Y",
        "^TYX" : "Treasury Bond 30Y",
        "UBG"  : "ProShares Ultra Bloomberg Nat Gas",
        "UST"  : "Via Utilities HOLDRs (proxy)",
    },
    # ── Commodities ──────────────────────────────────────────────────
    "Commodities": {
        "CL=F" : "Brent Crude Oil",
        "GC=F" : "Gold Futures",
        "SI=F" : "Silver Futures",
        "HG=F" : "Copper Futures",
        "NG=F" : "Natural Gas Futures",
        "ZC=F" : "Corn Futures",
        "ZS=F" : "Soybeans Futures",
        "ZW=F" : "Wheat Futures",
        "ZL=F" : "Soybean Oil Futures",
        "LE=F" : "Live Cattle Futures",
        "HE=F" : "Lean Hogs Futures",
        "PL=F" : "Platinum Futures",
        "PA=F" : "Palladium Futures",
        "CT=F" : "Cotton Futures",
        "KC=F" : "Coffee Futures",
        "SB=F" : "Sugar Futures",
        "CC=F" : "Cocoa Futures",
        "OJ=F" : "OJ Frozen Conc. Juice Futures",
        "ZIB"  : "Intercontinental Exchange",
    },
}

# Intervalle temporel par défaut
DEFAULT_INTERVAL = "1d"   # daily

# ──────────────────────────────────────────────
#  CORE: Téléchargement des données
# ──────────────────────────────────────────────
def fetch_data(ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Télécharge les données OHLC via yfinance."""
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True,
                         progress=False, threads=True)
        df = df.dropna()
        return df
    except Exception as e:
        return pd.DataFrame()

# ──────────────────────────────────────────────
#  CORE: Calcul TD Sequential
# ──────────────────────────────────────────────
def compute_td_sequential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique l'algorithme TD Sequential sur un DataFrame OHLC.

    Colonnes ajoutées:
      td_buy_setup    : valeur > 0 pendant un buy setup (1-13)
      td_sell_setup   : valeur > 0 pendant un sell setup (1-13)
      td_count_buy    : lignes avec Count 13 BUY validés
      td_count_sell   : lignes avec Count 13 SELL validés
      td_exhaustion   : lignes où le setup est épuisé
      setup_phase     : 'buy' / 'sell' / 'none'
    """
    n = len(df)
    close = df["Close"].values
    high  = df["High"].values
    low   = df["Low"].values

    td_buy  = np.zeros(n, dtype=np.float32)
    td_sell = np.zeros(n, dtype=np.float32)
    cb_buy  = np.zeros(n, dtype=int)   # Count BUY
    cb_sell = np.zeros(n, dtype=int)   # Count SELL
    exhaust = np.zeros(n, dtype=int)

    phase = "none"   # 'buy' | 'sell' | 'none'
    buy_count  = 0
    sell_count = 0

    for i in range(1, n):
        # ── Calcul du setup TD ─────────────────────────────
        # Buy setup : close[i] < close[i-4]
        # Sell setup: close[i] > close[i-4]
        if close[i] < close[i-4]:
            new_phase = "buy"
        elif close[i] > close[i-4]:
            new_phase = "sell"
        else:
            new_phase = phase

        # Détection du changement de phase
        if new_phase != phase:
            if new_phase == "buy" and phase in ("sell", "none"):
                buy_count  = 1
                sell_count = 0
            elif new_phase == "sell" and phase in ("buy", "none"):
                sell_count = 1
                buy_count  = 0
            else:
                if new_phase == "buy":
                    buy_count  += 1
                else:
                    sell_count += 1
            phase = new_phase
        else:
            if phase == "buy":
                buy_count  += 1
            elif phase == "sell":
                sell_count += 1

        # ── Enregistrement du setup ───────────────────────
        if phase == "buy" and 0 < buy_count <= 13:
            td_buy[i] = buy_count
        if phase == "sell" and 0 < sell_count <= 13:
            td_sell[i] = sell_count

        # ── Count 13: confirmation du signal ─────────────
        # BUY Count 13: barres 9 à 13 toutes baissières,
        # et close[bar13] < close[bar9 - 4]
        if phase == "buy" and buy_count == 13:
            # Vérifier qu'il n'y a pas eu d'amélioration de close vs 4 barres avant
            # (pas de close supérieur à la barre 9)
            good = True
            for b in range(i-12, i+1):
                if b >= 0 and close[b] > close[i-12 - 4]:
                    good = False
                    break
            if good:
                cb_buy[i] = 1

        if phase == "sell" and sell_count == 13:
            good = True
            for b in range(i-12, i+1):
                if b >= 0 and close[b] < close[i-12 - 4]:
                    good = False
                    break
            if good:
                cb_sell[i] = 1

        # ── Exhaustion: close[bar] > close[bar-4] rompt le buy setup
        if phase == "buy" and i >= 4:
            if close[i] > close[i-4]:
                exhaust[i] = 1
                phase = "sell"
                sell_count = 1
                buy_count  = 0
        elif phase == "sell" and i >= 4:
            if close[i] < close[i-4]:
                exhaust[i] = 1
                phase = "buy"
                buy_count  = 1
                sell_count = 0

    result = df.copy()
    result["td_buy_setup"] = td_buy
    result["td_sell_setup"] = td_sell
    result["td_count_buy"]  = cb_buy
    result["td_count_sell"] = cb_sell
    result["td_exhaustion"] = exhaust
    result["td_phase"] = phase if n else "none"
    return result

# ──────────────────────────────────────────────
#  CORE: Extraction des signaux
# ──────────────────────────────────────────────
def extract_signals(df: pd.DataFrame, ticker: str, name="") -> list:
    """Extrait la liste des signaux trouvés dans la série."""
    signals = []
    n = len(df)
    if n < 15:
        return signals

    close = df["Close"].values
    # handle numpy array scalar → Python float
    if hasattr(close[0], 'item'):
        close = np.array([float(x) for x in close])

    for i in range(13, n):
        date = df.index[i]
        close_i = float(close[i])

        # Count 13 BUY
        if df["td_count_buy"].iloc[i]:
            signals.append({
                "ticker"   : ticker,
                "name"    : name,
                "date"    : date.strftime("%Y-%m-%d"),
                "type"    : "BUY Count 13",
                "price"   : round(float(close[i]), 2),
                "strength": "STRONG",
            })
        # Count 13 SELL
        elif df["td_count_sell"].iloc[i]:
            signals.append({
                "ticker"   : ticker,
                "name"    : name,
                "date"    : date.strftime("%Y-%m-%d"),
                "type"    : "SELL Count 13",
                "price"   : round(float(close[i]), 2),
                "strength": "STRONG",
            })
        # Setup 9
        elif df["td_buy_setup"].iloc[i] == 9:
            signals.append({
                "ticker"   : ticker,
                "name"    : name,
                "date"    : date.strftime("%Y-%m-%d"),
                "type"    : "BUY Setup 9",
                "price"   : round(float(close[i]), 2),
                "strength": "MEDIUM",
            })
        elif df["td_sell_setup"].iloc[i] == 9:
            signals.append({
                "ticker"   : ticker,
                "name"    : name,
                "date"    : date.strftime("%Y-%m-%d"),
                "type"    : "SELL Setup 9",
                "price"   : round(float(close[i]), 2),
                "strength": "MEDIUM",
            })
        # Exhaustion
        elif df["td_exhaustion"].iloc[i]:
            ex_type = "EXHAUSTION BUY" if df["td_buy_setup"].iloc[i-1] > 0 else "EXHAUSTION SELL"
            signals.append({
                "ticker"   : ticker,
                "name"    : name,
                "date"    : date.strftime("%Y-%m-%d"),
                "type"    : ex_type,
                "price"   : round(float(close[i]), 2),
                "strength": "WEAK",
            })

    return signals

# ──────────────────────────────────────────────
#  SCAN: Scan multi-actifs
# ──────────────────────────────────────────────
def scan_universe(
    categories=None,
    tickers=None,
    interval=DEFAULT_INTERVAL,
    lookback=60,
):
    """
    Scanne l'univers ou une liste de tickers personnalisés.
    Retourne un DataFrame de signaux consolidés.
    """
    rows = []

    # Construire la liste des tickers à scanner
    if tickers:
        targets = {t: t for t in tickers}
    elif categories:
        targets = {}
        for cat in categories:
            if cat in UNIVERSE:
                targets.update(UNIVERSE[cat])
    else:
        targets = {}
        for cat in UNIVERSE.values():
            targets.update(cat)

    print(f"\n🔍  Scan en cours... ({len(targets)} tickers)")
    print(f"   Intervalle: {interval}  |  Lookback: {lookback} barres\n")

    for ticker, name in targets.items():
        period_map = {"1d": "3mo", "1wk": "6mo", "1mo": "2y"}
        period = period_map.get(interval, "3mo")

        df = fetch_data(ticker, period=period, interval=interval)
        if df.empty:
            print(f"   ⚠  {ticker}: données non disponibles")
            continue

        # Garder uniquement les dernières `lookback` barres
        if len(df) > lookback:
            df = df.tail(lookback)

        df_td = compute_td_sequential(df)
        sigs  = extract_signals(df_td, ticker, name)

        if sigs:
            print(f"   ✅ {ticker:6s} → {len(sigs)} signal(aux)")
        else:
            print(f"   —  {ticker:6s} → aucun signal")

        rows.extend(sigs)

    if not rows:
        print("\n⚠  Aucun signal trouvé sur cet univers.")
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result = result.sort_values(["type", "ticker"])
    return result

# ──────────────────────────────────────────────
#  CLI principale
# ──────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="TD Sequential Scanner – Multi-Asset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
          Exemples:
            python td_sequential_app.py                         # dashboard web
            python td_sequential_app.py --report                 # rapport HTML
            python td_sequential_app.py --symbols AAPL,MSFT,GC=F  # tickers précis
            python td_sequential_app.py --categories "Actions US","ETF"
            python td_sequential_app.py --export signals.csv
            python td_sequential_app.py --interval 1wk            # weekly
        """)
    )
    parser.add_argument("--report",   action="store_true", help="Génère un rapport HTML")
    parser.add_argument("--symbols", type=str, help="Ticker séparés par virgules")
    parser.add_argument("--categories", type=str, help="Catégories séparées par virgules")
    parser.add_argument("--interval",  type=str, default="1d", choices=["1d","1wk","1mo"])
    parser.add_argument("--lookback",  type=int, default=60)
    parser.add_argument("--export",    type=str, help="Export CSV des signaux")
    args = parser.parse_args()

    # ── Traitement ──────────────────────────────────────────────────
    tickers  = [t.strip() for t in args.symbols.split(",")] if args.symbols else None
    cats     = [c.strip() for c in args.categories.split(",")] if args.categories else None

    df_signals = scan_universe(
        categories=cats,
        tickers=tickers,
        interval=args.interval,
        lookback=args.lookback,
    )

    if df_signals.empty:
        print("\nFin du scan. Aucun signal détecté.")
        sys.exit(0)

    # ── Affichage console ────────────────────────────────────────────
    print("\n" + "═"*70)
    print(f"  RÉSULTATS TD SEQUENTIAL – {len(df_signals)} signal(aux) trouvé(s)")
    print("═"*70)

    for _, row in df_signals.iterrows():
        badge = {
            "STRONG": "🟢",
            "MEDIUM": "🟡",
            "WEAK"  : "🔴",
        }.get(row["strength"], "⚪")

        print(f"  {badge} [{row['type']:20s}] {row['ticker']:6s} {row['name']:<30s} "
              f"${row['price']:>8}  le {row['date']}")

    print("═"*70)

    # ── Export CSV ───────────────────────────────────────────────────
    if args.export:
        out = Path(args.export)
        out.parent.mkdir(parents=True, exist_ok=True)
        df_signals.to_csv(out, index=False)
        print(f"\n📁  Export CSV → {out.absolute()}")

    # ── Rapport HTML ────────────────────────────────────────────────
    if args.report:
        generate_html_report(df_signals)

    return df_signals

# ──────────────────────────────────────────────
#  RAPPORT HTML
# ──────────────────────────────────────────────
def generate_html_report(df: pd.DataFrame, output_dir=None):
    """Génère un rapport HTML complet."""
    if output_dir is None:
        output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = output_dir / f"td_sequential_report_{timestamp}.html"

    # ── construire les statistiques ────────────────────────────────
    type_counts = df["type"].value_counts().to_dict()
    strength_counts = df["strength"].value_counts().to_dict()

    buy_signals  = df[df["type"].str.contains("BUY", na=False)]
    sell_signals = df[df["type"].str.contains("SELL", na=False)]

    rows_html = ""
    for _, r in df.iterrows():
        badge = {
            "STRONG": '<span class="badge strong">STRONG</span>',
            "MEDIUM": '<span class="badge medium">MEDIUM</span>',
            "WEAK"  : '<span class="badge weak">WEAK</span>',
        }.get(r["strength"], "")

        type_cls = "buy-type" if "BUY" in r["type"] else "sell-type"
        rows_html += f"""
        <tr class="{type_cls}">
          <td><strong>{r["ticker"]}</strong></td>
          <td>{r["name"]}</td>
          <td class="signal-type">{r["type"]}</td>
          <td>{badge}</td>
          <td class="price">${r["price"]:.2f}</td>
          <td>{r["date"]}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TD Sequential Report – {timestamp}</title>
<style>
  :root {{ --bg:#0d1117; --surface:#161b22; --border:#30363d;
           --text:#c9d1d9; --muted:#8b949e;
           --buy:#3fb950; --sell:#f85149; --neutral:#d29922;
           --strong:#238636; --medium:#9e6a03; --weak:#8b949e; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          padding:2rem; max-width:1200px; margin:0 auto; }}
  h1 {{ color:#58a6ff; margin-bottom:.25rem; }}
  .subtitle {{ color:var(--muted); font-size:.9rem; margin-bottom:2rem; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:1rem; margin-bottom:2rem; }}
  .stat-card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem; }}
  .stat-card .label {{ color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; }}
  .stat-card .value {{ font-size:1.8rem; font-weight:700; color:var(--text); }}
  .stat-card .value.buy {{ color:var(--buy); }}
  .stat-card .value.sell {{ color:var(--sell); }}
  table {{ width:100%; border-collapse:collapse; background:var(--surface); border-radius:8px; overflow:hidden; }}
  th {{ background:#1f6feb22; color:#58a6ff; padding:.75rem 1rem; text-align:left; font-size:.85rem; text-transform:uppercase; letter-spacing:.04em; }}
  td {{ padding:.65rem 1rem; border-top:1px solid var(--border); font-size:.9rem; }}
  tr:hover td {{ background:#1f6feb11; }}
  .buy-type td {{ border-left:3px solid var(--buy); }}
  .sell-type td {{ border-left:3px solid var(--sell); }}
  .signal-type {{ font-weight:600; font-size:.85rem; }}
  .buy-type .signal-type {{ color:var(--buy); }}
  .sell-type .signal-type {{ color:var(--sell); }}
  .badge {{ display:inline-block; padding:.15rem .5rem; border-radius:4px; font-size:.75rem; font-weight:600; }}
  .badge.strong {{ background:#23863633; color:var(--buy); }}
  .badge.medium  {{ background:#9e6a0333; color:var(--neutral); }}
  .badge.weak    {{ background:#8b949e22; color:var(--muted); }}
  .price {{ font-variant-numeric:tabular-nums; }}
  .footer {{ margin-top:2rem; color:var(--muted); font-size:.75rem; text-align:center; }}
</style>
</head>
<body>
<h1>📊 TD Sequential Report</h1>
<p class="subtitle">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} &nbsp;|&nbsp;
  {len(df)} signal(aux) sur {df['ticker'].nunique()} actif(s)</p>

<div class="stats">
  <div class="stat-card"><div class="label">Total signaux</div><div class="value">{len(df)}</div></div>
  <div class="stat-card"><div class="label">Signaux BUY</div><div class="value buy">{len(buy_signals)}</div></div>
  <div class="stat-card"><div class="label">Signaux SELL</div><div class="value sell">{len(sell_signals)}</div></div>
  <div class="stat-card"><div class="label">Actifs uniques</div><div class="value">{df['ticker'].nunique()}</div></div>
  <div class="stat-card"><div class="label">Count 13 (forts)</div><div class="value">{df[df['type'].str.contains('13',na=False)].shape[0]}</div></div>
  <div class="stat-card"><div class="label">Setup 9 (moyens)</div><div class="value">{df[df['type'].str.contains('Setup',na=False)].shape[0]}</div></div>
</div>

<table>
<thead>
<tr>
  <th>Ticker</th><th>Nom</th><th>Signal</th><th>Force</th><th>Prix</th><th>Date</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>

<div class="footer">
  TD Sequential – Méthode DeMark | Données Yahoo Finance via yfinance | {timestamp}
</div>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n📄  Rapport HTML généré → {filepath.absolute()}")
    return filepath

# ──────────────────────────────────────────────
#  DASHBOARD WEB (Flask minimal)
# ──────────────────────────────────────────────
def run_dashboard(port: int = 5005):
    try:
        from flask import Flask, render_template_string, request, jsonify
    except ImportError:
        print("⚠  Flask non installé. Utilise: pip install flask")
        print("   Ou génère le rapport HTML avec: python td_sequential_app.py --report")
        sys.exit(1)

    app = Flask(__name__)

    DASHBOARD_HTML = """
    <!doctype html>
    <html lang="fr">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>TD Sequential Dashboard</title>
    <style>
      :root{--bg:#0d1117;--s:#161b22;--b:#30363d;--t:#c9d1d9;--m:#8b949e;
            --buy:#3fb950;--sell:#f85149;--acc:#58a6ff;}
      *{box-sizing:border-box;margin:0;padding:0}
      body{background:var(--bg);color:var(--t);font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:1.5rem;max-width:1200px;margin:0 auto}
      h1{color:var(--acc);font-size:1.6rem;margin-bottom:.3rem}
      .subtitle{color:var(--m);font-size:.85rem;margin-bottom:1.5rem}
      .controls{background:var(--s);border:1px solid var(--b);border-radius:8px;padding:1rem;margin-bottom:1.5rem;display:flex;flex-wrap:wrap;gap:.75rem;align-items:center}
      label{color:var(--m);font-size:.8rem}
      select,input,button{background:#0d1117;border:1px solid var(--b);color:var(--t);border-radius:5px;padding:.45rem .75rem;font-size:.85rem}
      button{background:#1f6feb;color:#fff;border:none;cursor:pointer;font-weight:600;transition:opacity .2s}
      button:hover{opacity:.85}
      .spinner{color:var(--acc);font-size:.9rem}
      .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.75rem;margin-bottom:1.5rem}
      .card{background:var(--s);border:1px solid var(--b);border-radius:6px;padding:.75rem}
      .card .lbl{color:var(--m);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}
      .card .val{font-size:1.5rem;font-weight:700;margin-top:.2rem}
      .card .val.buy{color:var(--buy)}.card .val.sell{color:var(--sell)}
      table{width:100%;border-collapse:collapse;background:var(--s);border-radius:8px;overflow:hidden;margin-bottom:1rem}
      th{background:#1f6feb22;color:var(--acc);padding:.6rem .8rem;text-align:left;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
      td{padding:.55rem .8rem;border-top:1px solid var(--b);font-size:.85rem}
      tr:hover td{background:#1f6feb11}
      .buy-row td{border-left:3px solid var(--buy)}
      .sell-row td{border-left:3px solid var(--sell)}
      .buy-row .sig{color:var(--buy);font-weight:600}
      .sell-row .sig{color:var(--sell);font-weight:600}
      .str{font-size:.72rem;padding:.1rem .4rem;border-radius:3px;font-weight:600}
      .str-s{background:#23863633;color:var(--buy)}
      .str-m{background:#9e6a0333;color:#d29922}
      .str-w{background:#8b949e22;color:var(--m)}
      .price{font-variant-numeric:tabular-nums}
      .msg{color:var(--m);padding:2rem;text-align:center;font-size:.9rem}
    </style>
    </head>
    <body>
    <h1>📊 TD Sequential Dashboard</h1>
    <p class="subtitle">Signaux DeMark 9 &amp; 13 – Actions, ETF, Taux, Commodities</p>

    <div class="controls">
      <label>Catégorie</label>
      <select id="cat">
        <option value="">Toutes</option>
        <option value="Actions US">Actions US</option>
        <option value="ETF">ETF</option>
        <option value="Taux d'intérêt">Taux d'intérêt</option>
        <option value="Commodities">Commodities</option>
      </select>
      <label>Intervalle</label>
      <select id="interval">
        <option value="1d">Daily</option>
        <option value="1wk">Weekly</option>
        <option value="1mo">Monthly</option>
      </select>
      <label>Lookback</label>
      <input type="number" id="lookback" value="60" min="20" max="300" style="width:70px">
      <button onclick="runScan()">🔍 Lancer le scan</button>
    </div>

    <div class="stats" id="stats"></div>
    <div id="msg" class="msg">Appuie sur « Lancer le scan » pour démarrer…</div>
    <table id="tbl" style="display:none">
    <thead><tr><th>Ticker</th><th>Nom</th><th>Signal</th><th>Force</th><th>Prix</th><th>Date</th></tr></thead>
    <tbody id="tbody"></tbody>
    </table>

    <script>
    async function runScan() {
      const cat = document.getElementById('cat').value;
      const interval = document.getElementById('interval').value;
      const lookback = parseInt(document.getElementById('lookback').value) || 60;

      document.getElementById('msg').textContent = '⏳ Scan en cours…';
      document.getElementById('tbl').style.display = 'none';

      const body = { interval, lookback };
      if (cat) body.categories = [cat];

      const resp = await fetch('/scan', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      const data = await resp.json();

      if (!data.signals || data.signals.length === 0) {
        document.getElementById('msg').textContent = '⚠ Aucun signal trouvé.';
        document.getElementById('stats').innerHTML = '';
        return;
      }

      const buyCount = data.signals.filter(s=>s.type.includes('BUY')).length;
      const sellCount= data.signals.filter(s=>s.type.includes('SELL')).length;
      const strongCount = data.signals.filter(s=>s.strength==='STRONG').length;

      document.getElementById('stats').innerHTML =
        `<div class="card"><div class="lbl">Total</div><div class="val">${data.signals.length}</div></div>
         <div class="card"><div class="lbl">BUY</div><div class="val buy">${buyCount}</div></div>
         <div class="card"><div class="lbl">SELL</div><div class="val sell">${sellCount}</div></div>
         <div class="card"><div class="lbl">Count 13</div><div class="val">${strongCount}</div></div>
         <div class="card"><div class="lbl">Actifs</div><div class="val">${data.unique_tickers}</div></div>`;

      const tbody = document.getElementById('tbody');
      tbody.innerHTML = data.signals.map(s => {
        const rowClass = s.type.includes('BUY') ? 'buy-row' : 'sell-row';
        const strClass = s.strength==='STRONG'?'str-s':s.strength==='MEDIUM'?'str-m':'str-w';
        return `<tr class="${rowClass}">
          <td><strong>${s.ticker}</strong></td><td>${s.name||''}</td>
          <td class="sig">${s.type}</td>
          <td><span class="str ${strClass}">${s.strength}</span></td>
          <td class="price">$${parseFloat(s.price).toFixed(2)}</td>
          <td>${s.date}</td>
        </tr>`;
      }).join('');

      document.getElementById('msg').textContent = `${data.signals.length} signal(aux) trouvé(s)`;
      document.getElementById('tbl').style.display = '';
    }
    </script>
    </body>
    </html>"""

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/scan", methods=["POST"])
    def scan():
        req = request.json or {}
        cats  = req.get("categories")
        tickers = req.get("tickers")
        interval = req.get("interval", "1d")
        lookback = int(req.get("lookback", 60))

        df = scan_universe(
            categories=cats,
            tickers=tickers,
            interval=interval,
            lookback=lookback,
        )

        if df.empty:
            return jsonify({"signals": [], "unique_tickers": 0})

        signals = df.to_dict(orient="records")
        return jsonify({
            "signals": signals,
            "unique_tickers": df["ticker"].nunique(),
        })

    print(f"\n🌐  Dashboard → http://localhost:{port}")
    print(f"   Ctrl+C pour arrêter\n")
    app.run(host="0.0.0.0", port=port, debug=False)

# ──────────────────────────────────────────────
#  POINT D'ENTRÉE
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--port", type=int, default=5005)
    args, remaining = parser.parse_known_args()

    if args.dashboard:
        run_dashboard(port=args.port)
    elif len(sys.argv) == 1:
        run_dashboard(port=args.port)
    else:
        sys.argv = [sys.argv[0]] + remaining
        main()