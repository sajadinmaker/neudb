FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY neudb ./neudb
COPY neudb.py ./
RUN pip install --no-cache-dir ".[api]"
ENV NEUDB_API_DB=/data
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1
CMD ["uvicorn", "neudb.api:app", "--host", "0.0.0.0", "--port", "8000"]
