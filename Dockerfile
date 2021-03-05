FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
COPY config.json config.json
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "main.py"]