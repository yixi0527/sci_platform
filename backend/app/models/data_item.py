from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import relationship

from app.database import Base


class DataItem(Base):
    """
    DataItem model representing uploaded data files and their metadata.
    
    Stores information about data files including their location, type, 
    and associations with projects, subjects, and users.
    """
    __tablename__ = "DataItem"

    dataItemId = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="Data item name")
    userId = Column(Integer, ForeignKey("User.userId", ondelete="SET NULL"), comment="Creator user ID")
    projectId = Column(Integer, ForeignKey("Project.projectId", ondelete="CASCADE"), nullable=False, comment="Associated project ID")
    subjectId = Column(Integer, ForeignKey("Subject.subjectId", ondelete="SET NULL"), comment="Associated subject ID (optional)")
    tagIds = Column(JSON, comment='关联的标签ID列表')
    
    # File metadata
    fileDescription = Column(Text, comment="Description of the file")
    filePath = Column(String(500), comment="Relative path to the file on server")
    fileName = Column(String(255), comment="Original file name")
    fileType = Column(String(50), comment="File type/extension (e.g., edf, csv, json)")
    dataType = Column(String(50), comment="Data category: raw, processed, or result")
    
    # Timestamps
    createdAt = Column(DateTime, server_default=func.now(), comment="Creation timestamp")
    updatedAt = Column(DateTime, server_default=func.now(), comment="Last update timestamp")

    # Relationships
    owner = relationship("User", back_populates="data_items")
    project = relationship("Project", back_populates="data_items")
    subject = relationship("Subject", back_populates="data_items")
