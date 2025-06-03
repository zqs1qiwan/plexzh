# Plex 媒体库中文首字母搜索优化工具 

https://hub.docker.com/r/zqs1qiwan/plexzh

## 特性

- **极简**: 简洁基础，无额外配置，新手友好
- 🚀 **自动排序改名**：把库中排序用标题替换为中文首字母，如“名侦探柯南”变为“MJTKN”方便遥控器首字母搜索
- 🕒 **cron 定时任务支持**：使用标准 cron 表达式配置任务计划
- 📅 **支持每小时/每天/每周运行**：例如 `0 * * * *` 表示每小时运行一次
- 🗑️ **智能日志管理**：自动轮转和清理旧日志

## 使用说明

### 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `PLEX_HOST` | `http://localhost:32400` | Plex 服务器地址 |
| `PLEX_TOKEN` | (无) | Plex 身份验证令牌 | 
| `CRON_SCHEDULE` | (空) | 定时任务表达式，如 `0 * * * *` 每小时运行 |
| `LOG_RETENTION_DAYS` | `7` | 日志保留天数 |
| `TZ` | (系统) | 时区设置，如 `Asia/Shanghai` |

Token获取方式参考官网 https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/

### 定时任务示例

每小时运行一次：
```bash
docker run -d \
  -e PLEX_HOST="http://192.168.2.1:32400" \
  -e PLEX_TOKEN="uGMVXF********zJ9" \
  -e CRON_SCHEDULE="0 * * * *" \
  -e LOG_RETENTION_DAYS=14 \
  -e TZ="Asia/Shanghai" \
  -v /path/to/config:/app/logs  \
  zqs1qiwan/plexzh:latest
