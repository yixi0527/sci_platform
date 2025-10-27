from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class LogEntry(Base):
    __tablename__ = "LogEntry"

    logId = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("User.userId", ondelete="SET NULL"))
    action = Column(String(100))
    detail = Column(JSON)
    createdAt = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="logs")
