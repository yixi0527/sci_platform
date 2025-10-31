"""
算法层契约与接口定义
与 create_DA_dataset.py 的参数风格对齐，但不绑定其实现
实现两种 dF/F 计算方法：zscore 和 warping
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from scipy import interpolate, signal

from app.utils.logger import algo_logger as logger


@dataclass
class Channel:
    """通道定义"""
    name: str  # 如 "CH1"
    baseline_410: np.ndarray  # 410nm 数据
    signal_470: np.ndarray    # 470nm 数据


@dataclass
class LabelEvent:
    """标注事件"""
    label: str           # 事件标签
    start_time: float    # 开始时间（秒）
    stop_time: float     # 结束时间（秒）
    is_point: bool = False  # 是否为点事件


@dataclass
class Dataset:
    """单个数据集（一个荧光文件 + 对应的打标文件）"""
    data_item_id: int
    fluorescence_file: str
    label_files: List[str]
    channels: List[Channel]
    events: List[LabelEvent]
    fps: float
    metadata: Dict[str, Any] = None


@dataclass
class AnalysisParams:
    """分析参数"""
    mode: str  # 'single' or 'multi'
    fps: float
    algorithm_type: str = 'zscore'  # 'zscore' or 'warping'
    
    # 单事件模式
    events: Optional[List[str]] = None  # 事件标签列表
    baseline_window: Optional[Tuple[float, float]] = None  # (start, end)
    response_window: Optional[Tuple[float, float]] = None
    
    # 多事件模式
    groups: Optional[List[Dict[str, Any]]] = None  # [{'groupName': '...', 'events': [...]}]
    
    # 可选
    offset_window: Optional[Tuple[float, float]] = None
    output_df_f: bool = True
    output_zscore: bool = False
    output_warping: bool = False


@dataclass
class AnalysisResult:
    """分析结果"""
    matrices: List[Dict[str, Any]]  # 热力图矩阵
    curves: List[Dict[str, Any]]     # 均值曲线
    metadata: Dict[str, Any]


def load_fluorescence_data(
    file_path: str,
    fps: float,
    masks: Optional[List[Tuple[float, float]]] = None
) -> List[Channel]:
    """
    加载荧光数据文件并解析通道
    
    Args:
        file_path: 荧光 CSV 文件路径
        fps: 采样率
        masks: 掩码时间范围列表 [(start, end), ...]
    
    Returns:
        通道列表
    
    Raises:
        ValueError: 通道不成对或缺失
    """
    logger.info(f"Loading fluorescence data from {file_path} with fps={fps}")
    
    # 读取 CSV 文件
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
    
    # 检测通道列（匹配 CHx-410 和 CHx-470 模式）
    import re
    channel_pattern = re.compile(r'^CH(\d+)-(410|470)$', re.IGNORECASE)
    
    channel_cols = {}
    for col in df.columns:
        match = channel_pattern.match(col.strip())
        if match:
            ch_num = match.group(1)
            wavelength = match.group(2)
            if ch_num not in channel_cols:
                channel_cols[ch_num] = {}
            channel_cols[ch_num][wavelength] = col
    
    # 验证通道成对
    channels = []
    for ch_num, wavelengths in channel_cols.items():
        if '410' not in wavelengths or '470' not in wavelengths:
            raise ValueError(f"Channel {ch_num} is missing 410 or 470 wavelength data")
        
        # 提取数据
        data_410 = df[wavelengths['410']].values.astype(float)
        data_470 = df[wavelengths['470']].values.astype(float)
        
        # 应用掩码（删除指定时间范围的数据点）
        if masks and len(masks) > 0:
            mask_indices = []
            for start, end in masks:
                start_idx = int(start * fps)
                end_idx = int(end * fps)
                mask_indices.extend(range(start_idx, min(end_idx, len(data_410))))
            
            # 创建布尔掩码并保留非掩码数据
            keep_mask = np.ones(len(data_410), dtype=bool)
            if mask_indices:
                keep_mask[mask_indices] = False
                data_410 = data_410[keep_mask]
                data_470 = data_470[keep_mask]
                logger.debug(f"Applied masks, removed {len(mask_indices)} samples from CH{ch_num}")
        
        channel = Channel(
            name=f"CH{ch_num}",
            baseline_410=data_410,
            signal_470=data_470
        )
        channels.append(channel)
    
    if not channels:
        raise ValueError("No valid channel pairs found in CSV file")
    
    logger.info(f"Loaded {len(channels)} channel(s)")
    return channels


def load_label_data(
    file_path: str,
    column_map: Dict[str, str],
    label_mapping: Dict[str, str] = None
) -> List[LabelEvent]:
    """
    加载打标数据文件
    
    Args:
        file_path: 打标 CSV 文件路径
        column_map: 列名映射 {'behavior': '...', 'start': '...', 'stop': '...', 'isPointEvent': bool}
        label_mapping: 原始标签到显示名称的映射
    
    Returns:
        事件列表
    """
    logger.info(f"Loading label data from {file_path}")
    logger.debug(f"Column map: {column_map}")
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read label CSV file: {e}")
    
    # 获取列名
    behavior_col = column_map.get('behavior')
    start_col = column_map.get('start')
    stop_col = column_map.get('stop')
    is_point_event = column_map.get('isPointEvent', False)
    
    if not behavior_col or not start_col:
        raise ValueError("behavior and start columns must be specified")
    
    if behavior_col not in df.columns:
        raise ValueError(f"Behavior column '{behavior_col}' not found in CSV")
    if start_col not in df.columns:
        raise ValueError(f"Start column '{start_col}' not found in CSV")
    
    events = []
    for idx, row in df.iterrows():
        label = str(row[behavior_col]).strip()
        
        # 应用标签映射
        if label_mapping and label in label_mapping:
            label = label_mapping[label]
        
        start_time = float(row[start_col])
        
        # 处理点事件和区间事件
        if is_point_event or not stop_col or stop_col not in df.columns:
            stop_time = start_time
            is_point = True
        else:
            stop_time = float(row[stop_col])
            is_point = (start_time == stop_time)
        
        event = LabelEvent(
            label=label,
            start_time=start_time,
            stop_time=stop_time,
            is_point=is_point
        )
        events.append(event)
    
    logger.info(f"Loaded {len(events)} events")
    return events


def calculate_df_f_zscore(
    signal_410: np.ndarray,
    signal_470: np.ndarray,
    fps: float,
    baseline_start: float,
    baseline_end: float,
    event_time: float,
    window_start: float,
    window_end: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    使用 z-score 方法计算单个事件的 ΔF/F
    
    基于论文常用的 dF/F 计算方法：
    1. 计算 F = signal_470 - k * signal_410 (k 由基线拟合得到)
    2. 归一化: ΔF/F = (F - baseline_mean) / baseline_std
    
    Args:
        signal_410: 410nm 信号
        signal_470: 470nm 信号
        fps: 采样率
        baseline_start: 基线窗口起始（相对于事件）
        baseline_end: 基线窗口结束
        event_time: 事件发生时间（秒）
        window_start: 提取窗口起始（相对于事件）
        window_end: 提取窗口结束
    
    Returns:
        (df_f, time_axis)
    """
    # 转换时间到索引
    event_idx = int(event_time * fps)
    baseline_start_idx = event_idx + int(baseline_start * fps)
    baseline_end_idx = event_idx + int(baseline_end * fps)
    window_start_idx = event_idx + int(window_start * fps)
    window_end_idx = event_idx + int(window_end * fps)
    
    # 边界检查
    baseline_start_idx = max(0, baseline_start_idx)
    baseline_end_idx = min(len(signal_410), baseline_end_idx)
    window_start_idx = max(0, window_start_idx)
    window_end_idx = min(len(signal_410), window_end_idx)
    
    if baseline_start_idx >= baseline_end_idx or window_start_idx >= window_end_idx:
        raise ValueError("Invalid time window indices")
    
    # 提取基线数据并计算拟合系数 k
    baseline_410 = signal_410[baseline_start_idx:baseline_end_idx]
    baseline_470 = signal_470[baseline_start_idx:baseline_end_idx]
    
    # 使用线性回归拟合 470 = k * 410
    if len(baseline_410) > 1:
        k = np.polyfit(baseline_410, baseline_470, 1)[0]
    else:
        k = 1.0
    
    # 计算校正后的荧光信号 F
    F_full = signal_470 - k * signal_410
    
    # 提取窗口数据
    F_window = F_full[window_start_idx:window_end_idx]
    F_baseline = F_full[baseline_start_idx:baseline_end_idx]
    
    # 计算基线统计量
    baseline_mean = np.mean(F_baseline)
    baseline_std = np.std(F_baseline)
    
    # 计算 ΔF/F (z-score 归一化)
    if baseline_std > 1e-10:
        df_f = (F_window - baseline_mean) / baseline_std
    else:
        df_f = (F_window - baseline_mean)
    
    # 生成时间轴
    time_axis = np.arange(len(F_window)) / fps + window_start
    
    return df_f, time_axis


