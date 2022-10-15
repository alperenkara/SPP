import os
import certifi 
from datetime import datetime, timedelta
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from typing import Optional, List, Dict, Any
import motor.motor_asyncio
import string
from random import choice
# mail imports
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from starlette.responses import JSONResponse
from starlette.requests import Request
from fastapi_mail import FastMail, MessageSchema,ConnectionConfig
from pydantic import BaseModel, EmailStr
from typing import List
import codecs
# Enviroment values are registered under .env file
from dotenv import dotenv_values

#credentials = dotenv_values(".env")


# Addding Cross Origin Resource Sharing
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Adding CORS URLs
origins = [
    
    'http://localhost:3000'
]

# Add Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)


# connecting to MongoDB with async motor driver
# client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"],tlsCAFile=certifi.where())
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ['MONGODB_URL'],tlsCAFile=certifi.where())
db = client.spp

print(db)
# FastAPI encodes and decodes data as JSON strings.
# BSON has support for additional non-JSON-native data types, including ObjectId which can't be directly encoded as JSON

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")
        
# MongoDB Model - 1
# Respose Model - Primary Model
class sppModel(BaseModel):
    # If you have an attribute on your model that starts with an underscore, Python will assume that it is a private variable
    # We name the field id but give it an alias of _id
    # We set this id value automatically to an ObjectId string, so you do not need to supply it when creating a customer record.
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    # hexnum=Field(default_factory:=secrets.token_hex(6))
    # print(hexnum)
    # print(id)
    customer_name: str = Field(...)
    # print(customer_name)
    customer_surname: str = Field(...)
    # print(customer_surname)
    email: EmailStr = Field(...)
    # print(email)
    spp_code: str = Field(...)
    
    date: str = Field(...)

    class Config:
        def HexGenerator(num):
            chars = string.digits
            random =  ''.join(choice(chars) for _ in range(num))
            return random
        spp_code = HexGenerator(num=4)
        print(spp_code)
        # keep in True for _id alias
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "customer_name": "ALPEREN",
                "customer_surname":"KARA",
                "email": "ALPEREN.KARA@example.com",
                "spp_code": "{}".format(HexGenerator(num=4)),
                "date":"123"
            }
        }

# MongoDB Model - 2
# it does not contain id attribute because it should not change.
# all fields are optional, you only need to supply the fields you wish to update. 
class UpdatesppModel(BaseModel):
    customer_name: Optional[str]
    #print(customer_name)
    customer_surname: Optional[str]
   #print(customer_surname)
    email: Optional[EmailStr]
    #print(email)
    spp_code: Optional[str]
    #print(spp_code)

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "customer_name": "ALPEREN",
                "customer_surname":"KARA",
                "email": "jdoe@example.com",
                "spp_code": "1234567",
                "date":"123"
            }
        }

  #  POST / - creates a new customer.
  #  GET / - view a list of all customers.
  #  GET /{id} - view a single customer.
  #  PUT /{id} - update a customer.
  #  DELETE /{id} - delete a customer.

@app.post("/", response_description="Add a new Anti-Phishing Code", response_model=sppModel)
async def new_email_record(customer: sppModel = Body(...)):
    # We have to decode this JSON request body into a Python dictionary before passing it to our MongoDB client.
    #customer_email = customer['email']
    customer = jsonable_encoder(customer)
    customer_email = customer['email']
    # Appending Random Six Digits and Date
    chars = string.digits
    random =  ''.join(choice(chars) for _ in range(4))
    customer.update(
        {'spp_code':random,
         'date': jsonable_encoder(datetime.today())
         })

    print(customer)
    # DB entry
    new_customer_record = await db["customers"].insert_one(customer)
    # Find new created customer
    created_email_record = await db["customers"].find_one(
        {
        "_id": new_customer_record.inserted_id,
        } )
    print(customer['email'])
    await simple_send([customer])
    # return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_email_record)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_email_record)

