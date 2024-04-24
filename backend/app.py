import sys
sys.path.append('.')
import datetime
from settings import BACKEND_HOST
from flask import Flask, jsonify, request
from flask.views import MethodView
from typing import Optional, Union
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError
from currency_pair_converter import CurrencyPair, CurrencyPairRateNow, CurrencyPairRateByTime

app = Flask('app')

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

@app.route('/historical_currency_rate/<currency_name_first>/<currency_name_second>/<time_from>/<time_till>')
def historical_currency_rate(currency_name_first,currency_name_second,time_from,time_till):
    time_from = datetime.datetime.strptime(time_from,'%Y-%m-%d')
    time_till = datetime.datetime.strptime(time_till,'%Y-%m-%d')
    currency_pair_rate_by_time = CurrencyPairRateByTime(currency_name_first,currency_name_second,time_from,time_till)
    if time_from == time_till:
        response = currency_pair_rate_by_time[time_from]
    return jsonify(response)

def start_server():

    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
