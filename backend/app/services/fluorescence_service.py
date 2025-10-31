"""
荧光分析服务层
负责业务逻辑编排、数据选择、任务管理
"""
import os
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.utils.logger import service_logger as logger

from app.models.data_item import DataItem
from app.schemas.fluorescence import (
    AnalyzeRequest,
    DataSelection,
    JobCreateResponse,
    JobStatusResponse,
    ResultResponse,
    ResultMeta,
    MatrixResult,
    CurveResult,
)
from app.services.job_registry import job_registry, JobStatus
from app.services.algorithms.fluorescence_algo import (
    Dataset,
    Channel,
    LabelEvent,
    AnalysisParams,
    AnalysisResult,
    load_fluorescence_data,
    load_label_data,
    analyze_single_event,
    analyze_multi_event,
)
from app.utils.tag_selector import select_by_tags, get_data_items_by_ids


def resolve_data_items(
    db: Session,
    project_id: int,
    selection: DataSelection
) -> List[DataItem]:
    """
    解析数据选择，返回 DataItem 列表
    
    Args:
        db: 数据库会话
        project_id: 项目 ID
        selection: 数据选择方式
    
    Returns:
        DataItem 列表
    """
    if selection.dataItemIds:
        # 直接通过 ID 获取
        return get_data_items_by_ids(db, project_id, selection.dataItemIds)
    elif selection.tagFilter:
        # 通过标签筛选
        return select_by_tags(db, project_id, selection.tagFilter.model_dump())
    else:
        return []


def build_datasets(
    db: Session,
    data_items: List[DataItem],
    request: AnalyzeRequest
) -> List[Dataset]:
    """
    构建数据集列表
    为每个荧光文件关联打标文件，并加载数据
    
    Args:
        db: 数据库会话
        data_items: 数据项列表
        request: 分析请求
    
    Returns:
        Dataset 列表
    """
    datasets = []
    
    # 按目录分组，找出荧光文件与打标文件的对应关系
    # 简化策略：同一目录下的所有 CSV 文件视为相关
    # 可以通过 type 字段或文件名模式区分荧光/打标
    
    fluorescence_items = [item for item in data_items if is_fluorescence_file(item)]
    
    for fluor_item in fluorescence_items:
        # 找到同一目录下的打标文件
        label_items = find_label_files(fluor_item, data_items)
        
        # 加载荧光数据
        # Construct full path from uploads directory
        fluor_path = os.path.join("uploads", fluor_item.filePath)
        masks_key = f"{fluor_item.dataItemId}"
        masks = []
        
        # 提取掩码（支持按通道或文件级）
        for mask_key, mask_ranges in request.masks.items():
            if mask_key.startswith(str(fluor_item.dataItemId)):
                for mr in mask_ranges:
                    masks.append((mr.start, mr.end))
        
        try:
            channels = load_fluorescence_data(fluor_path, request.fps, masks if masks else None)
        except Exception as e:
            logger.error(f"Failed to load fluorescence data from {fluor_path}: {e}")
            continue
        
        # 加载打标数据
        all_events = []
        for label_item in label_items:
            try:
                label_path = os.path.join("uploads", label_item.filePath)
                events = load_label_data(
                    label_path,
                    column_map=request.columnMap.model_dump(),
                    label_mapping=request.labelMapping
                )
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Failed to load label data from {label_path}: {e}")
                continue
        
        dataset = Dataset(
            data_item_id=fluor_item.dataItemId,
            fluorescence_file=fluor_path,
            label_files=[os.path.join("uploads", item.filePath) for item in label_items],
            channels=channels,
            events=all_events,
            fps=request.fps,
            metadata={'projectId': fluor_item.projectId}
        )
        
        datasets.append(dataset)
    
    return datasets


def is_fluorescence_file(item: DataItem) -> bool:
    """
    判断是否为荧光文件
    可通过 type 字段或文件名模式判断
    """
    # 简化判断：如果 dataType 为 'fluorescence' 或文件名包含 'fluorescence'
    if hasattr(item, 'dataType') and item.dataType == 'fluorescence':
        return True
    
    # 或者通过文件名判断（不含 'top' 等关键词）
    filename = Path(item.filePath).name.lower()
    if 'top' in filename or 'label' in filename or 'behavior' in filename:
        return False
    
    return True


