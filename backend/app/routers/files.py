"""
File upload and download router for data items.
"""
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.models.data_item import DataItem
from app.schemas.data_item import DataItemCreate, DataItemRead

router = APIRouter(
    prefix="/files",
    tags=["files"],
    dependencies=[Depends(require_access_token)],
)

# Configure upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def save_uploaded_file(file: UploadFile, project_id: int, user_id: int) -> str:
    """
    Save uploaded file to disk and return the file path.
    
    Args:
        file: The uploaded file
        project_id: Project ID for organizing files
        user_id: User ID for organizing files
    
    Returns:
        Relative file path where the file was saved
    """
    # Create directory structure: uploads/{project_id}/{user_id}/
    project_dir = UPLOAD_DIR / str(project_id) / str(user_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename to avoid conflicts
    filename = file.filename or "unnamed_file"
    file_path = project_dir / filename
    
    # If file exists, append number to filename
    counter = 1
    while file_path.exists():
        name_parts = filename.rsplit(".", 1)
        if len(name_parts) == 2:
            new_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
        else:
            new_filename = f"{filename}_{counter}"
        file_path = project_dir / new_filename
        counter += 1
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    # Return relative path
    return str(file_path.relative_to(UPLOAD_DIR))


@router.post("/upload", response_model=DataItemRead, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    projectId: int = Form(...),
    name: Optional[str] = Form(None),
    subjectId: Optional[int] = Form(None),
    fileDescription: Optional[str] = Form(None),
    dataType: Optional[str] = Form(None),
    fileName: Optional[str] = Form(None),
    fileType: Optional[str] = Form(None),
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db),
):
    """
    Upload a data file and create a corresponding DataItem record.
    
    The file is saved to disk and metadata is stored in the database.
    """
    try:
        # Save file to disk
        relative_path = save_uploaded_file(file, projectId, current_user['userId'])
        
        # Determine file type if not provided
        if not fileType and file.filename:
            fileType = file.filename.rsplit(".", 1)[-1] if "." in file.filename else None
        
        # Create DataItem record
        data_item_data = DataItemCreate(
            name=name or fileName or file.filename or "Untitled",
            projectId=projectId,
            userId=current_user['userId'],
            subjectId=subjectId,
            fileDescription=fileDescription,
            filePath=relative_path,
            fileName=fileName or file.filename,
            fileType=fileType,
            dataType=dataType,
        )
        
        data_item = DataItem(**data_item_data.dict())
        db.add(data_item)
        db.commit()
        db.refresh(data_item)
        
        return data_item
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.get("/download/{data_item_id}")
async def download_file(
    data_item_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    Download a file associated with a data item.
    
    Returns the file as a downloadable attachment.
    """
    # Get data item
    data_item = db.query(DataItem).filter(DataItem.dataItemId == data_item_id).first()
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    
    # Check if file path exists
    if not data_item.filePath:
        raise HTTPException(status_code=404, detail="No file associated with this data item")
    
    # Construct full file path
    file_path = UPLOAD_DIR / data_item.filePath
    
    # Check if file exists on disk
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Return file
    return FileResponse(
        path=str(file_path),
        filename=data_item.fileName or data_item.name or "download",
        media_type="application/octet-stream",
    )
