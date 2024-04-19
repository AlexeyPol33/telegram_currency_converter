import sys
sys.path.append('.')
from settings import BACKEND_HOST
from flask import Flask, jsonify, request
from flask.views import MethodView
from database.dbmain import DataBase
from database.model import CurrencyNames, CurrencyValue
from sqlalchemy.orm import Session, sessionmaker

app = Flask('app')

def get_last_currency_rate(currency_name_first: str, currency_name_second:str) -> dict:

    currency_name_first = currency_name_first.upper()
    currency_name_second = currency_name_second.upper()
    currency_name = currency_name_first + '/' + currency_name_second
    db = DataBase()
    currency = db.session.query(CurrencyNames).filter_by(name = currency_name).first()

    if currency:
        last_currency_rate = db.session.query(CurrencyValue).filter_by(currency = currency.id).order_by(CurrencyValue.id.desc()).first()
        return {
            'id': last_currency_rate.id,
            'currency_name': currency.name,
            'price':last_currency_rate.price,
            'datetime': last_currency_rate.datetime,
        }
    else:
        reverse_currency_name = currency_name_second + '/' + currency_name_first
        currency = db.session.query(CurrencyNames).filter_by(name = reverse_currency_name).first()

        if currency:
            last_currency_rate = db.session.query(CurrencyValue).filter_by(currency = currency.id).order_by(CurrencyValue.id.desc()).first()
            return {
                'id': last_currency_rate.id,
                'currency_name': reverse_currency_name,
                'price':1/last_currency_rate.price,
                'datetime': last_currency_rate.datetime,
            }
        else:
            _currency_name_first = currency_name_first + '/RUB'
            _currency_name_second = currency_name_second + '/RUB'

            currency_name_first = db.session.query(CurrencyNames).filter_by(name=_currency_name_first).first()
            currency_name_second = db.session.query(CurrencyNames).filter_by(name=_currency_name_second).first()
            if currency_name_first and currency_name_second:
                currency_first = db.session.query(CurrencyValue).filter_by(currency = currency_name_first.id).order_by(CurrencyValue.id.desc()).first()
                currency_second = db.session.query(CurrencyValue).filter_by(currency = currency_name_second.id).order_by(CurrencyValue.id.desc()).first()
                return {
                    'id':'None',
                    'currency_name': currency_name,
                    'price': currency_first.price / currency_second.price,
                    'datetime': str(currency_first.datetime) + ' - ' + str(currency_second.datetime)
                    }
    return None

@app.route('/info', methods=['GET'])
def information():
    db = DataBase()
    currencies = set(('/'.join([i.name for i in db.session.query(CurrencyNames).all()])).split('/'))

    return jsonify(
        {
            'currencies':list(currencies)
        }
    )

@app.route('/last_currency_rate/<currency_name_first>/<currency_name_second>', methods=['GET'])
def last_currency_rate(currency_name_first,currency_name_second):

    last_rate = get_last_currency_rate(currency_name_first,currency_name_second)
    if last_rate:
        return jsonify(last_rate)
    else:
        return ('not found',404)

@app.route('/convert/<value>/<currency_name_first>/<currency_name_second>')
def convert_currencies(value,currency_name_first,currency_name_second):

    last_rate = get_last_currency_rate(currency_name_first,currency_name_second)
    if last_rate and value.isdecimal():
        last_rate['price'] = last_rate['price'] * float(value)
        return jsonify(last_rate)

    return ('Err', 400)

def start_server():
    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
