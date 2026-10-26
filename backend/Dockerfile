# собирается из корня репозитория: нужны config/ (политика Аскара), models/pd (модель задачи 2) и mocks/companies (для тестов)
FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY config/ config/
COPY models/pd/ models/pd/
COPY mocks/companies/ mocks_companies/

EXPOSE 8000
CMD ["sh", "start.sh"]
