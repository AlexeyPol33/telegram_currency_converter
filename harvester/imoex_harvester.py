
import sys
sys.path.append('.')
import requests
import datetime
import time
from database.dbmain import DataBase
from database.model import CurrencyNames, CurrencyValue
from sqlalchemy.orm import Session, sessionmaker

def get_usd():
    url = 'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities/USD/RUB.json?iss.only=securities.current'
    res = requests.get(url)
    if res.status_code == 200:
        res, = res.json()['securities.current']['data']
        name = res[0]
        date_time = datetime.datetime.strptime(f'{res[1]} {res[2]}', '%Y-%m-%d %H:%M:%S')
        value = res[3] 
        db = DataBase()
        currency_name = db.get_or_create(model=CurrencyNames,name=name)
        currency_value = CurrencyValue(currency=currency_name.id,price=value,datetime=date_time)
        db.create(currency_value)

def start():
    while True:
        time.sleep(60)
        get_usd()

if __name__ == '__main__':
    start()