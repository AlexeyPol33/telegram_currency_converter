import requests
from database.dbmain import DataBase
from database.model import CurrencyNames, CurrencyValue
from sqlalchemy.orm import Session, sessionmaker

def get_usd():
    url = 'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities/USD/RUB.json?iss.only=securities.current'
    res = requests.get(url)
    if res.status_code == 200:
        res = res.json()['securities.current']['data']
        db = DataBase
        currency_names = db.get_or_create(CurrencyNames)
        


    pass


if __name__ == '__main__':
    pass