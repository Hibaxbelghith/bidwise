FROM python:3.12-slim

# Empêcher Python de créer des fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Forcer l'affichage immédiat des logs
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Installer dépendances système minimales
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libexpat1 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    libcups2 \
    libdrm2 \
    libxshmfence1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    fonts-unifont \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances Python
COPY requirements.txt .

# Installer les dépendances
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN python -m playwright install chromium

# Copier le code du projet
COPY . .