# road-1
@app.get(
    "/", response_description="List all customers", response_model=List[sppModel]
)
async def list_customers():
    # TODO: Fix hard coded number of customers.
    customers = await db["customers"].find().to_list(1000)
    return customers

# TODO: SPP Code Search will come here !
# road-2
@app.post("/{spp_code}", response_description="Verification of SPP Code", response_model=sppModel)
async def check_spp_code(email: EmailStr,spp_code: str):
    # print(type(email),type(spp_code))
    verified = False
    date = ''
    mode = 'email'

    if (customer := await db["customers"].find_one({"spp_code" : spp_code})) is not None:
        if (customer['email']==email) is not True:
            #return customer
            print('Customer Not Found')
            verified = False
        else: 
            verified = True
            date = customer['date']
            print("Code has been verified for {spp_code} and email: {email} date of {date}".format(spp_code = spp_code, email = email,date= date))
    else: 
        verified = False
        print("Simple Phishing Protection Code({spp_code}) has not been found".format(spp_code=spp_code))
    result = {'verified':verified,'date':date,'mode':mode}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=result)         

    # raise HTTPException(status_code=404, detail=f"Customer Email Record not found")

# road-3
@app.get(
    "/{id}", response_description="Get a single customer", response_model=sppModel
)
async def show_customer_record(id: str):
    if (customer := await db["customers"].find_one({"_id": id})) is not None:
        return customer

    raise HTTPException(status_code=404, detail=f"Customer Email Record {id} not found")

# Update the record
@app.put("/{id}", response_description="Update a customer", response_model=sppModel)
async def update_customer_record(id: str, customer: UpdatesppModel = Body(...)):
    # we iterate over all the items in the received dictionary and only add the items that have a value to our new document.
    customer = {k: v for k, v in customer.dict().items() if v is not None}

    if len(customer) >= 1:
        #  $set the new values
        update_result = await db["customers"].update_one({"_id": id}, {"$set": customer})

        if update_result.modified_count == 1:
            if (
                updated_customer_record := await db["customers"].find_one({"_id": id})
            ) is not None:
                return updated_customer_record

    if (existing_customer := await db["customers"].find_one({"_id": id})) is not None:
        return existing_customer

    raise HTTPException(status_code=404, detail=f"Customer Record {id} not found")


@app.delete("/{id}", response_description="Delete a customer")
async def delete_customer(id: str):
    delete_result = await db["customers"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Customer Record {id} not found")

class EmailSchema(BaseModel):
    email: List[EmailStr]
    body: Dict[str, Any]

# class EmailContent(BaseModel):
#      message: str = "test"
#      subject: str = "test"
#      spp_code: str = "test"

conf = ConnectionConfig(
    MAIL_USERNAME = os.environ['USERNAME'],
    MAIL_PASSWORD = os.environ['PASS'],
    MAIL_FROM = os.environ['EMAIL'],
    MAIL_PORT = 587,
    MAIL_SERVER = os.environ['SERVER_NAME'],
    MAIL_TLS = True,
    MAIL_SSL = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    TEMPLATE_FOLDER='./templates'
)


    #<p>{content.subject}</p>
    # <p>{content.message}</p>
@app.post('/email')
# async def send_email(email: EmailStr, content: EmailContent):
# async def simple_send(email: EmailSchema) -> JSONResponse: 


async def simple_send(customer: list) -> JSONResponse:    
    # email = await email.get(email = email)
    # spp = await spp_code.get(spp_code = spp_code)
    print("customer listesi",customer)
    print(type(customer))
    customer_email = [customer[0]['email']]
    print(customer_email)
    print("customer email type",type(customer_email))
    message = MessageSchema(
    subject=f"Mr {customer[0]['customer_surname']}, fraud - how to avoid being tricked in a click",
    recipients=customer_email,
    template_body = {'spp_code':customer[0]['spp_code']},
    subtype="html")
    
    print("Type of message",type(message))
    
    fm = FastMail(conf)
    await fm.send_message(message, template_name='hsbc_template.html')
    return JSONResponse(status_code=200, content={"message": "email has been sent"})
