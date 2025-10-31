# 代码优化修复实施指南

本文档提供了具体的代码修复步骤和示例。

---

## 修复 1: 统一 Pydantic V2 API

### 步骤 1: 更新所有 Schema 的 Config

**修改文件**: `backend/app/schemas/user.py`

```python
# 修改前:
class UserRead(UserBase):
    userId: int
    createdAt: datetime
    updatedAt: datetime

    class Config:
        orm_mode = True  # ❌ Pydantic V1

# 修改后:
class UserRead(UserBase):
    userId: int
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)  # ✅ Pydantic V2
```

**需要修改的文件**:
- `backend/app/schemas/user.py` (line 51)
- `backend/app/schemas/tag.py` (line 34)

---

### 步骤 2: 替换所有 .dict() 为 .model_dump()

**修改文件**: `backend/app/services/project_service.py`

```python
# 修改前:
def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.dict(exclude_unset=True)  # ❌
    for field, value in update_data.items():
        setattr(project, field, value)
    # ...

# 修改后:
def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)  # ✅
    for field, value in update_data.items():
        setattr(project, field, value)
    # ...
```

**需要修改的文件和行号**:
- `backend/app/services/project_service.py:37`
- `backend/app/services/data_item_service.py:38, 46`
- `backend/app/services/subject_service.py:37`
- `backend/app/services/tag_service.py:109`
- `backend/app/services/fluorescence_service.py:61, 120, 207, 270, 300, 349`

---

## 修复 2: 统一 DELETE 端点返回值

### 方案 A: 使用 204 No Content (推荐)

**修改文件**: `backend/app/routers/data_items.py`

```python
# 修改前:
@router.delete("/{data_item_id}", status_code=200)
def delete_data_item(
    data_item_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    
    name = data_item.name
    data_item_service.delete_data_item(db, data_item)
    
    log_data(db, current_user.get('userId'), 'delete_data_item', {
        'dataItemId': data_item_id,
        'name': name,
    })
    
    return None  # ❌

# 修改后:
@router.delete("/{data_item_id}", status_code=204)  # ✅ 改为 204
def delete_data_item(
    data_item_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    data_item = data_item_service.get_data_item(db, data_item_id)
    if not data_item:
        raise HTTPException(status_code=404, detail="Data item not found")
    
    name = data_item.name
    data_item_service.delete_data_item(db, data_item)
    
    log_data(db, current_user.get('userId'), 'delete_data_item', {
        'dataItemId': data_item_id,
        'name': name,
    })
    
    # 不需要 return 语句，FastAPI 自动返回 204
```

**需要修改的所有 DELETE 端点**:
- `backend/app/routers/data_items.py:121`
- `backend/app/routers/projects.py:142, 180`
- `backend/app/routers/users.py:132`
- `backend/app/routers/subjects.py:56`
- `backend/app/routers/user_projects.py:77`
- `backend/app/routers/tags.py:158`
- `backend/app/routers/log_entries.py:108`

---

## 修复 3: 创建统一的错误处理工具

### 步骤 1: 创建错误处理模块

**创建文件**: `backend/app/utils/error_handler.py`

```python
"""统一的错误处理工具"""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def handle_integrity_error(e: IntegrityError, entity_name: str = "资源") -> None:
    """
    统一处理数据库唯一性约束错误
    
    Args:
        e: IntegrityError 异常
        entity_name: 实体名称（用于错误消息）
        
    Raises:
        HTTPException: 包含友好错误消息的 400 异常
    """
    raw = ""
    try:
        # 尝试获取原始错误信息
        if hasattr(e, "orig") and e.orig is not None:
            raw = str(e.orig)
        else:
            raw = str(e)
    except Exception:
        raw = str(e)
    
    lower = raw.lower()
    
    # 根据错误信息生成友好的错误消息
    if "username" in lower or "unique_username" in lower:
        detail = "用户名已存在"
    elif "projectname" in lower or "project_name" in lower or "unique_projectname" in lower:
        detail = "项目名称已存在"
    elif "realname" in lower or "real_name" in lower:
        detail = "真实姓名已存在，为避免管理混乱，重名情况请作区分"
    elif "subjectname" in lower or "subject_name" in lower:
        detail = "受试者名称已存在"
    elif "tagname" in lower or "tag_name" in lower:
        detail = "标签名称已存在"
    elif "duplicate" in lower or "unique" in lower:
        detail = f"{entity_name}已存在或违反唯一性约束"
    elif "foreign key" in lower:
        detail = "关联的数据不存在，请检查关联ID是否正确"
    else:
        detail = f"数据库错误: {raw}"
    
    raise HTTPException(status_code=400, detail=detail)


def handle_not_found(entity_name: str, entity_id: int | str) -> None:
    """
    统一处理资源未找到错误
    
    Args:
        entity_name: 实体名称
        entity_id: 实体ID
        
    Raises:
        HTTPException: 404 异常
    """
    raise HTTPException(
        status_code=404,
        detail=f"{entity_name} (ID: {entity_id}) 未找到"
    )


def handle_permission_denied(action: str = "执行此操作") -> None:
    """
    统一处理权限不足错误
    
    Args:
        action: 操作描述
        
    Raises:
        HTTPException: 403 异常
    """
    raise HTTPException(
        status_code=403,
        detail=f"您没有权限{action}"
    )
```

