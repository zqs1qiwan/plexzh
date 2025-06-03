#!/bin/bash
#!/bin/bash

# 设置默认日志保留天数（7天）
RETENTION_DAYS=${LOG_RETENTION_DAYS:-7}

# 确保日志目录存在
mkdir -p /app/logs

# 清理旧日志（超过指定天数）
find /app/logs -name "plexzh.log.*" -mtime +$RETENTION_DAYS -exec rm -f {} \;

# 执行主程序
exec python plexzh.py