def calculate_df_f(
    channel: Channel,
    events: List[LabelEvent],
    baseline_window: Tuple[float, float],
    response_window: Tuple[float, float],
    fps: float,
    event_filter: Optional[List[str]] = None,
    algorithm: str = "zscore"
) -> Dict[str, np.ndarray]:
    """
    计算 ΔF/F
    
    Args:
        channel: 通道数据
        events: 事件列表
        baseline_window: 基线窗口 (start, end) 相对于事件时间
        response_window: 响应窗口
        fps: 采样率
        event_filter: 仅处理指定标签的事件
        algorithm: 算法类型 "zscore" 或 "warping"
    
    Returns:
        {
            'df_f': ndarray,  # shape: (n_trials, n_timepoints)
            'time_axis': ndarray,
            'trial_ids': List[str]
        }
    """
    logger.info(f"Calculating ΔF/F for channel {channel.name} using {algorithm}")
    logger.debug(f"Baseline window: {baseline_window}, Response window: {response_window}")
    
    # 筛选事件
    filtered_events = [e for e in events if not event_filter or e.label in event_filter]
    
    if not filtered_events:
        logger.warning(f"No events found matching filter {event_filter}")
        return {
            'df_f': np.array([]),
            'time_axis': np.array([]),
            'trial_ids': []
        }
    
    # 计算完整窗口范围
    window_start = min(baseline_window[0], response_window[0])
    window_end = max(baseline_window[1], response_window[1])
    
    df_f_list = []
    time_axis = None
    trial_ids = []
    
    for i, event in enumerate(filtered_events):
        event_time = event.start_time
        
        try:
            df_f_trial, time_axis_trial = calculate_df_f_zscore(
                signal_410=channel.baseline_410,
                signal_470=channel.signal_470,
                fps=fps,
                baseline_start=baseline_window[0],
                baseline_end=baseline_window[1],
                event_time=event_time,
                window_start=window_start,
                window_end=window_end
            )
            
            df_f_list.append(df_f_trial)
            if time_axis is None:
                time_axis = time_axis_trial
            
            trial_ids.append(f"trial_{i}_{event.label}")
            
        except Exception as e:
            logger.warning(f"Failed to process event {i} at {event_time}s: {e}")
            continue
    
    if not df_f_list:
        raise ValueError("No valid trials could be processed")
    
    # 堆叠成矩阵
    df_f_matrix = np.vstack(df_f_list)
    
    return {
        'df_f': df_f_matrix,
        'time_axis': time_axis,
        'trial_ids': trial_ids
    }


