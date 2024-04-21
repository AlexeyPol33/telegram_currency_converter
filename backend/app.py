import sys
sys.path.append('.')
import datetime
from settings import BACKEND_HOST
from flask import Flask, jsonify, request
from flask.views import MethodView
from database.dbmain import DataBase
from typing import Optional, Union
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError

app = Flask('app')

class CurrencyPair:

    first_currency: Optional[str]
    second_currency: Optional[str]
    date_time: datetime = None
    value:float = None
    _engine:sqlalchemy.engine = None
    _currency_name:None|CurrencyNames|tuple[CurrencyNames] = None
    _reverse_pair:bool = False

    def __new__(cls,*args,**kwargs):
        def engine():
            login = DB_LOGIN
            password = DB_PASSWORD
            dbname = DB_NAME
            host = DB_HOST
            DNS = f"postgresql+psycopg2://{login}:{password}@{host}:5432/{dbname}"
            engine = sqlalchemy.create_engine(DNS)
            return engine
        instance = super().__new__(cls)
        instance._engine = engine()
        return instance

    def __init__(self,first_currency,second_currency) -> None:
        self.first_currency = str(first_currency).upper()
        self.second_currency = str(second_currency).upper()
        with Session(bind=self._engine) as session:
            self._currency_name = session.query(CurrencyNames).filter_by(name=f'{self.first_currency}/{self.second_currency}').first()
            if self._currency_name is None:
                self._currency_name = session.query(CurrencyNames).filter_by(name=f'{self.second_currency}/{self.first_currency}').first()
                if self._currency_name is not None:
                    self._reverse_pair = True
        if self._currency_name is None:
            self._currency_name = self._get_nearby_currency_pairs()
        if self._currency_name is None:
            raise NoDataBaseValueError('No currency data in the database')
        
    def _get_nearby_currency_pairs(self) -> tuple[CurrencyNames]:
        first_list_currency_names:list[CurrencyNames] = None
        second_list_currency_names:list[CurrencyNames] = None
        with Session(bind=self._engine) as session:
            first_list_currency_names = session.query(CurrencyNames).filter(CurrencyNames.name[:3] == self.first_currency).all()
            second_list_currency_names = session.query(CurrencyNames).filter(CurrencyNames.name[:3] == self.second_currency).all()
        if not first_list_currency_names or not second_list_currency_names:
            raise NoDataBaseValueError('No currency data in the database')
        for first_currency_name in first_list_currency_names:
            for second_currency_name in second_list_currency_names:
                if first_currency_name.name[4:] == second_currency_name.name[4:]:
                    return tuple(first_currency_name, second_currency_name)
        return None
    
    def to_json(self):
        date_time:str = None
        if isinstance(self.date_time,datetime.datetime):
            date_time = datetime.datetime.strftime(self.date_time,'%Y-%m-%d %H:%M:%S')
        data = {
            'currency_pair':'/'.join([self.first_currency,self.second_currency]),
            'datetime':date_time,
            'value':self.value}
        return jsonify(data)

class CurrencyPairRateNow(CurrencyPair):

    def _get_current_exchange_rate(self) -> None:
        currency_value:CurrencyValue|dict = None
        if isinstance(self._currency_name,CurrencyNames):
            with Session(bind=self._engine) as session:
                currency_value = session.query(CurrencyValue).\
                    filter(
                        CurrencyValue.currency == self._currency_name.id).\
                    order_by(CurrencyValue.id.desc()).first()
                if not currency_value:
                    raise NoDataBaseValueError('No information on currency pair')
            self.date_time = currency_value.datetime
            if self._reverse_pair:
                self.value = 1 / currency_value.price
            else:
                self.value = currency_value.price
            return
        elif isinstance(self._currency_name,tuple):
            with Session(bind=self._engine) as session:
                currency_value = {}
                currency_value['first_currency_value'] = session.query(CurrencyValue).\
                    filter(
                        CurrencyValue.currency == self._currency_name[0].id).\
                                    order_by(CurrencyValue.id.desc()).first()
                currency_value['second_currency_value'] = session.query(CurrencyValue).\
                    filter(
                        CurrencyValue.currency == self._currency_name[1].id).\
                                    order_by(CurrencyValue.id.desc()).first()
                if  not currency_value['second_currency_value'] or not currency_value['first_currency_value']:
                    raise NoDataBaseValueError('No information on currency pair')
                self.date_time = currency_value['first_currency_value'].datetime
                self.value = currency_value['first_currency_value'].price / currency_value['second_currency_value'].price
                return 
        else:
            raise CurrencyConversionError('Conversion error')

    def __call__(self, *args,**kwargs) -> jsonify:

        self._get_current_exchange_rate()
        self.value *= kwargs.get('value',1)
        return self.to_json()

class CurrencyPairRateByTime(CurrencyPair):
    time_from:datetime
    time_till:datetime

    def __init__(self, first_currency, second_currency,time_from,time_till) -> None:
        super().__init__(first_currency, second_currency)


@app.route('/info', methods=['GET'])
def information():
    currencies = None
    def engine():
        login = DB_LOGIN
        password = DB_PASSWORD
        dbname = DB_NAME
        host = DB_HOST
        DNS = f"postgresql+psycopg2://{login}:{password}@{host}:5432/{dbname}"
        engine = sqlalchemy.create_engine(DNS)
        return engine
    with Session(bind=engine()) as session:
        quary = session.query(CurrencyNames).all()
        currencies = set(('/'.join([i.name for i in quary])).split('/'))

    return jsonify(
        {
            'currencies':list(currencies)
        }
    )

@app.route('/last_currency_rate/<currency_name_first>/<currency_name_second>', methods=['GET'])
def last_currency_rate(currency_name_first,currency_name_second):

    last_rate = CurrencyPairRateNow(currency_name_first,currency_name_second)
    return last_rate()

@app.route('/convert/<value>/<currency_name_first>/<currency_name_second>')
def convert_currencies(value,currency_name_first,currency_name_second):

    last_rate = CurrencyPairRateNow(currency_name_first,currency_name_second)
    return last_rate(value = float(value))

def start_server():

    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
