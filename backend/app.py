import sys
sys.path.append('.')
import datetime
from abc import ABC, abstractmethod
from settings import BACKEND_HOST
from flask import Flask, jsonify, request, send_file
from flask.views import MethodView, View
from typing import Optional, Union
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError
from currency_pair_converter import CurrencyPair, CurrencyPairRateNow, CurrencyPairRateByTime
import pandas as pd
from io import BytesIO


app = Flask('app')
send_Formats: dict = {}

class UrlRuleRegister():
    global app

    def __init__(self, path: str) -> None:
        self.path = path

    def __call__(self, obj: MethodView):
        app.add_url_rule(
            rule=self.path,
            view_func=obj.as_view(obj.__name__))
        return obj


@UrlRuleRegister('/currency_list')
class СurrencyList(MethodView):
    _engine: sqlalchemy.engine

    def __new__(cls):
        def engine() -> sqlalchemy.engine:
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

    def get(self):
        currencies = None
        with Session(bind=self._engine) as session:
            quary = session.query(CurrencyNames).all()
            currencies = set(('/'.join([i.name for i in quary])).split('/'))
        return jsonify({
                'currencies':list(currencies)
            })


@UrlRuleRegister('/convert/<first_currency>/<second_currency>')
class ConvertCurrencies(MethodView):

    def get(self,first_currency,second_currency):
        value = float(request.args.get('value',1))
        last_rate = CurrencyPairRateNow(first_currency,second_currency)
        return last_rate(value=value)

@UrlRuleRegister('/historical_rate/<first_currency>/<second_currency>')
class HistoricalCurrencyRate(MethodView):
    formats:dict = None

    def __init__(self):
        self.formats = {'.json':self.send_json,'.csv':self.send_csv,}
        super().__init__()

    def get(self,first_currency, second_currency:str):
        _format: str = None
        currency_name_first = currency_name_first.upper()
        find_dot = currency_name_second.find('.')
        if find_dot > 0:
            _format = currency_name_second[find_dot:]
            currency_name_second = currency_name_second[:find_dot]
        currency_name_second = currency_name_second.upper()
        time_from = request.args.get('time_from',datetime.datetime.now())
        time_till = request.args.get('time_till',datetime.datetime.now())
        if isinstance(time_from,str):
            time_from = datetime.datetime.strptime(time_from,'%Y-%m-%d')
        if isinstance(time_till,str):
            time_till = datetime.datetime.strptime(time_till,'%Y-%m-%d')
        currency_pair_rate_by_time = CurrencyPairRateByTime(
            first_currency=currency_name_first,
            second_currency=currency_name_second,
            time_from=time_from,
            time_till=time_till
            )
        return self.formats.get(_format,self.send_json)(currency_pair_rate_by_time)

    def send_json(self,currency_pair_rate_by_time: CurrencyPairRateByTime):
        return jsonify([c for c in currency_pair_rate_by_time])

    def send_csv(self,currency_pair_rate_by_time: CurrencyPairRateByTime):
        data_frame = pd.DataFrame(*[data for data in currency_pair_rate_by_time])
        csv = data_frame.to_csv(index=False).encode()
        csv = BytesIO(csv)
        return send_file(csv,download_name='test.csv',mimetype='text/csv')
    
    class SendFormat(ABC):

        @abstractmethod
        def __init__(self) -> None:
            pass
        
        @abstractmethod
        def send(self):
            pass
    
    class FormatRegistr():
        global send_Formats

        def __init__(self,format_name) -> None:
            self.format_name = format_name

        def __call__(self,obj):
            send_Formats[self.format_name] = obj
            return obj


    @FormatRegistr('.csv')
    class SendCSV(SendFormat):
        def __init__(self) -> None:
            pass

        def send(self):
            pass


    @FormatRegistr('.json')
    class SendJSON(SendFormat):

        def __init__(self) -> None:
            pass

        def send(self):
            pass

    
    @FormatRegistr('.txt')
    class SendTXT(SendFormat):
        def __init__(self) -> None:
            pass

        def send(self):
            pass


    @FormatRegistr('.png')
    class SendPNG(SendFormat):
        def __init__(self) -> None:
            pass

        def send(self):
            pass


def start_server():

    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    #start_server()
    print(HistoricalCurrencyRate.__name__)
    pass
