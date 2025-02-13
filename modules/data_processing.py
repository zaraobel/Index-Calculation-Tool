# modules/data_processing.py

import pandas as pd
import logging

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

        if file_type in ['xlsx', 'xlsb']:
            engine = 'pyxlsb' if file_type == 'xlsb' else None
            # Read all sheets into a dictionary
            data = pd.read_excel(file_buffer, sheet_name=None, engine=engine)
            logging.info("%s file loaded successfully with sheets: %s", file_type, list(data.keys()))
        else:
            data = pd.read_csv(file_buffer)
            logging.info("CSV file loaded successfully.")
        return data
    except Exception as e:
        logging.error("Error loading data: %s", e)
        raise e

def preprocess_data(data_dict):
    """
    Preprocess the data from the Excel file.
    
    Expected keys in data_dict:
        - 'Stock Prices'
        - 'FX'
        - 'Weights'
        - 'Currency'
    
    This function checks for the existence of the required sheets and logs warnings
    if any critical data is missing.
    
    Parameters:
        data_dict (dict): Dictionary of DataFrames from load_data.
    
    Returns:
        Tuple of DataFrames: (df_stock, df_fx, df_weights, df_currency)
    
    Raises:
        ValueError: if a required sheet is missing.
    """
    required_sheets = ['Stock Prices', 'FX', 'Weights', 'Currency']
    for sheet in required_sheets:
        if sheet not in data_dict:
            error_msg = f"Missing required sheet: {sheet}"
            logging.error(error_msg)
            raise ValueError(error_msg)
    
    # Extract individual DataFrames
    df_stock = data_dict['Stock Prices']
    df_fx = data_dict['FX']
    df_weights = data_dict['Weights']
    df_currency = data_dict['Currency']

    # Basic validation: log warnings if missing values are detected
    if df_stock.isnull().values.any():
        logging.warning("Missing values found in Stock Prices data.")
    if df_fx.isnull().values.any():
        logging.warning("Missing values found in FX data.")
    if df_weights.isnull().values.any():
        logging.warning("Missing values found in Weights data.")
    if df_currency.isnull().values.any():
        logging.warning("Missing values found in Currency data.")

    logging.info("Data preprocessing complete.")
    return df_stock, df_fx, df_weights, df_currency