---

### 步骤 2: 在路由中使用错误处理工具

**修改文件**: `backend/app/routers/users.py`

```python
# 修改前 (67 行重复代码):
@router.post("/", response_model=UserRead, status_code=201)
def create_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    try:
        user = user_service.create_user(db, user_in)
        log_user(db, current_user.get('userId'), 'create_user', {
            'userId': user.userId,
            'username': user.username,
            'realName': user.realName,
        })
    except IntegrityError as e:
        db.rollback()
        raw = ""
        try:
            if hasattr(e, "orig") and e.orig is not None:
                raw = str(e.orig)
            else:
                raw = str(e)
        except Exception:
            raw = str(e)

        lower = raw.lower()
        if "username" in lower or "`username`" in lower or "unique_username" in lower:
            detail = "用户名已存在"
        elif "realname" in lower:
            detail = "真实姓名已存在\n为避免管理混乱，重名情况请作区分"
        elif "duplicate" in lower or "unique" in lower:
            detail = f"唯一性冲突: {raw}"
        else:
            detail = f"数据库错误: {raw}"

        raise HTTPException(status_code=400, detail=detail)
    return user

# 修改后 (简洁):
from app.utils.error_handler import handle_integrity_error

@router.post("/", response_model=UserRead, status_code=201)
def create_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    try:
        user = user_service.create_user(db, user_in)
        log_user(db, current_user.get('userId'), 'create_user', {
            'userId': user.userId,
            'username': user.username,
            'realName': user.realName,
        })
        return user
    except IntegrityError as e:
        db.rollback()
        handle_integrity_error(e, "用户")  # ✅ 一行搞定
```

---

## 修复 4: 添加缺失的日志记录

### 示例: 为 subjects.py 添加日志

**修改文件**: `backend/app/routers/subjects.py`

```python
# 添加导入
from app.utils.logger import api_logger as logger

# 修改 list_subjects
@router.get("/", response_model=List[SubjectRead])
def list_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),  # ✅ 添加 current_user
):
    """获取受试者列表（支持分页）"""
    logger.info(f"List subjects requested by user: {current_user.get('username')}")
    subjects = subject_service.list_subjects(db, skip=skip, limit=limit)
    logger.debug(f"Found {len(subjects)} subjects")
    return subjects

# 修改 get_subject
@router.get("/{subject_id}", response_model=SubjectRead)
def get_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """获取受试者详情"""
    logger.info(f"Get subject {subject_id} requested by user: {current_user.get('username')}")
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        logger.warning(f"Subject {subject_id} not found")
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

# 修改 create_subject
@router.post("/", response_model=SubjectRead, status_code=201)
def create_subject(
    subject_in: SubjectCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """创建新受试者"""
    logger.info(f"Create subject requested by user: {current_user.get('username')}, name: {subject_in.subjectName}")
    try:
        subject = subject_service.create_subject(db, subject_in)
        logger.info(f"Subject created successfully: {subject.subjectId}")
        return subject
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create subject: {e}")
        raise HTTPException(status_code=400, detail="Subject already exists")

# 修改 delete_subject
@router.delete("/{subject_id}", status_code=204)
def delete_subject(
    subject_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """删除受试者"""
    logger.info(f"Delete subject {subject_id} requested by user: {current_user.get('username')}")
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        logger.warning(f"Subject {subject_id} not found")
        raise HTTPException(status_code=404, detail="Subject not found")
    
    subject_name = subject.subjectName
    subject_service.delete_subject(db, subject)
    logger.info(f"Subject deleted: {subject_id} ({subject_name})")
    # 不返回任何内容 (204)
```