def calculate_zscore(df_f: np.ndarray) -> np.ndarray:
    """
    计算 z-score
    """
    mean = np.mean(df_f, axis=1, keepdims=True)
    std = np.std(df_f, axis=1, keepdims=True)
    zscore = (df_f - mean) / (std + 1e-10)
    return zscore


def time_warp_signal(
    signal: np.ndarray,
    events: List[float],
    target_length: int = 100
) -> np.ndarray:
    """
    对多个事件之间的信号片段进行时间归一化（warping）
    
    Args:
        signal: 完整信号
        events: 事件时间点列表（单位：样本索引）
        target_length: 目标归一化长度
    
    Returns:
        归一化后的信号
    """
    if len(events) < 2:
        return signal
    
    warped_segments = []
    
    for i in range(len(events) - 1):
        start_idx = int(events[i])
        end_idx = int(events[i + 1])
        
        if start_idx >= end_idx or end_idx > len(signal):
            continue
        
        segment = signal[start_idx:end_idx]
        
        # 使用插值将片段归一化到目标长度
        if len(segment) > 1:
            x_old = np.linspace(0, 1, len(segment))
            x_new = np.linspace(0, 1, target_length)
            f = interpolate.interp1d(x_old, segment, kind='linear', fill_value='extrapolate')
            warped_segment = f(x_new)
            warped_segments.append(warped_segment)
    
    if not warped_segments:
        return signal[:target_length] if len(signal) >= target_length else np.pad(signal, (0, target_length - len(signal)))
    
    # 拼接所有归一化片段
    warped_signal = np.concatenate(warped_segments)
    
    return warped_signal


