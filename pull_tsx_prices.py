"""Pull 3 years of daily closes, earnings history and current financials for the stock list.

Run on any computer with internet:
    pip install yfinance pandas
    python pull_tsx_prices.py

Writes tsx100_closes.csv, earnings.csv and financials.csv next to this script.
"""
import pandas as pd
import yfinance as yf

STOCKS = """RY.TO SHOP.TO TD.TO BMO.TO BNS.TO CNQ.TO ENB.TO CM.TO AEM.TO SU.TO
BN.TO CP.TO BAM.TO CNR.TO MFC.TO ABX.TO TRP.TO IMO.TO WPM.TO CVE.TO
GWO.TO NA.TO L.TO ATD.TO FNV.TO CSU.TO TRI.TO CLS.TO SLF.TO POW.TO
BBD-B.TO CCO.TO DOL.TO FFH.TO NTR.TO TECK-B.TO QSR.TO IFC.TO PPL.TO K.TO
FTS.TO WN.TO FM.TO H.TO LUN.TO PAAS.TO BCE.TO TOU.TO MG.TO RCI-B.TO
WCP.TO RBA.TO LUG.TO WSP.TO GFL.TO GIB-A.TO EMA.TO TOI.V MRU.TO
AGI.TO IGM.TO IAG.TO EQX.TO T.TO ALA.TO TIH.TO ATZ.TO CCL-B.TO HBM.TO
KEY.TO IVN.TO CGG.TO SAP.TO IMG.TO X.TO HUT.TO QBR-B.TO GMIN.TO ATRL.TO
FTT.TO ELD.TO TFII.TO CU.TO DPM.TO AG.TO GIL.TO CTC-A.TO EMP-A.TO STN.TO
CAE.TO CHP-UN.TO DSG.TO CS.TO CPX.TO SOBO.TO DSV.TO BTO.TO SSRM.TO""".split()

# Market and macro drivers: TSX index, S&P 500, oil, gold, copper, nat gas, USD/CAD, US 10y yield, VIX
FACTORS = ["^GSPTSE", "^GSPC", "CL=F", "GC=F", "HG=F", "NG=F", "CAD=X", "^TNX", "^VIX"]

data = yf.download(STOCKS + FACTORS, period="3y", interval="1d",
                   auto_adjust=True, progress=True, threads=True)
closes = data["Close"].sort_index()
closes.index = pd.to_datetime(closes.index).date
closes.to_csv("tsx100_closes.csv", index_label="date")

missing = [t for t in STOCKS + FACTORS if t not in closes or closes[t].dropna().empty]
print(f"Saved {closes.shape[0]} days x {closes.shape[1]} series to tsx100_closes.csv")
if missing:
    print("No data for:", ", ".join(missing))

# Earnings history (reported vs expected EPS) and current financials
FIELDS = ["financialCurrency", "trailingPE", "forwardPE", "priceToBook", "returnOnEquity",
          "debtToEquity", "revenueGrowth", "earningsGrowth", "profitMargins", "dividendYield"]
earn, fin = [], []
for t in STOCKS:
    tk = yf.Ticker(t)
    try:
        ed = tk.get_earnings_dates(limit=12)
        if ed is not None and not ed.empty:
            ed = ed.reset_index().iloc[:, :4]
            ed.columns = ["datetime", "eps_estimate", "eps_reported", "surprise_pct"]
            ed["ticker"] = t
            earn.append(ed)
    except Exception as exc:
        print("earnings failed", t, exc)
    try:
        info = tk.info
        fin.append({"ticker": t, **{f: info.get(f) for f in FIELDS}})
    except Exception as exc:
        print("info failed", t, exc)
pd.concat(earn).to_csv("earnings.csv", index=False)
pd.DataFrame(fin).to_csv("financials.csv", index=False)
print(f"Earnings for {len(earn)} stocks, financials for {len(fin)}")
