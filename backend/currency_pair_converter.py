import datetime
from flask import jsonify
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError
import sys
sys.path.append('.')


class CurrencyPair:

    first_currency: str | None
    second_currency: str | None
    date_time: datetime = None
    value: float = None
    _engine: sqlalchemy.engine = None
    _currency_name: CurrencyNames | tuple[CurrencyNames] = None
    _reverse_pair: bool = False

    def __new__(cls, *args, **kwargs):
        def engine():
            login = DB_LOGIN
            password = DB_PASSWORD
            dbname = DB_NAME
            host = DB_HOST
            engine = sqlalchemy.\
                create_engine(
                    f'postgresql+psycopg2://{login}:\
                        {password}@{host}:5432/{dbname}')
            return engine
        instance = super().__new__(cls)
        instance._engine = engine()
        return instance

    def __init__(self, first_currency: str = None,
                 second_currency: str = None,
                 obj: object = None, *args, **kwargs) -> None:
        if obj is not None:
            self.first_currency = obj.first_currency
            self.second_currency = obj.second_currency
            self.date_time = obj.date_time
            self.value = obj.value
            self._currency_name = obj._currency_name
            self._reverse_pair = obj._reverse_pair
        elif first_currency and second_currency and obj is None:
            self.first_currency = str(first_currency).upper()
            self.second_currency = str(second_currency).upper()
            with Session(bind=self._engine) as session:
                self._currency_name = session.query(CurrencyNames).\
                    filter_by(
                        name=f'{self.first_currency}/{self.second_currency}'
                        ).first()
                if self._currency_name is None:
                    self._currency_name = session.query(CurrencyNames).\
                        filter_by(
                            name=f'{self.second_currency}/\
                                        {self.first_currency}'
                            ).first()
                    if self._currency_name is not None:
                        self._reverse_pair = True
            if self._currency_name is None:
                self._currency_name = self._get_nearby_currency_pairs()
            if self._currency_name is None:
                raise NoDataBaseValueError('No currency data in the database')
        else:
            raise CurrencyConversionError('initialization error')

    def _get_nearby_currency_pairs(self) -> tuple[CurrencyNames]:
        first_list_currency_names: list[CurrencyNames] = None
        second_list_currency_names: list[CurrencyNames] = None
        with Session(bind=self._engine) as session:
            first_list_currency_names = session.query(CurrencyNames).\
                filter(
                    CurrencyNames.name.like(f'%{self.first_currency}%')).all()
            second_list_currency_names = session.query(CurrencyNames).\
                filter(
                    CurrencyNames.name.like(f'%{self.second_currency}%')).all()
        if not first_list_currency_names or not second_list_currency_names:
            raise NoDataBaseValueError('No currency data in the database')
        for first_currency_name in first_list_currency_names:
            for second_currency_name in second_list_currency_names:
                first_name = first_currency_name.name[4:]
                second_name = second_currency_name.name[4:]
                if first_name == second_name:
                    return tuple([first_currency_name, second_currency_name])
        return None

    def to_json(self):
        date_time: str = None
        if isinstance(self.date_time, datetime.datetime):
            date_time = datetime.datetime.\
                strftime(self.date_time, '%Y-%m-%d %H:%M:%S')
        data = {
            'currency_pair': '/'.join([
                self.first_currency,
                self.second_currency]),
            'datetime': date_time,
            'value': self.value}
        return jsonify(data)


class CurrencyPairRateNow(CurrencyPair):

    def _get_current_exchange_rate(self, *args, **kwargs):
        if isinstance(self._currency_name, CurrencyNames):
            currency_pair_rate = CurrencyPairRateNowSimpleConvert(obj=self)
        elif isinstance(self._currency_name, tuple):
            currency_pair_rate = CurrencyPairRateNowCrossConvert(obj=self)
        else:
            raise CurrencyConversionError('Incorrect format "_currency_name"')
        currency_pair_rate()
        self.date_time = currency_pair_rate.date_time
        self.value = currency_pair_rate.value
        self.value *= kwargs.get('value', 1)
        return self.to_json()

    def __call__(self, *args, **kwargs) -> jsonify:
        return self._get_current_exchange_rate(**kwargs)


class CurrencyPairRateNowSimpleConvert(CurrencyPairRateNow):

    def _get_current_exchange_rate(self) -> None:
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


