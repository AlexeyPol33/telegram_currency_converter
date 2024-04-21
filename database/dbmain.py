import sys
sys.path.append('.')
import sqlalchemy
from sqlalchemy.orm import sessionmaker
try:
    from model import CurrencyNames, CurrencyValue, Base
except:
    from .model import CurrencyNames, CurrencyValue, Base
from settings import DB_LOGIN,DB_PASSWORD,DB_NAME,DB_HOST

TABLE = {}

def get_engine():
    login = DB_LOGIN
    password = DB_PASSWORD
    dbname = DB_NAME
    host = DB_HOST
    DNS = f"postgresql+psycopg2://{login}:{password}@{host}:5432/{dbname}"
    engine = sqlalchemy.create_engine(DNS)
    return engine

def create_tables(engine):
    Base.metadata.create_all(engine)

def drop_tables(engine):
    Base.metadata.drop_all(engine)

def clear_db(engine):
    drop_tables(engine)
    create_tables(engine)

if __name__ == '__main__':
    engine = get_engine()
    create_tables(engine)



