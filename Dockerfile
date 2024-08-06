FROM python:3.11.9-slim
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    zlib1g-dev \
    openjdk-17-jdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN echo "setuptools<72" > /app/constraints.txt
ENV PIP_CONSTRAINT=/app/constraints.txt
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000 80