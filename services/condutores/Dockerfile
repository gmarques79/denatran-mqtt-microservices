FROM python:3.12-slim

WORKDIR /app

COPY services/condutores/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ /app/common/
COPY services/condutores/ /app/services/condutores/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "services/condutores/main.py"]
