FROM python:3.12-slim

# Install git (needed for cloning PRs)
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY drift_bot/ drift_bot/

EXPOSE 8000

CMD ["python", "-m", "drift_bot.main"]
