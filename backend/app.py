import sys
sys.path.append('.')
import datetime
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


class LastRate(MethodView):
    def get(self,currency_name_first,currency_name_second):
            last_rate = CurrencyPairRateNow(currency_name_first,currency_name_second)
            return jsonify(last_rate())


class ConvertCurrencies(MethodView):
    def get(self,currency_name_first,currency_name_second,value):
        last_rate = CurrencyPairRateNow(currency_name_first,currency_name_second)
        return last_rate(value = float(value))


class HistoricalCurrencyRate(MethodView):
    formats:dict = None

    def __init__(self):
        self.formats = {'.json':self.send_json,'.csv':self.send_csv,}
        super().__init__()

    def get(self,currency_name_first:str,currency_name_second:str):
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

app = Flask('app')

app.add_url_rule(
    '/info',
    view_func=СurrencyList.as_view('currency_list')
    )
app.add_url_rule(
    '/last_currency_rate/<currency_name_first>/<currency_name_second>',
    view_func=LastRate.as_view('last_rate')
    )
app.add_url_rule(
    '/convert/<value>/<currency_name_first>/<currency_name_second>',
    view_func=ConvertCurrencies.as_view('convert_currencies')
    )
app.add_url_rule(
    '/historical_currency_rate/<currency_name_first>/<currency_name_second>',
    view_func=HistoricalCurrencyRate.as_view('historical_currency_rate')
)

def start_server():

    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
