FROM python:3.8.8-slim 

WORKDIR /api

COPY ./requirements.txt /api/requirements.txt
COPY ./app_e3.py /api/app.py
COPY ./d.env /api/d.env

RUN pip install -r /api/requirements.txt

EXPOSE 8000

CMD uvicorn app:app --reload --host 0.0.0.0