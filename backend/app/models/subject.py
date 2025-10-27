from sqlalchemy import Column, DateTime, Integer, String, JSON, func
from sqlalchemy.orm import relationship

from app.database import Base


class Subject(Base):
    __tablename__ = "Subject"

    subjectId = Column(Integer, primary_key=True, index=True)
    subjectName = Column(String(50), nullable=False)
    tagIds = Column(JSON, comment='关联的标签ID列表')
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now())

    data_items = relationship("DataItem", back_populates="subject")
