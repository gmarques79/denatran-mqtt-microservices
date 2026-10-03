FROM python:3.12-slim

WORKDIR /app

COPY cliente/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ /app/common/
COPY services/ /app/services/
COPY cliente/ /app/cliente/
COPY tests/ /app/tests/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "cliente/main.py"]
