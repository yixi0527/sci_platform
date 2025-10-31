"""
荧光分析相关的 Pydantic 模型
定义所有请求和响应的数据结构
"""
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator


# ==================== 通用模型 ====================

class TimeWindow(BaseModel):
    """时间窗口"""
    start: float = Field(..., description="起始时间（秒）")
    end: float = Field(..., description="结束时间（秒）")


class MaskRange(BaseModel):
    """掩码时间范围"""
    start: float = Field(..., description="掩码起始时间（秒）")
    end: float = Field(..., description="掩码结束时间（秒）")


class Event(BaseModel):
    """单个事件定义"""
    label: str = Field(..., description="事件标签/行为名称")
    displayName: Optional[str] = Field(None, description="显示名称")


class EventGroup(BaseModel):
    """事件组（用于 multi 模式）"""
    groupName: str = Field(..., description="组名")
    events: List[str] = Field(..., description="事件标签列表")


class ColumnMap(BaseModel):
    """CSV 列映射"""
    behavior: str = Field(..., description="行为列名")
    start: str = Field(..., description="开始时间列名")
    stop: Optional[str] = Field(None, description="结束时间列名（点事件可为空）")
    isPointEvent: bool = Field(False, description="是否为点事件")


class TagFilter(BaseModel):
    """标签筛选条件"""
    and_tags: List[int] = Field(default_factory=list, alias="and", description="AND 逻辑标签 ID 列表")
    or_tags: List[int] = Field(default_factory=list, alias="or", description="OR 逻辑标签 ID 列表")
    
    class Config:
        populate_by_name = True


class DataSelection(BaseModel):
    """数据选择方式"""
    dataItemIds: Optional[List[int]] = Field(None, description="直接指定 data_item ID 列表")
    tagFilter: Optional[TagFilter] = Field(None, description="通过标签筛选")
    
    @field_validator('dataItemIds', 'tagFilter')
    @classmethod
    def check_selection(cls, v, info):
        # 至少提供一种选择方式
        if info.field_name == 'tagFilter' and v is None:
            values = info.data
            if values.get('dataItemIds') is None:
                raise ValueError("Must provide either dataItemIds or tagFilter")
        return v


class OutputOptions(BaseModel):
    """输出选项"""
    df_f: bool = Field(True, description="输出 ΔF/F")
    zscore: bool = Field(False, description="输出 z-score")
    warping: bool = Field(False, description="输出 time warping 结果（仅 multi 模式）")


# ==================== 预览相关 ====================

class PreviewRequest(BaseModel):
    """CSV 预览请求"""
    dataItemId: int = Field(..., description="数据项 ID")
    maxRows: int = Field(50, ge=1, le=100, description="最大预览行数")


class PreviewResponse(BaseModel):
    """CSV 预览响应"""
    dataItemId: int
    columns: List[str] = Field(..., description="列名列表")
    rows: List[List[Any]] = Field(..., description="数据行")
    totalRows: int = Field(..., description="实际返回的行数")


# ==================== 分析相关 ====================

class AnalyzeRequest(BaseModel):
    """荧光分析请求"""
    selection: DataSelection = Field(..., description="数据选择")
    fps: float = Field(50.0, gt=0, description="采样率（帧/秒）")
    mode: str = Field(..., pattern="^(single|multi)$", description="分析模式：single 或 multi")
    algorithmType: str = Field("zscore", pattern="^(zscore|warping)$", description="算法类型：zscore 或 warping")
    
    # 单事件模式
    events: Optional[List[Event]] = Field(None, description="事件列表（single 模式）")
    baselineWindow: Optional[TimeWindow] = Field(None, description="基线窗口（single 模式）")
    responseWindow: Optional[TimeWindow] = Field(None, description="响应窗口（single 模式）")
    
    # 多事件模式
    groups: Optional[List[EventGroup]] = Field(None, description="事件组列表（multi 模式）")
    
    # 可选参数
    offsetWindow: Optional[TimeWindow] = Field(None, description="实验前偏移窗口")
    outputs: OutputOptions = Field(default_factory=OutputOptions, description="输出选项")
    
    # 列映射与标签映射
    columnMap: ColumnMap = Field(..., description="CSV 列名映射")
    labelMapping: Dict[str, str] = Field(default_factory=dict, description="原始标签到显示名称的映射")
    
    # 掩码（key 格式："{dataItemId}:{channel}"）
    masks: Dict[str, List[MaskRange]] = Field(default_factory=dict, description="时间掩码")
    
    @field_validator('events', 'baselineWindow', 'responseWindow')
    @classmethod
    def check_single_mode(cls, v, info):
        values = info.data
        if values.get('mode') == 'single' and v is None:
            raise ValueError(f"{info.field_name} is required for single mode")
        return v
    
    @field_validator('groups')
    @classmethod
    def check_multi_mode(cls, v, info):
        values = info.data
        if values.get('mode') == 'multi' and v is None:
            raise ValueError("groups is required for multi mode")
        return v


class JobCreateResponse(BaseModel):
    """任务创建响应"""
    jobId: str = Field(..., description="任务 ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="提示信息")


# ==================== 任务状态相关 ====================

class JobStatusResponse(BaseModel):
    """任务状态响应"""
    jobId: str
    projectId: int
    status: str = Field(..., description="queued/running/succeeded/failed")
    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    message: str = Field(..., description="当前状态描述")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    createdAt: str = Field(..., description="创建时间（ISO 格式）")
    updatedAt: str = Field(..., description="更新时间（ISO 格式）")


# ==================== 结果相关 ====================

class MatrixResult(BaseModel):
    """热力图矩阵结果"""
    key: str = Field(..., description="标识，如 'CH1/w' 表示通道1的事件w")
    heatmap: List[List[float]] = Field(..., description="热力图数据矩阵")
    xAxis: List[float] = Field(..., description="X轴时间点")
    trialIds: List[str] = Field(..., description="试次标识列表")


class CurveResult(BaseModel):
    """均值曲线结果"""
    key: str = Field(..., description="标识")
    mean: List[float] = Field(..., description="均值曲线")
    sem: Optional[List[float]] = Field(None, description="标准误差曲线")
    xAxis: List[float] = Field(..., description="X轴时间点")


class ResultMeta(BaseModel):
    """结果元信息"""
    projectId: int
    fps: float
    mode: str
    params: Dict[str, Any] = Field(..., description="分析参数")
    tagsUsed: List[int] = Field(default_factory=list, description="使用的标签 ID 列表")
    dataItemsCount: int = Field(..., description="处理的数据项数量")


class ResultResponse(BaseModel):
    """分析结果响应"""
    jobId: str
    meta: ResultMeta = Field(..., description="元信息")
    matrices: List[MatrixResult] = Field(default_factory=list, description="热力图矩阵列表")
    curves: List[CurveResult] = Field(default_factory=list, description="均值曲线列表")
    assets: Dict[str, str] = Field(default_factory=dict, description="可选的导出文件 URL")


# ==================== 行为映射相关 ====================

class LabelMapRequest(BaseModel):
    """行为映射请求"""
    mapping: Dict[str, str] = Field(..., description="原始标签 -> 显示名称的映射")


class LabelMapResponse(BaseModel):
    """行为映射响应"""
    projectId: int
    mapping: Dict[str, str] = Field(..., description="行为映射字典")
