import sys
sys.path.append('.')
import datetime
from database.model import CurrencyNames, CurrencyValue
import sqlalchemy
from sqlalchemy.orm import Session
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST
from itertools import zip_longest
from backend_exceptions import NoDataBaseValueError, CurrencyConversionError


class CurrencyPairBase:
    first_currency: str | None
    second_currency: str | None
    date_time: datetime = None
    value: float = None

    def __init__(self, **kwargs) -> None:
        self.first_currency = kwargs.get('first_currency', None)
        self.second_currency = kwargs.get('second_currency', None)
        self.date_time = kwargs.get('date_time', None)
        self.value = kwargs.get('value', None)

    @property
    def _engine(self):
        url_object = sqlalchemy.URL.create(
            'postgresql+psycopg2',
            username=DB_LOGIN,
            password=DB_PASSWORD,
            host=DB_HOST,
            database=DB_NAME)
        engine = sqlalchemy.create_engine(url_object)
        return engine

class CurrencyPair(CurrencyPairBase):
    _currency_name: CurrencyNames | tuple[CurrencyNames] = None
    _reverse_pair: bool = False

    def __init__(self, first_currency: str = None,
                 second_currency: str = None,
                 obj: object = None, *args, **kwargs) -> None:
        if obj is not None:
            self._init_obj(obj)
        elif first_currency and second_currency and obj is None:
            self._init_currencies(first_currency, second_currency)
        else:
            raise CurrencyConversionError('initialization error')
    
    @classmethod
    def init_obj(cls,object:CurrencyPairBase) -> object:
        pass

    def _init_currencies(self, first_currency, second_currency):
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

    def _init_obj(self, obj) -> None:
        self.first_currency = obj.first_currency
        self.second_currency = obj.second_currency
        self.date_time = obj.date_time
        self.value = obj.value
        self._currency_name = obj._currency_name
        self._reverse_pair = obj._reverse_pair

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

    def to_dict(self):
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
        return data


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
        return self.to_dict()

    def __call__(self, *args, **kwargs) -> dict:
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

    def __iter__(self):
        if isinstance(self._currency_name, CurrencyNames):
            return CurrencyPairRateByTimeSimpleConvert(obj=self).__iter__()
        elif isinstance(self._currency_name, tuple):
            return CurrencyPairRateByTimeCrossConvert(obj=self).__iter__()


class CurrencyPairRateByTimeSimpleConvert(CurrencyPairRateByTime):

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

    def __iter__(self):
        self.__start_time = self.time_from
        self.__time_step = datetime.timedelta(days=30)
        return self

    def __next__(self):
        result = []
        if self.__start_time > self.time_till:
            raise StopIteration
        elif self.__start_time + self.__time_step >= self.time_till:
            with Session(bind=self._engine) as session:
                query_one = session.query(CurrencyValue).filter(
                    CurrencyValue.currency == self._currency_name[0].id,
                    CurrencyValue.datetime >= self.__start_time,
                    CurrencyValue.datetime <= self.time_till).all()
                query_two = session.query(CurrencyValue).filter(
                    CurrencyValue.currency == self._currency_name[1].id,
                    CurrencyValue.datetime >= self.__start_time,
                    CurrencyValue.datetime <= self.time_till).all()
                query_zip = zip_longest(query_one,query_two)
                for pair_one, pair_two in query_zip:
                    if pair_one is None or pair_two is None:
                        continue
                    elif pair_one.datetime == pair_two.datetime:
                        result.append(
                            {
                                'currency_pair':'/'.join(
                                    [self.first_currency,
                                     self.second_currency]),
                                'datetime':pair_one.datetime,
                                'value':pair_one.price/pair_two.price
                            })
                self.__start_time = self.__start_time + self.__time_step
                return result
        with Session(bind=self._engine) as session:
            delta = self.__start_time + self.__time_step

            query_one = session.query(CurrencyValue).filter(
                    CurrencyValue.currency == self._currency_name[0].id,
                    CurrencyValue.datetime >= self.__start_time,
                    CurrencyValue.datetime <= delta).all()
            query_two = session.query(CurrencyValue).filter(
                    CurrencyValue.currency == self._currency_name[1].id,
                    CurrencyValue.datetime >= self.__start_time,
                    CurrencyValue.datetime <= delta).all()
            self.__start_time = delta
            query_zip = zip_longest(query_one,query_two)
            for pair_one, pair_two in query_zip:
                print(pair_one, pair_two)
                if pair_one is None or pair_two is None:
                    continue
                elif pair_one.datetime == pair_two.datetime:
                    result.append(
                        {
                            'currency_pair':'/'.join(
                                [self.first_currency,
                                    self.second_currency]),
                            'datetime':pair_one.datetime,
                            'value':pair_one.price/pair_two.price
                        })
                self.__start_time = delta
                return result
        
