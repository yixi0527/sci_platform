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


def save_uploaded_file(file: UploadFile, project_id: int, user_id: int, relative_path: Optional[str] = None) -> str:
    """
    Save uploaded file to disk and return the file path.
    
    Args:
        file: The uploaded file
        project_id: Project ID for organizing files
        user_id: User ID for organizing files
        relative_path: Optional relative path to preserve folder structure
    
    Returns:
        Relative file path where the file was saved
    """
    # Create base directory structure: uploads/{project_id}/{user_id}/
    base_dir = UPLOAD_DIR / str(project_id) / str(user_id)
    
    # If relative path is provided, use it to preserve folder structure
    if relative_path:
        # Use the full relative path including subdirectories
        full_path = base_dir / relative_path
        # Create all parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = full_path
    else:
        # Original behavior: save directly in base directory
        base_dir.mkdir(parents=True, exist_ok=True)
        filename = file.filename or "unnamed_file"
        file_path = base_dir / filename
        
        # If file exists, append number to filename
        counter = 1
        while file_path.exists():
            name_parts = filename.rsplit(".", 1)
            if len(name_parts) == 2:
                new_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_filename = f"{filename}_{counter}"
            file_path = base_dir / new_filename
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
        
        data_item = DataItem(**data_item_data.model_dump())
        db.add(data_item)
        db.commit()
        db.refresh(data_item)
        
        return data_item
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/upload-folder", response_model=dict, status_code=201)
async def upload_folder(
    files: list[UploadFile] = File(...),
    projectId: int = Form(...),
    relativePaths: Optional[str] = Form(None),  # JSON string of relative paths
    current_user: dict = Depends(require_access_token),
    db: Session = Depends(get_db),
):
    """
    Upload multiple files with folder structure preservation.
    Automatically generates tags based on directory hierarchy.
    
    Args:
        files: List of files to upload
        projectId: Project ID
        relativePaths: JSON string mapping file indices to relative paths
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Summary of uploaded files and generated tags
    """
    import json
    from app.models.tag import Tag, EntityType
    from app.services import tag_service
    
    try:
        # Parse relative paths if provided
        path_mapping = {}
        if relativePaths:
            path_mapping = json.loads(relativePaths)
        
        uploaded_items = []
        tag_map = {}  # {tag_name: tag_id}
        
        for idx, file in enumerate(files):
            # Get relative path for this file
            rel_path = path_mapping.get(str(idx), file.filename or f"file_{idx}")
            
            # Parse directory structure for tags
            path_parts = Path(rel_path).parts
            directory_tags = []
            
            # Extract tags from directory structure (exclude filename)
            if len(path_parts) > 1:
                for part in path_parts[:-1]:  # Exclude the filename
                    if part and part != '.':
                        directory_tags.append(part)
            
            # Save file with relative path to preserve folder structure
            relative_file_path = save_uploaded_file(file, projectId, current_user['userId'], rel_path)
            
            # Get or create tags
            tag_ids = []
            for tag_name in directory_tags:
                if tag_name not in tag_map:
                    # Check if tag exists
                    existing_tag = db.query(Tag).filter(
                        Tag.tagName == tag_name,
                        Tag.entityType == EntityType.DATAITEM,
                        Tag.userId == current_user['userId']
                    ).first()
                    
                    if existing_tag:
                        tag_map[tag_name] = existing_tag.tagId
                    else:
                        # Create new tag
                        new_tag = Tag(
                            tagName=tag_name,
                            tagDescription=f"Auto-generated from folder structure",
                            entityType=EntityType.DATAITEM,
                            userId=current_user['userId']
                        )
                        db.add(new_tag)
                        db.flush()
                        tag_map[tag_name] = new_tag.tagId
                
                tag_ids.append(tag_map[tag_name])
            
            # Determine file type
            file_type = None
            filename = file.filename or f"file_{idx}"
            if '.' in filename:
                file_type = filename.rsplit('.', 1)[-1]
            
            # Determine data type based on filename patterns
            data_type = "raw"
            filename_lower = filename.lower()
            if 'processed' in filename_lower or 'filtered' in filename_lower:
                data_type = "processed"
            elif 'result' in filename_lower or 'output' in filename_lower:
                data_type = "result"
            
            # Determine file category for fluorescence analysis
            file_category = None
            if 'top' in filename_lower or 'label' in filename_lower or 'behavior' in filename_lower:
                file_category = 'label'
            elif any(col in filename_lower for col in ['ch1', 'ch2', 'fluorescence', '410', '470']):
                file_category = 'fluorescence'
            
            # Create DataItem record
            data_item = DataItem(
                name=filename,
                projectId=projectId,
                userId=current_user['userId'],
                fileDescription=f"Uploaded from folder: {rel_path}",
                filePath=relative_file_path,
                fileName=filename,
                fileType=file_type,
                dataType=data_type,
                tagIds=tag_ids if tag_ids else None
            )
            db.add(data_item)
            db.flush()
            
            uploaded_items.append({
                'dataItemId': data_item.dataItemId,
                'name': data_item.name,
                'relativePath': rel_path,
                'tags': directory_tags,
                'tagIds': tag_ids,
                'fileCategory': file_category
            })
        
        db.commit()
        
        return {
            'success': True,
            'uploadedCount': len(uploaded_items),
            'items': uploaded_items,
            'generatedTags': list(tag_map.keys())
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Folder upload failed: {str(e)}")


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
