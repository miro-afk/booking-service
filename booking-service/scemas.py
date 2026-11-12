'scemas for ease of use'
from pydantic import BaseModel

class FlightBooking(BaseModel):
    'for booking flights'
    flight_id:int
    seatnumber:int
    name:list
    surname:list
    passport_data:list

class Search(BaseModel):
    'scema for search'
    destination: str = None
    start: str = None
    date: str = None
    
class Payment(BaseModel):
    'scema for saving payment credentials'
    booking_id:int
    payment_credentials:str
    date:str
