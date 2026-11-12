"booking microservice"
import os
from dotenv import load_dotenv
import logging
import uuid
import pika
from sqlalchemy import create_engine,delete
from sqlalchemy.orm import Session
from fastapi import FastAPI,HTTPException,status,Header
import models
import scemas
load_dotenv()


engine = create_engine(os.getenv("DB_HOST"))
session = Session(engine)

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def startup():
    'occures on app startup'
    try:
        engine.connect()
    except Exception as err:
        logger.error("Проблема с подключением к базе данных", type(err))

class AuthClient(object):
    "Class calls to auth service"
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)
        self.response:bool = None
        self.corr_id = None
    async def call(self, token):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='auth_check',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=str(token))
        logger.info("Отправленно сообщение сервису авторизации")
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response
    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            logger.info("Получен ответ")
            self.response = bool(body)
check_auth = AuthClient()


@app.post('/book')
async def book_seat(request: scemas.FlightBooking,authorization = Header(None)):
    'books seat'
    logger.info("запрос на бронирование места")
    if check_auth.call(authorization):
        try:
            existing_booking = session.query(models.Booking).filter_by(flight_id =request.flight_id, place = request.seatnumber).first()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        if existing_booking:
            logger.error("Место уже зарезервированно")
            raise HTTPException(status_code=status.HTTP_226_IM_USED, detail="seat already registered")
        try:
            flight = session.query(models.Flight).filter_by(id = request.flight_id).first()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        if flight is None:
            logger.error("Не найден соответствующий полет")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="flight is not found")
        try:
            new_booking = models.Booking(flight_id=request.flight_id,seat=request.seatnumber)
            session.add(new_booking)
            session.commit()
            booking_id = session.query(models.Booking).filter_by(flight_id=request.flight_id,seat=request.seatnumber).first().id
            for name in request.name:
                i = request.name.index(name)
                new_passanger = models.Passenger(name=name,surname=request.surname[i],passport_data=request.passport_data[i])
                session.add(new_passanger)
                passanger = session.query(models.Passenger).filter_by(name=name,surname=request.surname[i],passport_data=request.passport_data[i]).first()
                new_booking_passanger = models.Booking_Passangers(id = booking_id, passanger_id = passanger.id)
                session.add(new_booking_passanger)
                session.commit()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        logger.info("Место зарезервированно")
        return {"message": "Seats booked succecfully"}
    else: 
        logger.info("отказано в доступе")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="user not authorized")

@app.delete('/book')
async def delete_booking(request: scemas.FlightBooking, authorization = Header(None)):
    'deletes booking from database'
    logger.info("Плучен запрос на удаление брони")
    if check_auth.call(authorization):
        try:
            existing_booking = session.query(models.Booking).filter_by(flight_id =request.flight_id, place = request.seatnumber).first()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        if not existing_booking:
            logger.error("Не найдена бронь")
            raise HTTPException(status_code=404, detail="booking not found")
        try:
            flight = session.query(models.Flight).filter(id = request.flight_id).first() 
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        if flight is None:
            logger.error("Не найден рейс")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="flight is not found")
        try:
            booking_id = session.query(models.Booking).filter_by(flight_id=request.flight_id,seat=request.seatnumber).first().id
            session.execute(delete(models.Booking_Passangers).where(models.Booking_Passangers.booking_id == booking_id ))
            session.commit()
            for name in request.name:
                i = request.name.index(name)
                passanger_id = session.query(models.Passenger).filter_by(name=name,surname=request.surname[i],passport_data=request.passport_data[i]).first().id
                session.delete(models.Passenger,passanger_id)
                session.commit()
            session.delete(models.Booking,booking_id)
            session.commit()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        logger.info("Бронь удалена")
        return {"message": "booking deleted succecfully"}
    else: 
        logger.info("отказано в доступе")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="user not authorized")
@app.get("/search")
async def search_articles( destination: str, start: str, date: str, authorization = Header(None)):
    'returns all flights by their destination, date'
    if check_auth.call(authorization):
        try:
            results = session.query(models.Flight).filter_by(destination=destination, start = start, date=date)
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        if not results:
            logger.error("Не найдено ни одного рейса")
            raise HTTPException(status_code=404, detail="No flights found")
        return results
    else: 
        logger.info("отказано в доступе")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="user not authorized")
@app.post("/payment")
async def payment(request: scemas.Payment, authorization=Header(None)):
    'adds payment data to DB'
    logger.info("Получен запрос на внесение данных оплаты")
    if check_auth.call(authorization):
        try:
            existing_booking = session.query(models.Passenger).filter_by(id=request.booking_id).first()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        if not existing_booking:
            logger.error("Бронь не найден")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="booking not found")
        try:
            new_payment = models.Payment(booking_id= request.booking_id,payment_credentials=request.payment_credentials,date=request.date)
            session.add(new_payment)
            session.commit()
        except Exception as err:
            logger.error("Проблема с запросом базе данных", type(err))
        logger.info("Платеж внесен")
        return {"message":"Payment completed"}
    else: 
        logger.info("отказано в доступе")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="user not authorized")
