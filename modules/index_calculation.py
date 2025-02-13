# modules/index_calculation.py

import pandas as pd
import numpy as np
import logging

def compute_no_of_shares(df_stock, df_weights):
    """
    Computes the number of shares for each asset on rebalance dates based on:
    
      NoOfShares(t_r) = Weight(t_r) / Price(t_r - 1)
    
    Assumes:
      - df_weights has a 'Date' column and columns for each asset with weights as percentages.
      - df_stock has a 'Date' column and asset price columns.
    
    Returns:
      A DataFrame with the same index as df_stock['Date'] and columns for each asset,
      with computed number of shares that remain constant between rebalance dates.
    """
    # Convert weight percentages to decimals
    df_weights_copy = df_weights.copy()
    asset_cols = [col for col in df_weights_copy.columns if col != "Date"]
    for col in asset_cols:
        # Remove '%' if present, then convert to float and divide by 100
        df_weights_copy[col] = df_weights_copy[col].astype(str).str.replace('%', '').astype(float) / 100

    # Ensure both dataframes are sorted by date
    df_stock = df_stock.sort_values("Date").reset_index(drop=True)
    df_weights_copy = df_weights_copy.sort_values("Date").reset_index(drop=True)

    # Create an empty DataFrame for number of shares, indexed by dates from df_stock
    no_of_shares = pd.DataFrame(index=df_stock["Date"], columns=asset_cols, dtype=float)

    # List of rebalance dates from weights
    weights_dates = df_weights_copy["Date"].tolist()

    for i, rb_date in enumerate(weights_dates):
        # Get the last available stock price before the rebalance date
        prev_prices_df = df_stock[df_stock["Date"] < rb_date]
        if prev_prices_df.empty:
            logging.warning("No stock data available before rebalance date %s", rb_date)
            continue
        last_date = prev_prices_df.iloc[-1]["Date"]
        last_prices = prev_prices_df[prev_prices_df["Date"] == last_date].iloc[0]

        # Get the weights for the rebalance date
        row_weights = df_weights_copy[df_weights_copy["Date"] == rb_date].iloc[0]

        # Compute number of shares for each asset
        for asset in asset_cols:
            price = last_prices[asset]
            if price == 0:
                logging.error("Zero price for asset %s on %s", asset, last_date)
                shares = np.nan
            else:
                shares = row_weights[asset] / price

            # Determine the period for which these shares are held
            if i < len(weights_dates) - 1:
                next_rb_date = weights_dates[i + 1]
                mask = (df_stock["Date"] >= rb_date) & (df_stock["Date"] < next_rb_date)
            else:
                mask = (df_stock["Date"] >= rb_date)
            no_of_shares.loc[mask, asset] = shares

    logging.info("Computed number of shares for each asset on rebalance dates.")
    return no_of_shares


def merge_fx(df_stock, df_fx, df_currency):
    """
    Merges FX rates with the stock prices.
    
    Parameters:
      - df_stock: DataFrame with stock prices (includes a 'Date' column).
      - df_fx: DataFrame with FX rates (includes a 'Date' column).
      - df_currency: DataFrame mapping asset names to their base currency.
                     Expected columns: asset, currency.
    
    For each asset:
      - If the asset's base currency is USD, FX factor = 1.
      - If the asset is in EUR, use the EURUSD rate.
      - If the asset is in GBP, use the GBPUSD rate.
    
    Returns:
      A DataFrame similar to df_stock but with additional columns (one per asset) for the FX factor.
    """
    # Build mapping: asset -> currency
    currency_map = {}
    for idx, row in df_currency.iterrows():
        asset = row.iloc[0]
        cur = row.iloc[1].strip()
        currency_map[asset] = cur

    df_stock = df_stock.copy()
    df_stock.set_index("Date", inplace=True)
    df_fx = df_fx.copy()
    df_fx.set_index("Date", inplace=True)

    # For each asset, add an FX column
    for asset in currency_map.keys():
        if currency_map[asset] == "USD":
            df_stock[asset + "_FX"] = 1.0
        elif currency_map[asset] == "EUR":
            df_stock[asset + "_FX"] = df_fx["EURUSD"]
        elif currency_map[asset] == "GBP":
            df_stock[asset + "_FX"] = df_fx["GBPUSD"]
        else:
            df_stock[asset + "_FX"] = 1.0

    df_stock.reset_index(inplace=True)
    logging.info("Merged FX data with stock prices.")
    return df_stock


def calculate_index_level(df_stock, no_of_shares):
    """
    Calculates the daily index level using the formula:
    
      For t <= 04-Jan-2017: IndexLevel = 100.
      For t > 04-Jan-2017:
        IndexLevel(t) = IndexLevel(t-1) * (PortfolioValue(t) / PortfolioValue(t-1))
      
      where PortfolioValue(t) = Σ_i [NoOfShares(i,t) * Price(i,t) * FX(i,t)]
    
    Parameters:
      - df_stock: DataFrame with stock prices (and merged FX columns), must include a 'Date' column.
      - no_of_shares: DataFrame with computed number of shares, indexed by date.
    
    Returns:
      df_stock with added columns 'PortfolioValue' and 'IndexLevel'
    """
    df_stock = df_stock.sort_values("Date").reset_index(drop=True)
    df_stock["PortfolioValue"] = np.nan
    df_stock["IndexLevel"] = np.nan

    # Define the cutoff date for the fixed index level
    cutoff_date = pd.to_datetime("04-Jan-2017")
    # Set IndexLevel to 100 for dates on or before cutoff_date
    df_stock.loc[pd.to_datetime(df_stock["Date"]) <= cutoff_date, "IndexLevel"] = 100

    asset_cols = [col for col in no_of_shares.columns if col != "Date"]

    # Calculate portfolio value for each day
    for i, row in df_stock.iterrows():
        current_date = row["Date"]
        # Extract the number of shares for the current date
        shares_row = no_of_shares.loc[no_of_shares.index == current_date]
        if shares_row.empty:
            logging.warning("No share data available for date %s", current_date)
            continue
        shares_row = shares_row.iloc[0]

        port_value = 0.0
        for asset in asset_cols:
            price = row[asset]
            fx_factor = row.get(asset + "_FX", 1)
            port_value += shares_row[asset] * price * fx_factor
        df_stock.at[i, "PortfolioValue"] = port_value

    # Calculate the index level for dates after the cutoff
    for i in range(1, len(df_stock)):
        prev_value = df_stock.at[i - 1, "PortfolioValue"]
        current_value = df_stock.at[i, "PortfolioValue"]

        if pd.isna(prev_value) or prev_value == 0:
            df_stock.at[i, "IndexLevel"] = df_stock.at[i - 1, "IndexLevel"]
            logging.warning("Carrying forward IndexLevel due to missing/zero previous portfolio value at date %s", df_stock.at[i, "Date"])
        else:
            ratio = current_value / prev_value
            # Log extreme movements (e.g., >10% change)
            if abs(ratio - 1) > 0.1:
                logging.warning("Extreme movement on %s: ratio = %.4f", df_stock.at[i, "Date"], ratio)
            df_stock.at[i, "IndexLevel"] = df_stock.at[i - 1, "IndexLevel"] * ratio

    logging.info("Index level calculation complete.")
    return df_stock
