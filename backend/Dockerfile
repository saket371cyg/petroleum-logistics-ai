FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["sh", "-c", "python data/synthetic/generate_data.py && python seed_db.py && python -m app.ml.train_demand_model && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
