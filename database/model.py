from sqlalchemy import Column, Integer, BigInteger,\
ForeignKey,String, Double, DateTime, create_engine, URL
from sqlalchemy.orm import declarative_base, relationship
from settings import DB_LOGIN, DB_PASSWORD, DB_NAME, DB_HOST

Base = declarative_base()


class CurrencyNames(Base):
    __tablename__ = 'currency_names'

    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String(20), unique=True)


class CurrencyValue(Base):

    __tablename__ = 'currency_value'
    id = Column(BigInteger, autoincrement=True, primary_key=True)
    currency = Column(Integer, ForeignKey('currency_names.id'),nullable=False)
    price = Column(Double, nullable=False)
    datetime = Column(DateTime, nullable=None)

    currency_names = relationship(CurrencyNames, backref='currency_value', cascade='delete')

def engine():
    url_object = URL.create(
        'postgresql+psycopg2',
        username=DB_LOGIN,
        password=DB_PASSWORD,
        host=DB_HOST,
        database=DB_NAME,
        )
    engine = create_engine(url_object)
    return engine

def create_tables(engine):
    Base.metadata.create_all(engine)

def drop_tables(engine):
    Base.metadata.drop_all(engine)

def clear_db(engine):
    drop_tables(engine)
    create_tables(engine)

if __name__ == '__main__':
    engine = engine()
    create_tables(engine)