def find_label_files(fluor_item: DataItem, all_items: List[DataItem]) -> List[DataItem]:
    """
    找到与荧光文件对应的打标文件
    策略：同一目录下的 top.csv 或包含 'label' 的文件
    """
    fluor_dir = Path(fluor_item.filePath).parent
    
    label_items = []
    for item in all_items:
        if item.dataItemId == fluor_item.dataItemId:
            continue
        
        item_path = Path(item.filePath)
        if item_path.parent == fluor_dir:
            filename = item_path.name.lower()
            if 'top' in filename or 'label' in filename or 'behavior' in filename:
                label_items.append(item)
    
    return label_items


def create_analysis_job(
    db: Session,
    project_id: int,
    request: AnalyzeRequest
) -> JobCreateResponse:
    """
    创建分析任务
    
    Args:
        db: 数据库会话
        project_id: 项目 ID
        request: 分析请求
    
    Returns:
        任务创建响应
    """
    # 生成任务 ID
    job_id = str(uuid.uuid4())
    
    # 持久化目录
    persist_dir = f"uploads/projects/{project_id}/fluorescence/jobs/{job_id}"
    
    # 创建任务记录
    job = job_registry.create_job(
        job_id=job_id,
        project_id=project_id,
        params=request.model_dump(),
        persist_dir=persist_dir
    )
    
    return JobCreateResponse(
        jobId=job_id,
        status=job["status"],
        message="Analysis task created and queued"
    )


def execute_analysis(
    db: Session,
    project_id: int,
    job_id: str,
    request: AnalyzeRequest
):
    """
    执行分析任务（后台运行）
    
    Args:
        db: 数据库会话
        project_id: 项目 ID
        job_id: 任务 ID
        request: 分析请求
    """
    try:
        # 更新状态：运行中
        job_registry.update_job(job_id, status=JobStatus.RUNNING, progress=5, message="Resolving data selection...")
        
        # 1. 解析数据选择
        data_items = resolve_data_items(db, project_id, request.selection)
        if not data_items:
            raise ValueError("No data items found for the given selection")
        
        job_registry.update_job(job_id, progress=10, message=f"Found {len(data_items)} data items")
        
        # 2. 构建数据集
        job_registry.update_job(job_id, progress=20, message="Building datasets...")
        datasets = build_datasets(db, data_items, request)
        
        if not datasets:
            raise ValueError("No valid datasets could be built")
        
        job_registry.update_job(job_id, progress=40, message=f"Built {len(datasets)} dataset(s)")
        
        # 3. 准备分析参数
        params = AnalysisParams(
            mode=request.mode,
            fps=request.fps,
            algorithm_type=request.algorithmType,
            output_df_f=request.outputs.df_f,
            output_zscore=request.outputs.zscore,
            output_warping=request.outputs.warping
        )
        
        if request.mode == 'single':
            params.events = [e.label for e in request.events]
            params.baseline_window = (request.baselineWindow.start, request.baselineWindow.end)
            params.response_window = (request.responseWindow.start, request.responseWindow.end)
            if request.offsetWindow:
                params.offset_window = (request.offsetWindow.start, request.offsetWindow.end)
        else:  # multi
            params.groups = [g.model_dump() for g in request.groups]
        
        # 4. 执行分析
        job_registry.update_job(job_id, progress=50, message="Running analysis algorithm...")
        
        if request.mode == 'single':
            result = analyze_single_event(datasets, params)
        else:
            result = analyze_multi_event(datasets, params)
        
        job_registry.update_job(job_id, progress=80, message="Analysis completed, formatting results...")
        
        # 5. 格式化结果
        # 提取使用的标签ID（从数据选择中获取）
        tags_used = set()
        if request.fluorSelection:
            if hasattr(request.fluorSelection, 'and_tags'):
                tags_used.update(request.fluorSelection.and_tags or [])
            if hasattr(request.fluorSelection, 'or_tags'):
                tags_used.update(request.fluorSelection.or_tags or [])
        if request.labelSelection:
            if hasattr(request.labelSelection, 'and_tags'):
                tags_used.update(request.labelSelection.and_tags or [])
            if hasattr(request.labelSelection, 'or_tags'):
                tags_used.update(request.labelSelection.or_tags or [])
        
        meta = ResultMeta(
            projectId=project_id,
            fps=request.fps,
            mode=request.mode,
            params=request.model_dump(),
            tagsUsed=list(tags_used),
            dataItemsCount=len(datasets)
        )
        
        matrices = [MatrixResult(**m) for m in result.matrices]
        curves = [CurveResult(**c) for c in result.curves]
        
        response = ResultResponse(
            jobId=job_id,
            meta=meta,
            matrices=matrices,
            curves=curves,
            assets={}
        )
        
        # 6. 保存结果到文件
        job_registry.update_job(job_id, progress=90, message="Saving results...")
        save_result(project_id, job_id, response)
        
        # 7. 完成
        job_registry.update_job(
            job_id,
            status=JobStatus.SUCCEEDED,
            progress=100,
            message="Analysis completed successfully"
        )
        
    except Exception as e:
        # 失败
        job_registry.update_job(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            message="Analysis failed",
            error=str(e)
        )
        logger.error(f"Analysis failed for job {job_id}: {e}", exc_info=True)


