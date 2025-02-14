import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import logging
import io
import os
import time

from modules.data_processing import load_data, preprocess_data
from modules.index_calculation import IndexCalculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit App Title
st.title("📈 Index Calculation Dashboard")

# Define a directory to store CSV files
CSV_DIR = "csv_results"
if not os.path.exists(CSV_DIR):
    os.makedirs(CSV_DIR)

# Initialize session state for processed data
if "df_index" not in st.session_state:
    st.session_state.df_index = None

# Sidebar for Historical Data Selection
st.sidebar.header("📅 View Historical Data")

# List available CSV files in CSV_DIR
csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith(".csv")]
if csv_files:
    selected_csv_file = st.sidebar.selectbox("Select a CSV file for historical data", csv_files)
    historical_file_path = os.path.join(CSV_DIR, selected_csv_file)
    try:
        df_historical = pd.read_csv(historical_file_path, parse_dates=["Date"])
        st.sidebar.success(f"✅ Historical data loaded from {selected_csv_file}")
    except Exception as e:
        st.sidebar.error(f"Error loading {selected_csv_file}: {e}")
        df_historical = None
else:
    df_historical = None
    st.sidebar.info("No historical CSV files available.")

# File Uploader for New Data
uploaded_file = st.file_uploader("Upload your data file (Excel, CSV, or XLSB)", type=["xlsb", "xlsx", "csv"])

if uploaded_file is not None:
    # Let the user provide a file name before processing
    result_filename = st.text_input(
        "Enter a file name to save the results (without extension)",
        value="historical_index_results"
    )
    
    # Button to start processing; processing will only start after file name is provided
    if st.button("Start Processing"):
        if not result_filename:
            st.warning("Please enter a file name to save the results.")
        else:
            try:
                # Determine file type and process data
                file_type = (
                    "xlsb" if uploaded_file.name.endswith(".xlsb")
                    else "xlsx" if uploaded_file.name.endswith(".xlsx")
                    else "csv"
                )
                data = load_data(uploaded_file, file_type)
                tables = preprocess_data(data)

                # Initialize Index Calculator
                index_calculator = IndexCalculator(tables)
                index_results = []
                
                # Create a placeholder for live chart updates
                chart_placeholder = st.empty()

                # Process the file with a spinner and live chart updates
                with st.spinner("Processing your file..."):
                    for row in tables['stock_prices'].itertuples():
                        date = row.Date
                        index_level = index_calculator.calculate_index(date)
                        # Adjust for Excel dates and convert to a string date
                        date_as_string = pd.to_datetime(date, unit='D', origin='1899-12-30').strftime('%Y-%m-%d')
                        index_results.append((date_as_string, index_level))
                        logger.info(f"Index level on {date_as_string}: {index_level}")

                        # Build a DataFrame with current results
                        df_live = pd.DataFrame(index_results, columns=["Date", "Index Level"])
                        df_live["Date"] = pd.to_datetime(df_live["Date"])

                        # Create a live plot
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.plot(df_live["Date"], df_live["Index Level"], marker='o', linestyle='-', color='blue')
                        ax.set_title("Live Index Level")
                        ax.set_xlabel("Date")
                        ax.set_ylabel("Index Level")
                        ax.grid(True)

                        # Update the chart placeholder with the new plot
                        chart_placeholder.pyplot(fig)

                        # Small delay for UI update visibility
                        time.sleep(0.1)

                        # Limit iterations for demonstration purposes (adjust as needed)
                        if len(index_results) >= 50:
                            break

                # Convert the complete results into a DataFrame
                df_index = pd.DataFrame(index_results, columns=["Date", "Index Level"])
                df_index["Date"] = pd.to_datetime(df_index["Date"])  # Ensure Date is in datetime format

                # Store the processed data in session state
                st.session_state.df_index = df_index

                # Display a preview of the processed data
                st.write("### 📄 Processed Data Preview")
                st.dataframe(df_index)

            except Exception as e:
                logger.error(f"Error processing the file: {e}")
                st.error(f"⚠ Error processing the file: {e}")

    # Button to save results if processing has been completed
    if st.session_state.df_index is not None:
        if st.button("Save Results"):
            save_path = os.path.join(CSV_DIR, f"{result_filename}.csv")
            st.session_state.df_index.to_csv(save_path, index=False)
            st.success(f"✅ Index calculation completed successfully! Results saved to {save_path}")

# Show Historical Data If Available
if df_historical is not None:
    st.write("### ⏳ View Historical Index Data")
    
    # Date Range Selector
    min_date, max_date = df_historical["Date"].min(), df_historical["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    # Filter data based on selected range
    df_filtered = df_historical[
        (df_historical["Date"] >= pd.to_datetime(start_date)) &
        (df_historical["Date"] <= pd.to_datetime(end_date))
    ]

    # Display the data table
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

# Download Historical Data Section
st.write("### 📥 Download Historical Index Data")
if csv_files:
    download_selected_file = st.selectbox("Select a CSV file to download", csv_files, key="download")
    download_file_path = os.path.join(CSV_DIR, download_selected_file)
    try:
        with open(download_file_path, "r") as f:
            csv_data = f.read()
        st.download_button(
            label="📥 Download Selected Historical Index Data as CSV",
            data=csv_data,
            file_name=download_selected_file,
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error reading file for download: {e}")
else:
    st.info("No CSV files available for download.")
