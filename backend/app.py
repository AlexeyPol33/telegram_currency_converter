import sys
sys.path.append('.')
import datetime
from settings import BACKEND_HOST
from flask import Flask, jsonify, request
from flask.views import View
from typing import Optional, Union
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError
from currency_pair_converter import CurrencyPair, CurrencyPairRateNow, CurrencyPairRateByTime


class СurrencyList(View):
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
        with Session(bind=self._engine()) as session:
            quary = session.query(CurrencyNames).all()
            currencies = set(('/'.join([i.name for i in quary])).split('/'))
        return jsonify({
                'currencies':list(currencies)
            })


class LastRate(View):
    def get(self,currency_name_first,currency_name_second):
            last_rate = CurrencyPairRateNow(currency_name_first,currency_name_second)
            return jsonify(last_rate())


class ConvertCurrencies(View):
    def get(self,currency_name_first,currency_name_second,value):
        last_rate = CurrencyPairRateNow(currency_name_first,currency_name_second)
        return last_rate(value = float(value))


class HistoricalCurrencyRate(View):
    def get(self,currency_name_first,currency_name_second,time_from,time_till):
        time_from = datetime.datetime.strptime(time_from,'%Y-%m-%d')
        time_till = datetime.datetime.strptime(time_till,'%Y-%m-%d')
        currency_pair_rate_by_time = CurrencyPairRateByTime(currency_name_first,currency_name_second,time_from,time_till)
        if time_from == time_till:
            response = currency_pair_rate_by_time[time_from]
        return jsonify(response)


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
    '/historical_currency_rate/<currency_name_first>/<currency_name_second>/<time_from>/<time_till>',
    view_func=HistoricalCurrencyRate.as_view('historical_currency_rate')
)

def start_server():

    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
