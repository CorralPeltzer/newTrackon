FROM python:3.6-alpine

COPY requirements.txt /
RUN apk add --no-cache curl && pip install --no-cache-dir -r requirements.txt

COPY . /app/newTrackon
WORKDIR /app/newTrackon

EXPOSE 8080

ENTRYPOINT [ "python", "run.py" ]
