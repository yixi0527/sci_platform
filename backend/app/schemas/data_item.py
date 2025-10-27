from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class DataItemBase(BaseModel):
    """Base schema for DataItem with field aliases for backward compatibility."""
    name: str = Field(..., description="Data item name")
    projectId: int = Field(..., description="Project ID")
    userId: Optional[int] = Field(None, description="User ID who created this item")
    subjectId: Optional[int] = Field(None, description="Subject ID if applicable")
    tagIds: Optional[List[int]] = Field(None, description="Tag IDs list if applicable")
    fileDescription: Optional[str] = Field(None, description="File description")
    filePath: Optional[str] = Field(None, description="File path on server")
    fileName: Optional[str] = Field(None, description="Original file name")
    fileType: Optional[str] = Field(None, description="File type/extension")
    dataType: Optional[str] = Field(None, description="Data type: raw, processed, or result")

    @validator('dataType')
    def validate_data_type(cls, v):
        """Validate dataType is one of the allowed values."""
        if v is not None and v not in ['raw', 'processed', 'result']:
            raise ValueError('dataType must be one of: raw, processed, result')
        return v


class DataItemCreate(DataItemBase):
    """Schema for creating a new DataItem."""
    userId: Optional[int] = None  # Will be set from current user if not provided
    tagIds: Optional[List[int]] = None


class DataItemUpdate(BaseModel):
    """Schema for updating an existing DataItem. All fields are optional."""
    name: Optional[str] = None
    projectId: Optional[int] = None
    userId: Optional[int] = None
    subjectId: Optional[int] = None
    tagIds: Optional[List[int]] = None
    fileDescription: Optional[str] = None
    filePath: Optional[str] = None
    fileName: Optional[str] = None
    fileType: Optional[str] = None
    dataType: Optional[str] = None

    @validator('dataType')
    def validate_data_type(cls, v):
        """Validate dataType is one of the allowed values."""
        if v is not None and v not in ['raw', 'processed', 'result']:
            raise ValueError('dataType must be one of: raw, processed, result')
        return v


class DataItemRead(DataItemBase):
    """Schema for reading DataItem with all fields including timestamps."""
    dataItemId: int
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True
        # Allow population by field name or alias
        allow_population_by_field_name = True
