# 使用多平台兼容的基础镜像
FROM --platform=$BUILDPLATFORM python:3.9-slim as builder

# 设置工作目录
WORKDIR /app

# 安装必要的工具（在构建阶段安装）
RUN apt-get update && \
    apt-get install -y dos2unix && \
    rm -rf /var/lib/apt/lists/*

# 复制应用程序文件
COPY plexzh.py .
COPY entrypoint.sh .

# 修复换行符问题并设置权限
RUN dos2unix entrypoint.sh && \
    chmod +x entrypoint.sh

# 安装 Python 依赖
RUN pip install --no-cache-dir requests pypinyin croniter

# 创建日志目录
RUN mkdir logs && chmod 777 logs

# 最终阶段使用多平台镜像
FROM python:3.9-slim

# 设置时区变量（默认为UTC）
ENV TZ=UTC

# 从构建阶段复制文件
COPY --from=builder /app /app

# 设置工作目录
WORKDIR /app

# 设置入口点
ENTRYPOINT ["./entrypoint.sh"]

ARG BUILD_VERSION="dev"
LABEL org.opencontainers.image.version=$BUILD_VERSION

# 设置镜像元数据
LABEL maintainer="zqs1qiwan@gmail.com"
LABEL org.opencontainers.image.source="https://github.com/zqs1qiwan/plexzh"
