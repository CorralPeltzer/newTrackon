FROM python:3.6

COPY requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/newTrackon
WORKDIR /app/newTrackon

EXPOSE 8080

ENTRYPOINT [ "python", "run.py" ]
