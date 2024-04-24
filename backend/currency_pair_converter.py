import sys
sys.path.append('.')
import datetime
from flask import sonify
from typing import Optional
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError


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

    def __init__(self,first_currency:str,second_currency:str) -> None:
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
    time_from:datetime = None
    time_till:datetime = None

    def __init__(self, first_currency:str, second_currency:str,time_from:datetime,time_till:datetime) -> None:
        self.time_from = time_from
        self.time_till = time_till
        super().__init__(first_currency, second_currency)

    def __getitem__(self,key: datetime) -> list[dict]:
        currency_value:CurrencyValue = None
        delta = key + datetime.timedelta(days=1)
        if isinstance(self._currency_name, tuple):
            raise AttributeError()
        with Session(bind=self._engine) as session:
            currency_value = session.query(CurrencyValue).filter(
                CurrencyValue.currency == self._currency_name.id,
                delta >= CurrencyValue.datetime,
                CurrencyValue.datetime >= key).all()
            if not currency_value:
                raise NoDataBaseValueError('There is no value in this time period')
            return [{
                'currency_pair':'/'.join([self.first_currency,self.second_currency]),
                'datetime':i.datetime,
                'value':i.price,
                } for i in currency_value]

    def __iter__(self):
        self.__start_time = self.time_from
        self.__time_step = datetime.timedelta(days=30)
        return self

    def __next__(self):
        if self.__start_time > self.time_till:
            raise StopIteration
        elif self.__start_time + self.__time_step >= self.time_till:
            with Session(bind=self._engine) as session:
                query = session.query(CurrencyValue).filter(
                    CurrencyValue.currency == self._currency_name.id,
                    CurrencyValue.datetime >= self.__start_time,
                    CurrencyValue.datetime <= self.time_till)
                self.__start_time = self.__start_time + self.__time_step
                return [{
                'currency_pair':'/'.join([self.first_currency,self.second_currency]),
                'datetime':i.datetime,
                'value':i.price,
                } for i in query]
        with Session(bind=self._engine):
            pass