def calculate_df_f_warping(
    channel: Channel,
    event_groups: List[List[LabelEvent]],
    fps: float,
    response_window: Tuple[float, float],
    target_segment_length: int = 100
) -> Dict[str, np.ndarray]:
    """
    使用 time warping 方法计算多事件组的 ΔF/F
    
    将一组连续事件之间的时间片段归一化到相同长度，然后进行分析
    
    Args:
        channel: 通道数据
        event_groups: 事件组列表，每组是一个事件序列
        fps: 采样率
        response_window: 响应窗口
        target_segment_length: 每个事件间隔归一化的目标长度
    
    Returns:
        {
            'df_f': ndarray,
            'time_axis': ndarray (normalized 0-1),
            'trial_ids': List[str]
        }
    """
    logger.info(f"Calculating ΔF/F with time warping for {len(event_groups)} groups")
    
    signal_410 = channel.baseline_410
    signal_470 = channel.signal_470
    
    # 计算基线校正系数（使用前10%数据作为基线）
    baseline_len = len(signal_410) // 10
    k = np.polyfit(signal_410[:baseline_len], signal_470[:baseline_len], 1)[0]
    F = signal_470 - k * signal_410
    
    df_f_list = []
    trial_ids = []
    
    for group_idx, event_group in enumerate(event_groups):
        if len(event_group) < 2:
            continue
        
        # 获取事件时间点（样本索引）
        event_times = [int(e.start_time * fps) for e in event_group]
        
        # 对信号进行 warping
        warped_signal = time_warp_signal(F, event_times, target_segment_length)
        
        # 计算归一化（使用warped signal的前20%作为基线）
        baseline_len = len(warped_signal) // 5
        baseline_mean = np.mean(warped_signal[:baseline_len])
        baseline_std = np.std(warped_signal[:baseline_len])
        
        if baseline_std > 1e-10:
            df_f_trial = (warped_signal - baseline_mean) / baseline_std
        else:
            df_f_trial = warped_signal - baseline_mean
        
        df_f_list.append(df_f_trial)
        trial_ids.append(f"trial_{group_idx}")
    
    if not df_f_list:
        raise ValueError("No valid trial groups could be processed")
    
    # 确保所有试次长度一致
    max_len = max(len(trial) for trial in df_f_list)
    df_f_padded = []
    for trial in df_f_list:
        if len(trial) < max_len:
            padded = np.pad(trial, (0, max_len - len(trial)), mode='edge')
        else:
            padded = trial[:max_len]
        df_f_padded.append(padded)
    
    df_f_matrix = np.vstack(df_f_padded)
    
    # 归一化时间轴 (0 到 1)
    time_axis = np.linspace(0, 1, max_len)
    
    return {
        'df_f': df_f_matrix,
        'time_axis': time_axis,
        'trial_ids': trial_ids
    }


