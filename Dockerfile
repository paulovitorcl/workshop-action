FROM python:3.9-slim

WORKDIR /action

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

ENTRYPOINT ["python", "/action/main.py"]