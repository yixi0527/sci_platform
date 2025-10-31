"""
荧光分析路由
提供 CSV 预览、分析提交、进度查询、结果获取、行为映射等接口
"""
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.models.data_item import DataItem
from app.models.project import Project
from app.schemas.fluorescence import (
    PreviewRequest,
    PreviewResponse,
    AnalyzeRequest,
    JobCreateResponse,
    JobStatusResponse,
    ResultResponse,
    LabelMapRequest,
    LabelMapResponse,
)
from app.utils.csv_reader import preview_csv
from app.services import fluorescence_service
from app.services import project_service


router = APIRouter(
    prefix="/fluorescence",
    tags=["fluorescence"],
    dependencies=[Depends(require_access_token)],
)


def verify_project_access(
    project_id: int,
    db: Session,
    current_user: dict = Depends(require_access_token)
) -> Project:
    """
    验证项目访问权限
    """
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 检查当前用户是否为项目成员（或管理员可访问所有项目）
    from app.utils.roles import deserialize_roles
    user_roles = deserialize_roles(current_user.get("roles", "[]"))
    
    # 管理员可以访问所有项目
    if "admin" in user_roles:
        return project
    
    # 检查是否为项目成员
    from app.models.project import UserProject
    is_member = db.query(UserProject).filter(
        UserProject.projectId == project_id,
        UserProject.userId == current_user["id"]
    ).first()
    
    if not is_member:
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    
    return project


def verify_data_item_access(data_item_id: int, project_id: int, db: Session) -> DataItem:
    """
    验证数据项访问权限
    """
    data_item = db.query(DataItem).filter(DataItem.id == data_item_id).first()
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    
    if data_item.projectId != project_id:
        raise HTTPException(status_code=403, detail="Data item does not belong to this project")
    
    return data_item


