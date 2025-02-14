from data_processing import *
from index_calculation import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


data = load_data("../IndexManagerTest 1.xlsb", "xlsb")
tables = preprocess_data(data)
index_calculator = IndexCalculator(tables)


for row in tables['stock_prices'].itertuples():
    date = row.Date
    price = index_calculator.calculate_index(date)
    date_as_string = pd.to_datetime(date, unit='D', origin='1899-12-30').strftime('%Y-%m-%d')
    logger.info(f"Index level on {date_as_string}: {price}")