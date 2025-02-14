import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import logging
import io
import os

from modules.data_processing import load_data, preprocess_data
from modules.index_calculation import IndexCalculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit App Title
st.title("📈 Index Calculation Dashboard")

# Sidebar for Historical Data Selection
st.sidebar.header("📅 View Historical Data")

# Load historical index data (if available)
HISTORICAL_DATA_FILE = "historical_index_results.csv"

if os.path.exists(HISTORICAL_DATA_FILE):
    df_historical = pd.read_csv(HISTORICAL_DATA_FILE, parse_dates=["Date"])
    st.sidebar.success("✅ Historical data loaded from previous calculations.")
else:
    df_historical = None

# File Uploader for New Data
uploaded_file = st.file_uploader("Upload your data file (Excel, CSV, or XLSB)", type=["xlsb", "xlsx", "csv"])

if uploaded_file is not None:
    try:
        # Determine file type and process data
        file_type = "xlsb" if uploaded_file.name.endswith(".xlsb") else "xlsx" if uploaded_file.name.endswith(".xlsx") else "csv"
        data = load_data(uploaded_file, file_type)
        tables = preprocess_data(data)

        # Initialize Index Calculator
        index_calculator = IndexCalculator(tables)

        # Calculate index levels dynamically
        index_results = []
        for row in tables['stock_prices'].itertuples():
            date = row.Date
            index_level = index_calculator.calculate_index(date)
            date_as_string = pd.to_datetime(date, unit='D', origin='1899-12-30').strftime('%Y-%m-%d')
            index_results.append((date_as_string, index_level))
            logger.info(f"Index level on {date_as_string}: {index_level}")
            if len(index_results) >= 50:
                break

        # Convert to DataFrame
        df_index = pd.DataFrame(index_results, columns=["Date", "Index Level"])
        df_index["Date"] = pd.to_datetime(df_index["Date"])  # Ensure Date is in datetime format

        # Save to CSV for future use
        df_index.to_csv(HISTORICAL_DATA_FILE, index=False)

        # Display results
        st.success("✅ Index calculation completed successfully!")

        # Show preview of processed data
        st.write("### 📄 Processed Data Preview")
        st.dataframe(df_index)

    except Exception as e:
        st.error(f"⚠ Error processing the file: {e}")

# Show Historical Data If Available
if df_historical is not None:
    st.write("### ⏳ View Historical Index Data")
    
    # Date Range Selector
    min_date, max_date = df_historical["Date"].min(), df_historical["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    # Filter data based on selected range
    df_filtered = df_historical[(df_historical["Date"] >= pd.to_datetime(start_date)) &
                                (df_historical["Date"] <= pd.to_datetime(end_date))]

    # Show Data Table
    st.dataframe(df_filtered)

    # Plot Historical Data
    st.write("### 📊 Historical Index Level Over Time")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_filtered["Date"], df_filtered["Index Level"], marker='o', linestyle='-', color='blue')
    ax.set_title("Historical Index Level")
    ax.set_xlabel("Date")
    ax.set_ylabel("Index Level")
    ax.grid(True)
    st.pyplot(fig)

    # Search for a Specific Date
    search_date = st.sidebar.date_input("Search for a Specific Date")
    df_search = df_historical[df_historical["Date"] == pd.to_datetime(search_date)]
    if not df_search.empty:
        st.write("### 🔍 Search Result")
        st.dataframe(df_search)
    else:
        st.sidebar.warning("❌ No index data available for the selected date.")

    # Download Historical Data
    st.write("### 📥 Download Historical Index Data")
    csv_buffer = io.StringIO()
    df_historical.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Download Historical Index Data as CSV",
        data=csv_buffer.getvalue(),
        file_name="historical_index_results.csv",
        mime="text/csv"
    )
