FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Playwright + Chromium (obligatoire pour scraping dans le container)
RUN python -m playwright install --with-deps chromium

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8501

CMD ["/app/entrypoint.sh"]
