FROM python:3.10-slim

LABEL org.opencontainers.image.title="医院WAF管理系统"
LABEL org.opencontainers.image.version="1.0.0"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8083

CMD ["python", "app.py"]
