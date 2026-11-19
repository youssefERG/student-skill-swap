FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p /app/instance

EXPOSE 5000

CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]