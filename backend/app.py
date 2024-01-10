import sys
sys.path.append('.')
from settings import BACKEND_HOST
from flask import Flask, jsonify, request
from flask.views import MethodView
from database.dbmain import DataBase
from database.model import CurrencyNames, CurrencyValue
from sqlalchemy.orm import Session, sessionmaker

app = Flask('app')

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
def get_last_currency_rate(currency_name_first,currency_name_second):
    currency_name = currency_name_first + '/' + currency_name_second
    db = DataBase()
    currency = db.session.query(CurrencyNames).filter_by(name = currency_name).first()
    if currency:
        last_currency_rate = db.session.query(CurrencyValue).filter_by(currency = currency.id).order_by(CurrencyValue.id.desc()).first()
    else:
        first_currency_pair = db.session.query(CurrencyNames).filter_by(name = currency_name_first +'/RUB').first()
        second_currency_pair = db.session.query(CurrencyNames).filter_by(name = currency_name_second +'/RUB').first()
        if first_currency_pair and second_currency_pair:
            pass
        else:
            pass #TODO Add error message
        first_currency_value = db.session.query(CurrencyValue).filter_by(currency = first_currency_pair.id).order_by(CurrencyValue.id.desc()).first()
        second_currency_pair = db.session.query(CurrencyValue).filter_by(currency = second_currency_pair.id).order_by(CurrencyValue.id.desc()).first()
        last_currency_rate = {
            'currency_name': currency_name,
            'price': first_currency_value.price}



    return jsonify(
        {
            'id': last_currency_rate.id,
            'currency_name': currency.name,
            'price':last_currency_rate.price,
            'datetime': last_currency_rate.datetime,
        }
    )

def start_server():
    app.run(host=BACKEND_HOST)

if __name__ == '__main__':
    start_server()
