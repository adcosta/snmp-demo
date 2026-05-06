FROM python:3.11-slim

WORKDIR /app

# grpcio runtime + pygnmi (gives us the pre-compiled proto stubs)
RUN pip install --no-cache-dir grpcio pygnmi

COPY server.py .

EXPOSE 50051

CMD ["python", "server.py"]
