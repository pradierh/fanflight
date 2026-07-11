FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_ml.txt .

# torch CPU d'abord, depuis l'index CPU dédié (évite ~3 Go de paquets CUDA)
RUN pip install --no-cache-dir torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements_ml.txt

# Copie le code dans l'image (garde cette ligne)
COPY . .