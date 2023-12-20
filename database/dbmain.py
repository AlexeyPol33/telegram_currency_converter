import sqlalchemy
from sqlalchemy.orm import sessionmaker
from model import CurrencyNames, CurrencyValue, Base
from os import getenv

TABLE = {}

def get_engine(login,password,dbname):
    DNS = f"postgresql://{login}:{password}@localhost:5432/{dbname}"
    engine = sqlalchemy.create_engine(DNS)
    return engine

def create_tables(engine):
    Base.metadata.create_all(engine)

def drop_tables(engine):
    Base.metadata.drop_all(engine)

def cleat_db(engine):
    drop_tables(engine)
    create_tables(engine)

class DataBase:
    def __init__(self,engine) -> None:
        self.engine = engine
        Session = sessionmaker(bind=self.engin)

if __name__ == '__main__':
    engine = get_engine(
        login=getenv('DB_LOGIN',default='postgres'),
        password=getenv('DB_PASSWORD',default='postgres'),
        dbname=getenv('DB_NAME')
    )
    create_tables(engine)

    

