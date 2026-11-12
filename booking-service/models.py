'database models'
from sqlalchemy import Column, Integer, String, DateTime,Boolean,create_engine, ForeignKey
from sqlalchemy.orm import declarative_base

engine = create_engine('postgresql://postgres:1234@localhost/Booking')
engine.connect()

Base = declarative_base()



class Flight(Base):
    'flight object'
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250),nullable=False)
    destination = Column(String(250),nullable=False)
    start = Column(String(250),nullable=False)
    date = Column(DateTime,nullable=False)
    seats = Column(Integer,nullable=False)

class Passenger(Base):
    'passenger object'
    __tablename__ = "passengers"
    id= Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(450),nullable=False)
    surname = Column(String(450),nullable=False)
    passport_data= Column(Integer,nullable=False)

class Payment(Base):
    'payment object'
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer,ForeignKey("bookings.id"),nullable=False)
    payment_credentials = Column(String(450),nullable=False)
    date =Column(DateTime,nullable=False)

class Booking_Passangers(Base):
    'booking object'
    __tablename__ = "bookings-passangers"
    booking_id = Column(Integer, ForeignKey("bookings.id"),primary_key=True,nullable=False)
    passenger_id = Column(Integer, ForeignKey("passengers.id"),nullable=False)
    

class Booking(Base):
    'booking object'
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flights.id"),nullable=False)
    place = Column(Integer,nullable=False)

Base.metadata.create_all(engine)