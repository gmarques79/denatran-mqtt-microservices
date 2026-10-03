FROM python:3.12-slim

WORKDIR /app

COPY services/veiculos/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ /app/common/
COPY services/veiculos/ /app/services/veiculos/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "services/veiculos/main.py"]
