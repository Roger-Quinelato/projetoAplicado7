FROM node:24-alpine AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY --from=frontend /web/dist ./web/dist
ENV PYTHONPATH=/app/src
CMD ["sh", "-c", "uvicorn archcorp.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
