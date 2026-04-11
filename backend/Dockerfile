# Railway部署使用的Dockerfile - 前后端一体化部署

# ==================== 阶段1: 构建前端 ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

COPY frontend/ .
RUN npm run build

# ==================== 阶段2: 后端 + 前端静态文件托管 ====================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# 从前端构建阶段复制产物到后端静态目录
COPY --from=frontend-builder /app/frontend/dist /app/static

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["python", "start.py"]
