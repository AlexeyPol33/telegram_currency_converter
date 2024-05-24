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
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError, SendFormatError
from currency_pair_converter import CurrencyPair, CurrencyPairRateNow, CurrencyPairRateByTime
import pandas as pd
from io import BytesIO
import json
import matplotlib as mpl
import matplotlib.pyplot as plt

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
    @property
    def _engine (self):
        url_object = sqlalchemy.URL.create(
            'postgresql+psycopg2',
            username=DB_LOGIN,
            password=DB_PASSWORD,
            host=DB_HOST,
            database=DB_NAME)
        engine = sqlalchemy.create_engine(url_object)
        return engine

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

    def get(self,first_currency: str, second_currency: str):
        
        first_currency = first_currency.upper()
        second_currency = second_currency.upper()
        time_from = request.args.get('time_from',datetime.datetime.now())
        time_till = request.args.get('time_till',datetime.datetime.now())
        try:
            time_from = datetime.datetime.strptime(time_from,'%Y-%m-%d')
            time_till = datetime.datetime.strptime(time_till,'%Y-%m-%d')
        except:
            pass
        _format = request.args.get('format','.json')
        send = send_Formats.get(_format)
        if send is None:
            raise SendFormatError('Format not supported',400)
        currency_pair_rate_by_time = CurrencyPairRateByTime(
            first_currency=first_currency,
            second_currency=second_currency,
            time_from=time_from,
            time_till=time_till)
        data = []
        for i in currency_pair_rate_by_time:
            data.extend(i)
        return send(data).send()

@UrlRuleRegister('/send_formats')
class SendFormatsView(MethodView):
    global send_Formats

    def get(self):
        return jsonify({'formats':list(send_Formats.keys())})

    class SendFormat(ABC):

        def __init__(self, data: list[dict]) -> None:
            self.data = data

        @property
        def file_name(self) -> str:
            pair_name = tuple(self.data[0].values())[0]
            start_datetime = tuple(self.data[0].values())[1]
            end_datetime = tuple(self.data[-1].values())[1]
            return f'{pair_name}_{start_datetime}-{end_datetime}'

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

        def send(self):
            data_frame = pd.DataFrame(data=self.data)
            csv = data_frame.to_csv(index=False).encode()
            file = BytesIO(csv)
            return send_file(
                path_or_file=file,
                download_name=f'{self.file_name}.csv',
                mimetype='text/csv')
        

    @FormatRegistr('.json')
    class SendJSON(SendFormat):

        def send(self):
            file = BytesIO(json.dumps(self.data,default=str).encode())
            return send_file(
                path_or_file=file,
                download_name=f'{self.file_name}.json')


    @FormatRegistr('.txt')
    class SendTXT(SendFormat):

        def send(self):
            file = BytesIO(str(self.data).encode())
            return send_file(
                path_or_file=file,
                download_name=f'{self.file_name}.txt')


    @FormatRegistr('.png')
    class SendPNG(SendFormat):

        def send(self):
            date = [tuple(d.values())[1] for d in self.data]
            price = [tuple(d.values())[2] for d in self.data]
            file = BytesIO()
            mpl.use('agg')
            plt.figure(figsize=(20,14), dpi= 80)
            plt.plot(date,price,color='blue')
            plt.xlabel('Время')
            plt.ylabel('Цена')
            plt.title(self.file_name, fontsize=22)
            plt.grid(axis='both', alpha=.3)
            plt.savefig(file,format='png')
            file.seek(0)
            return send_file(
                path_or_file=file,
                download_name=f'{self.file_name}.png',
                mimetype='image/png')


def start_server():

    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
