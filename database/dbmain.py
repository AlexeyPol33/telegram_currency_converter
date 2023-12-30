import sys
sys.path.append('.')
import sqlalchemy
from sqlalchemy.orm import sessionmaker
try:
    from model import CurrencyNames, CurrencyValue, Base
except:
    from .model import CurrencyNames, CurrencyValue, Base
from os import getenv

TABLE = {}

def get_engine():
    login,=getenv('DB_LOGIN',default='postgres'),
    password,=getenv('DB_PASSWORD',default='postgres'),
    dbname=getenv('DB_NAME')
    DNS = f"postgresql+psycopg2://{login}:{password}@localhost:5432/{dbname}"
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
    def __init__(self) -> None:
        self.engine = get_engine()
        self.session = sessionmaker(bind=self.engine)()

    def __dell__(self):
        self.session.commit()

    def create(self,instance):
        session = self.session
        session.add(instance)
        session.commit()

    def get_or_create(self, model, **kwargs):
        session = self.session
        print(kwargs)

        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance
        else:
            instance = model(**kwargs)
            session.add(instance)
            session.commit()
            return instance

if __name__ == '__main__':
    engine = get_engine()
    create_tables(engine)

    

