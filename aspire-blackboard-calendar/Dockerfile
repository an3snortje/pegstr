FROM python:3.12-slim

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/

VOLUME ["/srv/app/data"]
CMD ["python", "-m", "app.main", "--interval", "60"]
