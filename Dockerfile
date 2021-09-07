FROM python:3.8.8 AS builder

WORKDIR /api
COPY ./requirements.txt /api/requirements.txt
COPY ./app_e3.py /api/app.py
COPY ./.env /api/.env

RUN pip install -r /api/requirements.txt

RUN apt-get update && apt-get install -y unzip curl \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-2.0.30.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install