def time_warp_alignment(
    datasets: List[Dataset],
    groups: List[Dict[str, Any]],
    params: AnalysisParams
) -> AnalysisResult:
    """
    多事件组 time warping 对齐分析
    
    Args:
        datasets: 数据集列表
        groups: 事件组定义
        params: 分析参数
    
    Returns:
        分析结果
    """
    logger.info(f"Time warping alignment for {len(groups)} groups")
    
    matrices = []
    curves = []
    
    for group in groups:
        group_name = group.get('groupName') or group.get('name')
        event_labels = group.get('events', [])
        
        logger.debug(f"Processing group '{group_name}' with events: {event_labels}")
        
        # 遍历每个数据集
        for dataset in datasets:
            # 为每个组筛选事件并组织成序列
            event_sequences = []
            
            # 找出符合当前组定义的事件序列
            # 简化策略：将所有匹配标签的连续事件作为一个序列
            current_sequence = []
            for event in sorted(dataset.events, key=lambda e: e.start_time):
                if event.label in event_labels:
                    current_sequence.append(event)
                else:
                    if len(current_sequence) >= 2:
                        event_sequences.append(current_sequence)
                    current_sequence = []
            
            if len(current_sequence) >= 2:
                event_sequences.append(current_sequence)
            
            for channel in dataset.channels:
                if not event_sequences:
                    logger.warning(f"No valid event sequences for group '{group_name}'")
                    continue
                
                try:
                    result = calculate_df_f_warping(
                        channel=channel,
                        event_groups=event_sequences,
                        fps=params.fps,
                        response_window=params.response_window if params.response_window else (0, 6),
                        target_segment_length=100
                    )
                    
                    df_f = result['df_f']
                    time_axis = result['time_axis']
                    trial_ids = result['trial_ids']
                    
                    # 添加矩阵
                    matrices.append({
                        'key': f"{channel.name}/{group_name}",
                        'heatmap': df_f.tolist(),
                        'xAxis': time_axis.tolist(),
                        'trialIds': trial_ids
                    })
                    
                    # 添加曲线
                    if len(df_f) > 0:
                        mean_curve = np.mean(df_f, axis=0)
                        sem_curve = np.std(df_f, axis=0) / np.sqrt(len(df_f)) if len(df_f) > 1 else np.zeros_like(mean_curve)
                        
                        curves.append({
                            'key': f"{channel.name}/{group_name}",
                            'mean': mean_curve.tolist(),
                            'sem': sem_curve.tolist(),
                            'xAxis': time_axis.tolist()
                        })
                
                except Exception as e:
                    logger.error(f"Error processing group '{group_name}' for channel {channel.name}: {e}")
                    continue
    
    return AnalysisResult(
        matrices=matrices,
        curves=curves,
        metadata={'mode': 'multi', 'groups': [g.get('groupName') or g.get('name') for g in groups]}
    )


def analyze_single_event(
    datasets: List[Dataset],
    params: AnalysisParams
) -> AnalysisResult:
    """
    单事件模式分析
    
    Args:
        datasets: 数据集列表
        params: 分析参数
    
    Returns:
        分析结果
    """
    logger.info(f"Single event analysis for {len(datasets)} dataset(s)")
    logger.debug(f"Events: {params.events}")
    
    # 确定算法类型
    algorithm = getattr(params, 'algorithm_type', 'zscore')
    
    matrices = []
    curves = []
    
    # 遍历每个数据集
    for dataset in datasets:
        for channel in dataset.channels:
            # 对每个事件类型分别计算
            for event_label in params.events:
                result = calculate_df_f(
                    channel=channel,
                    events=dataset.events,
                    baseline_window=params.baseline_window,
                    response_window=params.response_window,
                    fps=params.fps,
                    event_filter=[event_label],
                    algorithm=algorithm
                )
                
                df_f = result['df_f']
                time_axis = result['time_axis']
                trial_ids = result['trial_ids']
                
                if len(df_f) == 0:
                    logger.warning(f"No data for {channel.name}/{event_label}")
                    continue
                
                # 是否额外计算 z-score
                if params.output_zscore and algorithm != 'zscore':
                    df_f = calculate_zscore(df_f)
                
                # 添加矩阵
                matrices.append({
                    'key': f"{channel.name}/{event_label}",
                    'heatmap': df_f.tolist(),
                    'xAxis': time_axis.tolist(),
                    'trialIds': trial_ids
                })
                
                # 添加曲线
                if len(df_f) > 0:
                    mean_curve = np.mean(df_f, axis=0)
                    sem_curve = np.std(df_f, axis=0) / np.sqrt(len(df_f)) if len(df_f) > 1 else np.zeros_like(mean_curve)
                    
                    curves.append({
                        'key': f"{channel.name}/{event_label}",
                        'mean': mean_curve.tolist(),
                        'sem': sem_curve.tolist(),
                        'xAxis': time_axis.tolist()
                    })
    
    return AnalysisResult(
        matrices=matrices,
        curves=curves,
        metadata={'mode': 'single', 'events': params.events, 'algorithm': algorithm}
    )


def analyze_multi_event(
    datasets: List[Dataset],
    params: AnalysisParams
) -> AnalysisResult:
    """
    多事件模式分析（time warping）
    """
    return time_warp_alignment(datasets, params.groups, params)
