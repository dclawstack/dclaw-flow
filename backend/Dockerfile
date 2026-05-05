FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn[standard]

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8088

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
