from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Validate required environment variables
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise RuntimeError(
        "Database configuration incomplete. Required environment variables: "
        "DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME"
    )

# 先连接 MySQL 不指定数据库，用于创建数据库
engine_tmp = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/",
    echo=False,  # 减少日志输出
    future=True
)

try:
    with engine_tmp.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
        conn.commit()
finally:
    engine_tmp.dispose()

# 正式连接指定数据库，配置连接池
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # 生产环境关闭 SQL 日志
    future=True,
    pool_pre_ping=True,  # 连接前检查连接有效性
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 超出 pool_size 时最多创建的连接数
    pool_recycle=3600,  # 1小时后回收连接，防止 MySQL 超时
    pool_timeout=30,  # 获取连接的超时时间
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