def save_result(project_id: int, job_id: str, result: ResultResponse):
    """
    保存结果到 JSON 文件
    """
    result_dir = Path(f"uploads/projects/{project_id}/fluorescence/jobs/{job_id}")
    result_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = result_dir / "result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)


def list_project_jobs(project_id: int, skip: int = 0, limit: int = 50) -> List[JobStatusResponse]:
    """
    获取项目的所有任务列表
    
    Args:
        project_id: 项目 ID
        skip: 分页偏移
        limit: 返回数量
    
    Returns:
        任务状态列表（按创建时间倒序）
    """
    all_jobs = job_registry.list_jobs()
    
    # 筛选该项目的任务
    project_jobs = [
        job for job in all_jobs
        if job.get("projectId") == project_id
    ]
    
    # 按创建时间倒序排序
    project_jobs.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    
    # 分页
    paginated_jobs = project_jobs[skip:skip + limit]
    
    # 转换为响应格式
    return [
        JobStatusResponse(
            jobId=job["jobId"],
            projectId=job["projectId"],
            status=job["status"],
            progress=job["progress"],
            message=job["message"],
            error=job.get("error"),
            createdAt=job["createdAt"],
            updatedAt=job["updatedAt"]
        )
        for job in paginated_jobs
    ]


def get_job_status(job_id: str) -> Optional[JobStatusResponse]:
    """
    获取任务状态
    """
    job = job_registry.get_job(job_id)
    if not job:
        return None
    
    return JobStatusResponse(
        jobId=job["jobId"],
        projectId=job["projectId"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        error=job.get("error"),
        createdAt=job["createdAt"],
        updatedAt=job["updatedAt"]
    )


def get_job_result(project_id: int, job_id: str) -> Optional[ResultResponse]:
    """
    获取任务结果
    """
    result_file = Path(f"uploads/projects/{project_id}/fluorescence/jobs/{job_id}/result.json")
    
    if not result_file.exists():
        return None
    
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return ResultResponse(**data)


def save_label_map(project_id: int, mapping: Dict[str, str]):
    """
    保存项目级行为映射
    """
    map_dir = Path(f"uploads/projects/{project_id}/fluorescence")
    map_dir.mkdir(parents=True, exist_ok=True)
    
    map_file = map_dir / "label-map.json"
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def load_label_map(project_id: int) -> Dict[str, str]:
    """
    加载项目级行为映射
    """
    map_file = Path(f"uploads/projects/{project_id}/fluorescence/label-map.json")
    
    if not map_file.exists():
        return {}
    
    with open(map_file, "r", encoding="utf-8") as f:
        return json.load(f)