class CurrencyPairRateNowCrossConvert(CurrencyPairRateNow):

    def _get_current_exchange_rate(self) -> None:
        with Session(bind=self._engine) as session:
            currency_value_one: CurrencyValue = None
            currency_value_two: CurrencyValue = None
            currency_value_one = session.query(CurrencyValue).\
                filter(
                    CurrencyValue.currency == self._currency_name[0].id
                        ).order_by(CurrencyValue.id.desc()).first()
            currency_value_two = session.query(CurrencyValue).\
                filter(
                    CurrencyValue.currency == self._currency_name[1].id
                        ).order_by(CurrencyValue.id.desc()).first()
            if not currency_value_two or not currency_value_one:
                raise NoDataBaseValueError('No information on currency pair')
            self.date_time = currency_value_one.datetime
            self.value = currency_value_one.price/currency_value_two.price
        return


class CurrencyPairRateByTime(CurrencyPair):
    time_from: datetime = None
    time_till: datetime = None

    def __init__(self, first_currency=None, second_currency=None,
                 time_from=None, time_till=None,
                 obj: object = None, *args, **kwargs) -> None:
        if obj:
            self.time_from = obj.time_from
            self.time_till = obj.time_till
        elif time_from and time_till and obj is None:
            self.time_from = time_from
            self.time_till = time_till
        super().__init__(first_currency, second_currency, obj, *args, **kwargs)

    def __getitem__(self, key: datetime) -> list[dict]:
        if isinstance(self._currency_name, CurrencyNames):
            item = CurrencyPairRateByTimeSimpleConvert(obj=self)
            return item[key]
        elif isinstance(self._currency_name, tuple):
            item = CurrencyPairRateByTimeCrossConvert(obj=self)
            return item[key]

    def __iter__(self):
        if isinstance(self._currency_name, CurrencyNames):
            return CurrencyPairRateByTimeSimpleConvert(obj=self).__iter__()
        elif isinstance(self._currency_name, tuple):
            return CurrencyPairRateByTimeCrossConvert(obj=self).__iter__()


class CurrencyPairRateByTimeSimpleConvert(CurrencyPairRateByTime):

    def __getitem__(self, key: datetime) -> list[dict]:
        currency_value: CurrencyValue = None
        delta = key + datetime.timedelta(days=1)

        with Session(bind=self._engine) as session:
            currency_value = session.query(CurrencyValue).filter(
                CurrencyValue.currency == self._currency_name.id,
                delta >= CurrencyValue.datetime,
                CurrencyValue.datetime >= key).all()
            if not currency_value:
                raise NoDataBaseValueError(
                    'There is no value in this time period'
                    )
            return [{
                'currency_pair': '/'.join([
                    self.first_currency,
                    self.second_currency]),
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
                    CurrencyValue.datetime <= self.time_till).all()
                self.__start_time = self.__start_time + self.__time_step
                return [{
                    'currency_pair': '/'.join([
                        self.first_currency,
                        self.second_currency]),
                    'datetime':i.datetime,
                    'value':i.price,
                } for i in query]
        with Session(bind=self._engine) as session:
            delta = self.__start_time + self.__time_step
            query = session.query(CurrencyValue).filter(
                    CurrencyValue.currency == self._currency_name.id,
                    CurrencyValue.datetime >= self.__start_time,
                    CurrencyValue.datetime <= delta).all()
            self.__start_time = delta
            return [{
                'currency_pair': '/'.join([
                    self.first_currency,
                    self.second_currency]),
                'datetime':i.datetime,
                'value':i.price,
                } for i in query]


class CurrencyPairRateByTimeCrossConvert(CurrencyPairRateByTime):
    def __getitem__(self, key: datetime) -> list[dict]:
        delta = key + datetime.timedelta(days=1)
        currency_value_one: list = []
        currency_value_two: list = []
        result: list[dict] = []
        with Session(bind=self._engine) as session:
            query = session.query(CurrencyValue).filter(
                CurrencyValue.currency == self._currency_name[0].id,
                CurrencyValue.currency == self._currency_name[1].id,
                CurrencyValue.datetime <= delta,
                CurrencyValue.datetime >= key).all()
            for q in query:
                if q.currency == self._currency_name[0].id:
                    currency_value_one.append(q)
                else:
                    currency_value_two.append(q)
            currency_value_one.sort(key=lambda q: q.datetime)
            currency_value_two.sort(key=lambda q: q.datetime)
            for currency_one in currency_value_one:
                for currency_two in currency_value_two:
                    if currency_one.datetime == currency_two.datetime:
                        result.append({
                            'currency_pair': '/'.join([
                                self.first_currency,
                                self.second_currency]),
                            'datetime': currency_one.datetime,
                            'value': currency_one.price / currency_two.price})
                        currency_value_two.remove(currency_two)
                        continue
        return result

    def __iter__(self):
        raise CurrencyConversionError()
        return super().__iter__()

    def __next__(self):
        raise StopIteration
