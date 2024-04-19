
import sys
sys.path.append('.')
import requests
import logging
from datetime import datetime, timedelta
import time
import sqlalchemy
from database.dbmain import DataBase
from database.model import CurrencyNames, CurrencyValue
from sqlalchemy.orm import Session, sessionmaker
from settings import DB_LOGIN,DB_PASSWORD,DB_NAME,DB_HOST,COLLECT_HISTORICAL_DATA

logging.basicConfig(
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class CurrencyPairsList:
    URL =  'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities.json?iss.only=securities.list'
    __moex_data:list[list] = None
    __date_filter:datetime = None

    def __new__(cls,*args,**kwargs):
        instance = super().__new__(cls)
        res = requests.get(instance.URL).json()['securities.list']['data']
        instance.__moex_data = res
        return instance

    def __init__(self,date_filter:datetime = None) -> None:
        if date_filter:
            self.__date_filter = date_filter

    def __iter__(self):
        if self.__date_filter:
            self.__filtered_data = [
                data 
                for data in self.__moex_data 
                if datetime.strptime(data[-1],'%Y-%m-%d') >= self.__date_filter
                ]
        else:
            self.__filtered_data = list(self.__moex_data)
        return self

    def __next__(self):
        if self.__filtered_data:
            match self.__filtered_data.pop():
                case [secid,title,time_from, time_till]:
                    time_from = datetime.strptime(time_from,'%Y-%m-%d')
                    time_till = datetime.strptime(time_till,'%Y-%m-%d')
                    return {'secid':secid,'title':title,'time_from':time_from, 'time_till':time_till}
                case __:
                    raise StopIteration
        else:
            raise StopIteration

class CurrentExchangeRate:
    URL = 'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities/{}.json?iss.only=securities.current'
    currency_pairs: tuple = None

    def __init__(self,currency_pairs:list[str]) -> None:
        self.currency_pairs = tuple(currency_pairs)

    def __iter__(self):
        self.__start = 0
        self.__end = len(self.currency_pairs)
        return self
    
    def __next__(self):
        if self.__start != self.__end:
            res = requests.get(self.URL.format(self.currency_pairs[self.__start]))
            res = res.json()['securities.current']['data']
            self.__start += 1
            match res:
                case [[name,date,time,value]]:
                    return {
                        'name':name,
                        'datetime':datetime.strptime(f'{date} {time}','%Y-%m-%d %H:%M:%S'),
                        'value': float(value)
                        }
                case __:
                    return None
        else:
            raise StopIteration

class HistoricalExchangeRate:
    URL = 'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates/securities/{}.json?from={}&till={}&iss.meta=off&iss.only=securities'
    currency_pair: str = None
    date_from: datetime = None
    date_till: datetime = None

    def __init__(self,currency_pair:str, date_from:datetime, date_till:datetime) -> None:
        self.currency_pair = str(currency_pair)
        self.date_from = date_from
        self.date_till = date_till

    def __iter__(self):
        self.__time_delta = timedelta(days=30)
        self.__date_from = self.date_from
        self.__date_till = self.date_till
        return self
    
    def __next__(self):
        if self.__date_from >= self.__date_till:
            raise StopIteration
        date_from = self.__date_from.strftime('%Y-%m-%d')
        date_till = (self.__date_from + self.__time_delta).strftime('%Y-%m-%d')
        res = requests.get(self.URL.format(self.currency_pair,date_from,date_till))
        res = res.json()['securities']['data']
        result = []
        while res:
            item = res.pop(0)
            match item:
                case [tradedate,tradetime,secid,rate,_]:
                    result.append(
                        {
                            'name':secid,
                            'datetime':datetime.strptime(f'{tradedate} {tradetime}','%Y-%m-%d %H:%M:%S'),
                            'value':float(rate)
                        })
        self.__date_from = self.__date_from + self.__time_delta
        return result

def get_engine():
    login = DB_LOGIN
    password = DB_PASSWORD
    dbname = DB_NAME
    host = DB_HOST
    DNS = f"postgresql+psycopg2://{login}:{password}@{host}:5432/{dbname}"
    engine = sqlalchemy.create_engine(DNS)
    return engine

def write_currency_names(names:list[str])->None:
    with Session(bind=get_engine()) as session:
        currency_names = [CurrencyNames(name=n) for n in names]
        session.add_all(currency_names)
        session.commit()

def write_historical_data(currency_pair:str,date_from:datetime,date_till:datetime)->None:
    with Session(bind=get_engine()) as session:
        currency_name = session.query(CurrencyNames).filter_by(name=currency_pair).first()
        for one_month_data in HistoricalExchangeRate(currency_pair,date_from,date_till):
            currency_values = [CurrencyValue(
                currency=currency_name.id,
                price=data['value'],
                datetime=data['datetime']) for data in one_month_data]
            session.add_all(currency_values)
        session.commit()

def poling_current_exchange_rate(currency_names:list[CurrencyNames])->None:
    currency_names_dict = {bd_obj.name:bd_obj for bd_obj in currency_names}
    current_exchange_rate = CurrentExchangeRate(list(currency_names_dict.keys()))
    while True:
        with Session(bind=get_engine()) as session:
            for data in current_exchange_rate:
                currency_value = CurrencyValue(
                    currency=currency_names_dict[data['name']].id,
                    price=data['value'],
                    datetime=data['datetime'],)
                session.add(currency_value)
            session.commit()
        time.sleep(60)

def start()->None:
    currency_names: list[CurrencyNames]
    currency_pairs_list = [currency_pair for currency_pair in CurrencyPairsList(datetime.now() - timedelta(days=30))]
    logging.info('List of currency pairs received successfully')
    currency_pairs_names = [name['secid'] for name in currency_pairs_list]
    with Session(bind=get_engine()) as session:
        currency_names = session.query(CurrencyNames).all()

    if not currency_names:
        write_currency_names(currency_pairs_names)
        with Session(bind=get_engine()) as session:
            currency_names = session.query(CurrencyNames).all()
        logging.info('List of currency pairs is writed successfully')

    if COLLECT_HISTORICAL_DATA:
        for cp in currency_pairs_list:
            write_historical_data(
                currency_pair=cp['secid'],
                date_from=cp['time_from'],
                date_till=cp['time_till'],
                )
            logging.info(f'{cp.get("secid")} historical data is writed successfully')
    logging.info('start poling')
    poling_current_exchange_rate(currency_names)

if __name__ == '__main__':
    start()