---

## 修复 5: 添加权限检查

### 步骤 1: 创建权限检查依赖项

**创建文件**: `backend/app/dependencies/permissions.py`

```python
"""权限检查依赖项"""
from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_access_token
from app.utils.roles import is_admin_or_tutor


def require_admin(current_user: dict = Depends(require_access_token)):
    """要求当前用户是管理员"""
    if not is_admin_or_tutor(current_user):
        raise HTTPException(
            status_code=403,
            detail="此操作需要管理员权限"
        )
    return current_user


def require_resource_owner_or_admin(
    resource_user_id: int,
    current_user: dict = Depends(require_access_token)
):
    """要求当前用户是资源所有者或管理员"""
    if is_admin_or_tutor(current_user):
        return current_user
    
    if current_user.get('userId') == resource_user_id:
        return current_user
    
    raise HTTPException(
        status_code=403,
        detail="您只能操作自己创建的资源"
    )


def require_project_member_or_admin(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token)
):
    """要求当前用户是项目成员或管理员"""
    from app.utils.roles import deserialize_roles
    from app.models.project import UserProject
    
    user_roles = deserialize_roles(current_user.get("roles", "[]"))
    
    # 管理员可以访问所有项目
    if "admin" in user_roles or "tutor" in user_roles:
        return current_user
    
    # 检查是否为项目成员
    is_member = db.query(UserProject).filter(
        UserProject.projectId == project_id,
        UserProject.userId == current_user["userId"]
    ).first()
    
    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="您不是该项目的成员"
        )
    
    return current_user
```

---

### 步骤 2: 在路由中使用权限检查

**修改文件**: `backend/app/routers/projects.py`

```python
from app.dependencies.permissions import require_project_member_or_admin

# 为删除操作添加权限检查
@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_project_member_or_admin),  # ✅ 添加权限检查
):
    """
    删除项目
    
    权限要求: 项目成员或管理员
    """
    logger.info(f"Delete project {project_id} requested by user: {current_user.get('username')}")
    project = project_service.get_project(db, project_id)
    if not project:
        logger.warning(f"Project {project_id} not found")
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_name = project.projectName
    project_service.delete_project(db, project)
    
    log_project(db, current_user.get('userId'), 'delete_project', {
        'projectId': project_id,
        'projectName': project_name,
    })
    
    logger.info(f"Project deleted: {project_id} ({project_name})")
```

---

## 修复 6: 统一分页响应格式

### 步骤 1: 创建通用分页 Schema

**创建文件**: `backend/app/schemas/common.py`

```python
"""通用 Schema 定义"""
from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: List[T]
    total: int
    skip: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """简单消息响应"""
    message: str
    code: int = 0
    
    model_config = ConfigDict(from_attributes=True)
```

---

### 步骤 2: 在服务层添加计数函数

**修改文件**: `backend/app/services/project_service.py`

```python
def count_projects(db: Session) -> int:
    """获取项目总数"""
    return db.query(Project).count()


def list_projects_with_total(
    db: Session, 
    skip: int = 0, 
    limit: int = 100
) -> tuple[List[Project], int]:
    """获取项目列表和总数"""
    total = count_projects(db)
    projects = (
        db.query(Project)
        .order_by(Project.createdAt.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return projects, total
```

---

### 步骤 3: 在路由中使用分页响应

**修改文件**: `backend/app/routers/projects.py`

```python
from app.schemas.common import PaginatedResponse

@router.get("/", response_model=PaginatedResponse[ProjectRead])
def list_projects(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    """
    获取项目列表（支持分页）
    
    Returns:
        PaginatedResponse: 包含项目列表和分页信息
    """
    logger.info(f"List projects requested by user: {current_user.get('username')}")
    projects, total = project_service.list_projects_with_total(db, skip=skip, limit=limit)
    logger.debug(f"Found {len(projects)} projects, total: {total}")
    
    return PaginatedResponse(
        items=projects,
        total=total,
        skip=skip,
        limit=limit
    )
```

