FROM python:3.14-alpine

COPY --chown=newtrackon:newtrackon . /app/newTrackon
WORKDIR /app/newTrackon
RUN apk add --no-cache curl && pip install --no-cache-dir .

VOLUME /app/newTrackon/data
RUN addgroup --system newtrackon && adduser -S -H -G newtrackon newtrackon
RUN mkdir -p /app/newTrackon/data && chown -R newtrackon:newtrackon /app/newTrackon/data
USER newtrackon

EXPOSE 8080

ENTRYPOINT [ "python", "run.py" ]
