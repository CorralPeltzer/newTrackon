FROM python:3.9.1-alpine

COPY requirements.txt /
RUN apk add --no-cache curl && pip install --no-cache-dir -r requirements.txt

COPY . /app/newTrackon
VOLUME /app/newTrackon/data
WORKDIR /app/newTrackon

EXPOSE 8080

ENTRYPOINT [ "python", "run.py" ]
