FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY demo_agent.py knowledge_agent.py model_config.json web_server.py ./
COPY web/ web/
COPY sample_docs/ sample_docs/

EXPOSE 8000
CMD ["python", "web_server.py", "--host", "0.0.0.0", "--port", "8000"]
