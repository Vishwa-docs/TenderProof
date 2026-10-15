FROM node:22-alpine AS frontend
WORKDIR /web
COPY track_2b/src/web/package*.json ./
RUN npm ci
COPY track_2b/src/web/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/track_2b/src RUNTIME_DIR=/data
WORKDIR /app
COPY requirements.lock.txt requirements-documents.lock.txt ./
RUN pip install --no-cache-dir -r requirements-documents.lock.txt
COPY scripts/prefetch_documents.py ./scripts/prefetch_documents.py
ENV HF_HUB_DISABLE_XET=1 HF_HUB_DOWNLOAD_TIMEOUT=60
RUN python scripts/prefetch_documents.py /opt/docling
ENV DOCLING_ARTIFACTS_PATH=/opt/docling HF_HUB_OFFLINE=1
COPY track_2b/src/tenderproof ./track_2b/src/tenderproof
COPY --from=frontend /web/dist ./track_2b/src/web/dist
RUN useradd --uid 10001 --create-home tenderproof && mkdir /data && chown tenderproof /data
USER tenderproof
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "tenderproof.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
