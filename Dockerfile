FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    GOOGLE_GENAI_USE_VERTEXAI=True \
    GOOGLE_CLOUD_LOCATION=global

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY cymbal_claims_agent ./cymbal_claims_agent
COPY data ./data
COPY skills ./skills
COPY AGENTS.md run_experiment.py ./

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "cymbal_claims_agent.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
