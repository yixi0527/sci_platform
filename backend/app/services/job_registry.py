"""
任务管理与进度跟踪
- 内存字典存储任务状态
- 可选落盘到 JSON 文件
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobRegistry:
    """
    任务注册表（单例模式）
    """
    _instance = None
    _jobs: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._jobs = {}
        return cls._instance
    
    def create_job(
        self,
        job_id: str,
        project_id: int,
        params: dict,
        persist_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新任务
        
        Args:
            job_id: 任务 ID
            project_id: 项目 ID
            params: 任务参数
            persist_dir: 可选的持久化目录
        
        Returns:
            任务信息字典
        """
        job = {
            "jobId": job_id,
            "projectId": project_id,
            "status": JobStatus.QUEUED,
            "progress": 0,
            "message": "Task queued",
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "params": params,
            "persistDir": persist_dir
        }
        self._jobs[job_id] = job
        
        # 持久化
        if persist_dir:
            self._persist_job(job_id)
        
        return job
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新任务状态
        """
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = progress
        if message is not None:
            job["message"] = message
        if error is not None:
            job["error"] = error
        
        job["updatedAt"] = datetime.utcnow().isoformat()
        
        # 持久化
        if job.get("persistDir"):
            self._persist_job(job_id)
        
        return job
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        """
        return self._jobs.get(job_id)
    
    def list_jobs(self) -> list[Dict[str, Any]]:
        """
        获取所有任务列表
        """
        return list(self._jobs.values())
    
    def delete_job(self, job_id: str) -> bool:
        """
        删除任务
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False
    
    def _persist_job(self, job_id: str):
        """
        将任务状态持久化到 JSON 文件
        """
        job = self._jobs.get(job_id)
        if not job or not job.get("persistDir"):
            return
        
        try:
            persist_dir = Path(job["persistDir"])
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            status_file = persist_dir / "status.json"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(job, f, indent=2, ensure_ascii=False)
        except (OSError, IOError) as e:
            # 持久化失败不应影响任务执行
            print(f"Failed to persist job {job_id}: {e}")
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        清理旧任务（超过指定小时数且已完成或失败）
        
        Args:
            max_age_hours: 任务最大保留时间（小时）
        """
        current_time = datetime.utcnow()
        to_delete = []
        
        for job_id, job in self._jobs.items():
            # 只清理已完成或失败的任务
            if job["status"] not in [JobStatus.SUCCEEDED, JobStatus.FAILED]:
                continue
            
            created_at = datetime.fromisoformat(job["createdAt"])
            age_hours = (current_time - created_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                to_delete.append(job_id)
        
        for job_id in to_delete:
            self.delete_job(job_id)
        
        return len(to_delete)


# 全局单例
job_registry = JobRegistry()
