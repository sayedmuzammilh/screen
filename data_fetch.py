import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

def get_nasdaq_tickers():
    url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
    df = pd.read_csv(url)
    return df["Symbol"].dropna().unique().tolist()

def fetch_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            "Ticker": ticker,
            "RevenueGrowth": info.get("revenueGrowth", 0) * 100,
            "EarningsGrowth": info.get("earningsGrowth", 0) * 100,
            "DebtEquity": info.get("debtToEquity", 999)
        }
    except:
        return None

def fetch_prices(ticker, days=10):
    try:
        df = yf.download(ticker, period=f"{days+5}d", interval="1d", progress=False)
        df = df.tail(days)
        df["Ticker"] = ticker
        return df[["Ticker", "Close"]]
    except:
        return None

if __name__ == "__main__":
    tickers = get_nasdaq_tickers()
    fundamentals = []
    prices = []

    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Processing {ticker}")
        f = fetch_fundamentals(ticker)
        p = fetch_prices(ticker)
        if f: fundamentals.append(f)
        if p is not None and not p.empty: prices.append(p)

    df_fund = pd.DataFrame(fundamentals)
    df_prices = pd.concat(prices)

    os.makedirs("cache", exist_ok=True)
    df_fund.to_parquet("cache/fundamentals.parquet", index=False)
    df_prices.to_parquet("cache/price_data.parquet", index=False)
    print("✅ Data cached in 'cache/' folder.")
