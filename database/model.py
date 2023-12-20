from sqlalchemy import Column, Integer, BigInteger, ForeignKey,String, Double, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CurrencyNames(Base):
    __tablename__ = 'currency_names'

    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String(20), unique=True)

class CurrencyValue(Base):
    __tablename__ = 'currency_value'
    id = Column(BigInteger, autoincrement=True, primary_key=True)
    name = Column(String, ForeignKey('currency_names.name'),nullable=False)
    price = Column(Double,nullable=False)
    datetime = Column(DateTime,nullable=None)

    currency_names = relationship(CurrencyNames, backref='currency_value', cascade='delete')
