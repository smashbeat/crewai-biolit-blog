FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
# agents.yaml and tasks.yaml are already under src/, so no extra COPY needed
ENV PYTHONPATH=/app
CMD ["python", "-m", "src.main", "--pdf", "src/data/input/sample.pdf"]