---

## 自动化修复脚本

### 脚本 1: 批量替换 .dict() 为 .model_dump()

**创建文件**: `backend/scripts/fix_pydantic_v2.py`

```python
#!/usr/bin/env python3
"""
自动将 Pydantic V1 的 .dict() 替换为 V2 的 .model_dump()
"""
import re
from pathlib import Path

def fix_dict_to_model_dump(file_path: Path):
    """替换文件中的 .dict() 为 .model_dump()"""
    content = file_path.read_text(encoding='utf-8')
    
    # 查找所有 .dict() 调用
    pattern = r'\.dict\('
    matches = re.findall(pattern, content)
    
    if matches:
        print(f"Processing {file_path}: found {len(matches)} occurrences")
        
        # 替换为 .model_dump(
        new_content = re.sub(pattern, '.model_dump(', content)
        
        # 写回文件
        file_path.write_text(new_content, encoding='utf-8')
        return True
    
    return False

def main():
    # 处理所有服务文件
    services_dir = Path("app/services")
    routers_dir = Path("app/routers")
    
    count = 0
    for directory in [services_dir, routers_dir]:
        for py_file in directory.glob("*.py"):
            if fix_dict_to_model_dump(py_file):
                count += 1
    
    print(f"\n✅ Fixed {count} files")

if __name__ == "__main__":
    main()
```

运行脚本:
```bash
cd backend
python scripts/fix_pydantic_v2.py
```

---

### 脚本 2: 批量修改 DELETE 端点

**创建文件**: `backend/scripts/fix_delete_endpoints.py`

```python
#!/usr/bin/env python3
"""
自动修改 DELETE 端点的状态码为 204 并移除 return None
"""
import re
from pathlib import Path

def fix_delete_endpoint(file_path: Path):
    """修复 DELETE 端点"""
    content = file_path.read_text(encoding='utf-8')
    
    # 查找 DELETE 端点
    pattern = r'@router\.delete\([^)]+status_code=200\)'
    matches = re.findall(pattern, content)
    
    if matches:
        print(f"Processing {file_path}: found {len(matches)} DELETE endpoints")
        
        # 替换状态码
        new_content = re.sub(
            r'status_code=200',
            'status_code=204',
            content
        )
        
        # 移除 return None (保留其他 return 语句)
        new_content = re.sub(
            r'\n\s+return None\s*$',
            '',
            new_content,
            flags=re.MULTILINE
        )
        
        file_path.write_text(new_content, encoding='utf-8')
        return True
    
    return False

def main():
    routers_dir = Path("app/routers")
    
    count = 0
    for py_file in routers_dir.glob("*.py"):
        if fix_delete_endpoint(py_file):
            count += 1
    
    print(f"\n✅ Fixed {count} files")

if __name__ == "__main__":
    main()
```

---

## 验证修复

### 1. 运行测试

```bash
# 后端测试
cd backend
pytest tests/

# 前端测试
cd frontend
pnpm test
```

### 2. 类型检查

```bash
# Python 类型检查
cd backend
mypy app/

# TypeScript 类型检查
cd frontend
pnpm type-check
```

### 3. 手动验证

1. 启动后端: `uvicorn app.main:app --reload`
2. 访问 Swagger UI: `http://localhost:8000/docs`
3. 测试所有 DELETE 端点，确认返回 204
4. 测试所有创建端点，确认错误消息友好

---

## 完成清单

修复完成后，请确认:

- [ ] 所有 Schema 使用 `ConfigDict(from_attributes=True)`
- [ ] 所有代码使用 `.model_dump()` 而不是 `.dict()`
- [ ] 所有 DELETE 端点返回 204
- [ ] 所有路由有适当的日志记录
- [ ] 所有敏感操作有权限检查
- [ ] 运行测试全部通过
- [ ] 类型检查无错误
- [ ] 更新文档

---

**注意**: 在进行大规模代码修改前，请务必:
1. 创建新的 Git 分支
2. 提交当前代码
3. 逐个模块测试修复

---

最后更新: 2025-10-31
