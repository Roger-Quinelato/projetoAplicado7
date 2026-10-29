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
# Usuário sem privilégios; /app fica gravável para o SQLite padrão quando DATABASE_URL não é informada.
RUN useradd --system --uid 10001 --home-dir /app archcorp && chown -R archcorp /app
USER archcorp
CMD ["sh", "-c", "uvicorn archcorp.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
