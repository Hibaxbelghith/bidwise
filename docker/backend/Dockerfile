FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Required OS libs for Playwright Chromium used by JS-rendered scrapers.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		fonts-liberation \
		fonts-noto-color-emoji \
		fonts-unifont \
		libasound2t64 \
		libatk-bridge2.0-0t64 \
		libatk1.0-0t64 \
		libatspi2.0-0t64 \
		libcairo2 \
		libcups2t64 \
		libdbus-1-3 \
		libexpat1 \
		libgbm1 \
		libglib2.0-0t64 \
		libgtk-3-0t64 \
		libnspr4 \
		libnss3 \
		libpango-1.0-0 \
		libx11-6 \
		libxcb1 \
		libxcomposite1 \
		libxdamage1 \
		libxext6 \
		libxfixes3 \
		libxkbcommon0 \
		libxrandr2 \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
	&& pip install --no-cache-dir -r requirements.txt \
	&& python -m playwright install chromium

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]