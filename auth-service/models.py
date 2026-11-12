'database models'
import datetime
from sqlalchemy import Column, Integer, String, DateTime,Boolean,ForeignKey
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class User(Base):
    'user object'
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50),  nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

class TokenTable(Base):
    'token object'
    __tablename__ = "tokens"
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token = Column(String(450), primary_key=True)
    refresh_token = Column(String(450),nullable=False)
    status = Column(Boolean)
    created_date = Column(DateTime, default=datetime.datetime.now)
