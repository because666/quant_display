# Railway部署使用的Dockerfile - 简化版
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 只安装必要的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（使用预编译包避免编译）
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV PORT=8000

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
