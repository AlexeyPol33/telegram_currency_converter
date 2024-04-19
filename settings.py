import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv('BACKEND_HOST',default='0.0.0.0')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

DB_NAME=os.getenv('DB_NAME',default='currency_converter')
DB_LOGIN=os.getenv('DB_LOGIN',default='postgres')
DB_PASSWORD=os.getenv('DB_PASSWORD',default='postgres')
DB_HOST=os.getenv('DB_HOST',default='localhost')

COLLECT_HISTORICAL_DATA = os.getenv('COLLECT_HISTORICAL_DATA', default=False)