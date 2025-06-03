# 使用轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir requests pypinyin croniter

# 复制脚本文件
COPY plexzh.py .
COPY entrypoint.sh .

# 修复换行符问题并设置权限
RUN apt-get update && apt-get install -y dos2unix && \
    dos2unix entrypoint.sh && \
    chmod +x entrypoint.sh && \
    rm -rf /var/lib/apt/lists/*

# 创建日志目录
RUN mkdir logs && chmod 777 logs

# 设置入口点
ENTRYPOINT ["./entrypoint.sh"]
