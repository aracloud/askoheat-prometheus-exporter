FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py .

ENV ASKOHEAT_URL=http://192.168.3.13/_gethome.json

EXPOSE 9105

CMD ["python", "exporter.py"]
