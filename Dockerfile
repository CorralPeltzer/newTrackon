FROM python:3.10-alpine

COPY requirements.txt /
RUN apk add --no-cache curl && pip install --no-cache-dir -r requirements.txt

RUN addgroup --system newtrackon && adduser -S -H -G newtrackon newtrackon
USER newtrackon

COPY --chown=newtrackon:newtrackon . /app/newTrackon
VOLUME /app/newTrackon/data
WORKDIR /app/newTrackon

EXPOSE 8080

ENTRYPOINT [ "python", "run.py" ]
