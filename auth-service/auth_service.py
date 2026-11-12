"auth microservice"
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import FastAPI,Depends, HTTPException, status
from jose import jwt
import pika
import asyncio
import aio_pika
import scemas
import models
import auth_data
from auth_bearer import JWTBearer
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_engine(os.getenv('DB_HOST'))

session = Session(engine)
ALGORITHM = os.getenv('ALGORITHM')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_REFRESH_SECRET_KEY = os.getenv('JWT_REFRESH_SECRET_KEY')

app = FastAPI()

@app.on_event('startup')
async def startup():
    try:
        engine.connect()
    except Exception as err:
        logger.error("Ошибка подключения к базе данных", type(err))
    loop = asyncio.get_event_loop()
    connection = await aio_pika.connect("amqp://guest:guest@localhost/", loop = loop)
    channel = await connection.channel()
    queue = await channel.declare_queue("auth_check")
    logger.info("Ожидаются сообщения о проверки авторизации")
    await queue.consume(auth_request)
@app.post("/register")
async def register_user(user: scemas.UserCreate):
    'registering user'
    logger.info("Получен запрос на регистрацию")
    try:
        existing_user = session.query(models.User).filter_by(email=str(user.email)).first()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    if existing_user:
        logger.error("Пользователь с такой почтой уже существует")
        raise HTTPException(status_code=400, detail="Email already registered")

    encrypted_password =auth_data.get_hashed_password(user.password)

    new_user = models.User(username=user.username, email=user.email, password=encrypted_password )

    session.add(new_user)
    session.commit()
    logger.info("Пользователь успешно создан")
    return {"message":"user created successfully"}


@app.post('/login' ,response_model=scemas.TokenSchema)
async def login(request: scemas.requestdetails):
    'gives tokens to user'
    logger.info("Получен запрос на вход")
    try:
        user = session.query(models.User).filter(models.User.email == request.email).first()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    if user is None:
        logger.error("Пользователь не найден")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email")
    hashed_pass = user.password
    if not auth_data.verify_password(request.password, hashed_pass):
        logger.error("Пароль не подходит")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    access=auth_data.create_access_token(user.id)
    refresh = auth_data.create_refresh_token(user.id)
    token_db = models.TokenTable(user_id=user.id,  access_token=access,  refresh_token=refresh, status=True)
    session.add(token_db)
    try:
        session.commit()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    logger.info("Вход успешный")
    return {
        "access_token": access,
        "refresh_token": refresh,
    }

@app.post('/change-password')
async def change_password(request: scemas.changepassword):
    'changes password for user'
    logger.info("Получен запрос на смену пароля")
    try:
        user = session.query(models.User).filter(models.User.email == str(request.email)).first()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    if user is None:
        logger.error("Пользователь не найден")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
    if not auth_data.verify_password(request.old_password, user.password):
        logger.error("Пароль не подходит")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid old password")

    encrypted_password = auth_data.get_hashed_password(request.new_password)
    user.password = encrypted_password
    try:
        session.commit()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    logger.info("Пароль был изменен")
    return {"message": "Password changed successfully"}

@app.post('/logout')
async def logout(dependencies=Depends(JWTBearer())):
    'logout function'
    logger.info("Получен запрос на выход из системы")
    token=dependencies
    payload = jwt.decode(token, JWT_SECRET_KEY, ALGORITHM)
    user_id = payload['sub']
    try:
        token_record = session.query(models.TokenTable).all()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    info=[]
    for record in token_record :
        if (datetime.utcnow() - record.created_date).days >1:
            info.append(record.user_id)
    if info:
            try:
                existing_token = session.query(models.TokenTable).where(models.TokenTable.user_id.in_(info)).delete()
                session.commit()
            except Exception as err:
                logger.error("Произошла ошибка при запросе базе данных", type(err))
    try:
        existing_token = session.query(models.TokenTable).filter(models.TokenTable.user_id == user_id, models.TokenTable.access_token==token).first()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    if existing_token:
        existing_token.status=False
        session.add(existing_token)
        try:
            session.commit()
        except Exception as err:
            logger.error("Произошла ошибка при запросе базе данных", type(err))
    logger.info("Выход произведен успешно")
    return {"message":"Logout Successfully"}


async def auth_request(message: aio_pika.IncomingMessage):
    'takes requset from RabbitMQ'
    logger.info("Было получено сообщение")
    body = message.body.decode("utf-8")
    ch = message.channel
    props = message.properties
    delivery_tag = message.delivery_tag
    user_id = None
    try:
        logger.info(body)
        payload = jwt.decode(body,JWT_SECRET_KEY, ALGORITHM)
        user_id = payload['sub']
    except Exception:
        logger.error("Токен не является действующим")
    try:
        data= session.query(models.TokenTable).filter_by(user_id=user_id,access_token=body,status=True).first()
    except Exception as err:
        logger.error("Произошла ошибка при запросе базе данных", type(err))
    if data:
        ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(1))
        ch.basic_ack(delivery_tag=delivery_tag)
        logger.info("Отправлено сообщение об успешно авторизованном пользователе")
    else:
        ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(0))
        ch.basic_ack(delivery_tag=delivery_tag)
        logger.info("Отправленно сообщение о неавторизованном пользователе")
