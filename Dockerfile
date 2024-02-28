FROM python:3.9-bookworm

COPY src ./src
COPY .env .
COPY requirements.txt .

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN pip3 install -r requirements.txt
CMD python3 ./src/main.py