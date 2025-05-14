FROM ubuntu:22.04

ENV PYTHONIOENCODING=utf-8

RUN apt-get update -y && apt-get install -y python3-pip python3-dev build-essential curl libssl-dev libpq-dev software-properties-common

COPY . /app
WORKDIR /app
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
CMD ["sh", "-c", "python3 sql_api.py"]

EXPOSE 8080