@router.post("/preview", response_model=PreviewResponse)
def preview_fluorescence_csv(
    request: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    预览 CSV 文件的前 N 行
    
    Args:
        request: 预览请求
    
    Returns:
        PreviewResponse: 列名与数据行
    
    Raises:
        404: 数据项不存在
        422: CSV 解析失败
    """
    # 获取数据项
    data_item = db.query(DataItem).filter(DataItem.dataItemId == request.dataItemId).first()
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    
    # 验证项目访问权限
    if data_item.projectId:
        verify_project_access(data_item.projectId, db, current_user)
    
    # 读取 CSV
    try:
        import os
        file_path = os.path.join("uploads", data_item.filePath)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="CSV file not found on disk")
            
        result = preview_csv(file_path, max_rows=request.maxRows)
        return PreviewResponse(
            dataItemId=request.dataItemId,
            columns=result["columns"],
            rows=result["rows"],
            totalRows=result["total_rows"]
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="CSV file not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"CSV parsing failed: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/projects/{project_id}/analyze", response_model=JobCreateResponse)
def submit_analysis(
    project_id: int,
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    提交荧光分析任务
    
    Args:
        project_id: 项目 ID
        request: 分析请求
        background_tasks: 后台任务
    
    Returns:
        JobCreateResponse: 任务 ID 与状态
    
    Raises:
        404: 项目不存在
        400: 参数不合法
    """
    # 验证项目访问权限
    verify_project_access(project_id, db, current_user)
    
    # 验证请求参数
    if request.mode == 'single':
        if not request.events or not request.baselineWindow or not request.responseWindow:
            raise HTTPException(
                status_code=400,
                detail="Single mode requires events, baselineWindow, and responseWindow"
            )
        if not request.events:
            raise HTTPException(status_code=400, detail="Single mode requires at least one event")
    elif request.mode == 'multi':
        if not request.groups:
            raise HTTPException(status_code=400, detail="Multi mode requires groups")
        if len(request.groups) == 0:
            raise HTTPException(status_code=400, detail="Multi mode requires at least one group")
    
    # 验证数据选择
    if not request.selection.dataItemIds and not request.selection.tagFilter:
        raise HTTPException(status_code=400, detail="Must provide dataItemIds or tagFilter")
    
    if request.selection.dataItemIds and len(request.selection.dataItemIds) == 0:
        raise HTTPException(status_code=400, detail="dataItemIds cannot be empty")
    
    # 验证列映射
    if not request.columnMap.behavior or not request.columnMap.start:
        raise HTTPException(status_code=400, detail="columnMap must include behavior and start fields")
    
    # 创建任务
    try:
        response = fluorescence_service.create_analysis_job(db, project_id, request)
        
        # 提交后台执行
        background_tasks.add_task(
            fluorescence_service.execute_analysis,
            db,
            project_id,
            response.jobId,
            request
        )
        
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create analysis job: {str(e)}")


@router.get("/projects/{project_id}/jobs", response_model=List[JobStatusResponse])
def list_jobs(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    获取项目的所有分析任务列表
    
    Args:
        project_id: 项目 ID
        skip: 分页偏移
        limit: 返回数量
    
    Returns:
        List[JobStatusResponse]: 任务状态列表
    """
    # 验证项目访问权限
    verify_project_access(project_id, db, current_user)
    
    # 获取任务列表
    jobs = fluorescence_service.list_project_jobs(project_id, skip=skip, limit=limit)
    return jobs


@router.get("/projects/{project_id}/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    project_id: int,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    查询任务状态与进度
    
    Args:
        project_id: 项目 ID
        job_id: 任务 ID
    
    Returns:
        JobStatusResponse: 任务状态
    
    Raises:
        404: 任务不存在
    """
    # 验证项目访问权限
    verify_project_access(project_id, db, current_user)
    
    # 获取任务状态
    status = fluorescence_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # 验证任务属于该项目
    if status.projectId != project_id:
        raise HTTPException(status_code=403, detail="Job does not belong to this project")
    
    return status


@router.get("/projects/{project_id}/jobs/{job_id}/results", response_model=ResultResponse)
def get_job_results(
    project_id: int,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    获取任务结果
    
    Args:
        project_id: 项目 ID
        job_id: 任务 ID
    
    Returns:
        ResultResponse: 分析结果
    
    Raises:
        404: 任务不存在或结果未生成
        400: 任务尚未完成
    """
    # 验证项目访问权限
    verify_project_access(project_id, db, current_user)
    
    # 检查任务状态
    status = fluorescence_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if status.projectId != project_id:
        raise HTTPException(status_code=403, detail="Job does not belong to this project")
    
    if status.status != "succeeded":
        raise HTTPException(
            status_code=400,
            detail=f"Job has not completed successfully. Current status: {status.status}"
        )
    
    # 获取结果
    result = fluorescence_service.get_job_result(project_id, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job result not found")
    
    return result


@router.post("/projects/{project_id}/label-map", response_model=LabelMapResponse)
def save_label_mapping(
    project_id: int,
    request: LabelMapRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    保存项目级行为映射
    
    Args:
        project_id: 项目 ID
        request: 行为映射
    
    Returns:
        LabelMapResponse: 已保存的映射
    """
    # 验证项目访问权限
    verify_project_access(project_id, db, current_user)
    
    # 保存映射
    try:
        fluorescence_service.save_label_map(project_id, request.mapping)
        return LabelMapResponse(projectId=project_id, mapping=request.mapping)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save label map: {str(e)}")


@router.get("/projects/{project_id}/label-map", response_model=LabelMapResponse)
def get_label_mapping(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """
    获取项目级行为映射
    
    Args:
        project_id: 项目 ID
    
    Returns:
        LabelMapResponse: 行为映射
    """
    # 验证项目访问权限
    verify_project_access(project_id, db, current_user)
    
    # 加载映射
    try:
        mapping = fluorescence_service.load_label_map(project_id)
        return LabelMapResponse(projectId=project_id, mapping=mapping)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load label map: {str(e)}")
