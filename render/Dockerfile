FROM node:20-slim AS node-base

# Python + sistem araçları
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    libgeos-dev libproj-dev proj-data \
    ffmpeg \
    chromium \
    fonts-liberation \
    curl wget \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# citygml-tools (CityGML ↔ CityJSON)
RUN curl -L https://github.com/citygml4j/citygml-tools/releases/download/v2.3.0/citygml-tools-2.3.0.zip \
    -o /tmp/citygml-tools.zip \
    && unzip /tmp/citygml-tools.zip -d /opt/ \
    && ln -s /opt/citygml-tools-2.3.0/citygml-tools /usr/local/bin/citygml-tools \
    && rm /tmp/citygml-tools.zip

WORKDIR /app

# Node bağımlılıkları
COPY package*.json ./
RUN npm install

# Python bağımlılıkları
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

EXPOSE 8001

CMD ["uvicorn", "src.pipeline:app", "--host", "0.0.0.0", "--port", "8001"]
