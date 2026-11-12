'scemas for ease of use'
import datetime
from pydantic import BaseModel

class UserCreate(BaseModel):
    'for register'
    username: str
    email: str
    password: str

class requestdetails(BaseModel):
    'for login'
    email:str
    password:str

class TokenSchema(BaseModel):
    'jwttokens'
    access_token: str
    refresh_token: str

class changepassword(BaseModel):
    'changing password'
    email:str
    old_password:str
    new_password:str

class TokenCreate(BaseModel):
    'creation of jwttoken'
    user_id:str
    access_token:str
    refresh_token:str
    status:bool
    created_date:datetime.datetime

