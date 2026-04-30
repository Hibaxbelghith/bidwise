# -------- BASE IMAGE --------
FROM python:3.12-slim

# -------- ENV --------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# -------- WORKDIR --------
WORKDIR /app

# -------- SYSTEM DEPENDENCIES --------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-unifont \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
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

# -------- PYTHON DEPENDENCIES --------
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# -------- APP CODE --------
COPY . .

# -------- NON-ROOT USER (SECURITY) --------
RUN useradd -m appuser
USER appuser

# -------- PORT --------
EXPOSE 8000

# -------- COMMAND --------
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]