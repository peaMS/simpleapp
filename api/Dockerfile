FROM ubuntu:22.04

ENV PYTHONIOENCODING=utf-8

RUN apt-get update -y && apt-get install -y python3-pip

COPY . /app
WORKDIR /app
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
CMD ["sh", "-c", "python3 mysql_api.py"]

EXPOSE 8080
