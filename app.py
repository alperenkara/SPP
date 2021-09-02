import os
import certifi 
from datetime import datetime, timedelta
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio
import secrets

app = FastAPI()
# connecting to MongoDB with async motor driver
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"],tlsCAFile=certifi.where())

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
    # We set this id value automatically to an ObjectId string, so you do not need to supply it when creating a new student.
    
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

    class Config:
        def HexGenerator(num):
            return secrets.token_hex(num)
        spp_code = HexGenerator(num=6)
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
                "spp_code": "{}".format(HexGenerator(num=6)),
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
    spp_code: Optional[int]
    #print(spp_code)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "customer_name": "ALPEREN",
                "customer_surname":"KARA",
                "email": "jdoe@example.com",
                "spp_code": "1234567",
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
    customer = jsonable_encoder(customer)
    # Appending Random Six Digits and Date
    customer.update(
        {'spp_code':secrets.token_hex(6),
         'Date': jsonable_encoder(datetime.today())
         })

    print(customer)
    # DB entry
    new_customer_record = await db["customers"].insert_one(customer)
    # Find new created customer
    created_email_record = await db["customers"].find_one(
        {
        "_id": new_customer_record.inserted_id,
        } )
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
