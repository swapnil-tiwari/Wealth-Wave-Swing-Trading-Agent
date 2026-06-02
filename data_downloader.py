import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# ========= CONFIG =========
SYMBOL_FILE = "fno_symbols.csv"
OUTPUT_FOLDER = "data"
START_DATE = "2023-01-01"
END_DATE = None   # None = today
# ==========================


# Create output folder if not exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Read symbols file
df = pd.read_csv(SYMBOL_FILE)

# Assuming csv contains a column named Symbol
# Change column name if required
symbols = df["Symbol"].dropna().unique().tolist()

print(f"Total symbols found: {len(symbols)}")

for symbol in tqdm(symbols):

    try:
        # Yahoo uses NSE suffix
        yahoo_symbol = f"{symbol}.NS"

        print(f"\nDownloading: {yahoo_symbol}")

        data = yf.download(
            yahoo_symbol,
            start=START_DATE,
            end=END_DATE,
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if data.empty:
            print(f"No data found for {symbol}")
            continue

        # Reset index so Date becomes column
        data.reset_index(inplace=True)

        # Optional cleanup
        data.columns = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
            "Volume"
        ]

        # Save file
        output_file = os.path.join(
            OUTPUT_FOLDER,
            f"{symbol}.csv"
        )

        data.to_csv(output_file, index=False)

        print(f"Saved -> {output_file}")

    except Exception as e:
        print(f"Error in {symbol}: {e}")

print("\nDownload completed.")