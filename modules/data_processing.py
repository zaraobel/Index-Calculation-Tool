import pandas as pd
import logging
logger = logging.getLogger(__name__)


def load_data(file_buffer, file_type=None):
    """
    Load data from an uploaded file.
    
    Parameters:
        file_buffer: File-like object from Streamlit file uploader.
        file_type (str): Optional; 'xlsx', 'xlsb', or 'csv'. 
    
    Returns:
        If Excel type: dict of DataFrames (one per sheet).
        If CSV: a single DataFrame.
    
    Raises:
        Exception: if the file cannot be read.
    """
    try:
        # Determine file type from the file name if not explicitly provided
        if not file_type:
            filename = getattr(file_buffer, 'name', '')
            if filename.endswith('.xlsb'):
                file_type = 'xlsb'
            elif filename.endswith('.xlsx'):
                file_type = 'xlsx'
            elif filename.endswith('.csv'):
                file_type = 'csv'
            else:
                raise ValueError("Unsupported file format")
        
        logger.debug("Loading %s file...", file_type)

        if file_type in ['xlsx', 'xlsb']:
            engine = 'pyxlsb' if file_type == 'xlsb' else None
            # Read all sheets into a dictionary
            data = pd.read_excel(file_buffer, sheet_name=None, engine=engine)
            logger.info("%s file loaded successfully with sheets: %s", file_type, list(data.keys()))
        else:
            data = pd.read_csv(file_buffer)
            logger.info("CSV file loaded successfully.")
        return data
    except Exception as e:
        logger.error("Error loading data: %s", e)
        raise e

def preprocess_data(data_dict):
    """
    Load and preprocess the data from a single-sheet Excel file containing Stock Prices, FX, Weights, and Currency.

    Expected format:
      - Stock Price: "Date" + Indices (e.g., ABC, DEF, GHI, etc.)
      - FX: Conversion rates for that date (but no date included in the table row) (e.g., EURUSD, GBPUSD)
      - Weights: "Date" + Indices (same as Stock Prices)
      - Currency: Two columns without a header row - Index and Currency

    Returns:
        A dictionary containing the preprocessed tables.

    Raises:
        ValueError: if the file does not contain enough tables for processing.
    """
    # first extract the sheet "Stock Data" which contains all the tables
    if "Stock Data" not in data_dict:
        logger.error("Sheet 'Stock Data' not found in the file.")
        raise ValueError("Sheet 'Stock Data' not found in the file.")

    stock_data = data_dict["Stock Data"]

    # remove the column names 
    stock_data.columns = range(stock_data.shape[1])

    # each table is separated by a column of NaN values
    nan_cols = stock_data.isnull().all()
    table_indices = [-1]
    table_indices.extend(stock_data.columns[nan_cols].tolist())
    table_indices = table_indices[:5]

    logger.debug("Table indices: %s", table_indices)

    # extract the tables
    tables = []
    for i in range(0, len(table_indices) - 1):
        tables.append(stock_data.iloc[:, table_indices[i]+1:table_indices[i + 1]])
        # remove rows with all NaN values
        tables[i] = tables[i].dropna(how="all")
        if i != 3:
            #make the first row the column names
            tables[i].columns = tables[i].iloc[0]
            # remove the first row
            tables[i] = tables[i][1:]


    # add a date column to the second table with the values from the first table
    tables[1].insert(0, "Date", tables[0].iloc[:, 0])

    # check if there are enough tables for processing
    if len(tables) < 4:
        logger.error("Not enough tables found in the file.")
        raise ValueError("Not enough tables found in the file.")

    logger.info("Data preprocessed successfully.")

    return {
        'stock_prices': tables[0],
        'fx_rates': tables[1],
        'weights': tables[2],
        'currency': tables[3]
    }


