## ===== Base image =====
#FROM python:3.10-slim
#
## ===== System deps =====
## - cron: để sau này bạn muốn chạy schedule trong container
## - lib* : một số lib hay cần cho TF / chạy headless
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    curl \
#    cron \
#    libglib2.0-0 \
#    libsm6 \
#    libxext6 \
#    libxrender-dev \
#    && rm -rf /var/lib/apt/lists/*
#
## ===== Workdir =====
#WORKDIR /app
#
## ===== Copy requirements trước để cache =====
#COPY requirements.txt .
#
## Khuyến nghị: nâng pip
#RUN pip install --no-cache-dir --upgrade pip \
#    && pip install --no-cache-dir -r requirements.txt
#
## ===== Copy source code cần chạy =====
#COPY app ./app
#COPY run.py .
#COPY run_cron.py .
#
## ===== Expose Flask port =====
#EXPOSE 5000
#
## ===== Start Flask =====
#CMD ["python", "run.py"]
FROM python:3.10-slim

# System deps (tensorflow + some libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .

EXPOSE 5000
CMD ["python", "run.py"]
