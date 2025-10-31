"""
应用常量配置
"""

# 文件上传限制
MAX_FILE_SIZE_MB = 500  # 最大文件大小（MB）
ALLOWED_FILE_EXTENSIONS = {
    'csv', 'edf', 'json', 'txt',
    'png', 'jpg', 'jpeg', 'pdf'
}

# 数据分页
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# JWT 配置
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 小时

# CSV 预览限制
CSV_PREVIEW_MAX_ROWS = 100
CSV_PREVIEW_DEFAULT_ROWS = 50

# 任务管理
JOB_CLEANUP_AGE_HOURS = 24  # 任务保留时间（小时）
JOB_POLL_INTERVAL_SECONDS = 2  # 前端轮询间隔建议值

# 数据库连接池
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_RECYCLE = 3600  # 1 小时

# 响应格式
SUCCESS_CODE = 0
ERROR_CODE_FIELD = "code"
DATA_FIELD = "data"
MESSAGE_FIELD = "message"

# 用户角色
ROLE_ADMIN = "admin"
ROLE_RESEARCHER = "researcher"
ROLE_VIEWER = "viewer"
DEFAULT_ROLE = ROLE_RESEARCHER

# 数据类型
DATA_TYPE_RAW = "raw"
DATA_TYPE_PROCESSED = "processed"
DATA_TYPE_RESULT = "result"

# 文件类型
FILE_TYPE_FLUORESCENCE = "fluorescence"
FILE_TYPE_LABEL = "label"
FILE_TYPE_BEHAVIOR = "behavior"
