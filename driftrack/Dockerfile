# driftrack/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . /app
ENV DRIFTRACK_HOST=0.0.0.0 \
    DRIFTRACK_PORT=8750 \
    DRIFTRACK_DATA=/data \
    PYTHONUNBUFFERED=1
RUN useradd -m driftrack && mkdir -p /data && chown driftrack /data
USER driftrack
VOLUME ["/data"]
EXPOSE 8750
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8750/api/health', timeout=4)" || exit 1
CMD ["python", "app.py"]
