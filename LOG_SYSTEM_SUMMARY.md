# 日志系统完善总结

## 概述
本次更新全面完善了系统的日志记录和查询功能，包括后端日志记录、权限控制、前端日志查询页面等。

## 完成的工作

### 1. 数据库架构更新

#### 修改的文件：
- `backend/sql.sql`
- `backend/app/models/log_entry.py`

#### 主要变更：
- 添加 `actionType` 字段用于操作类型分类（AUTH, PROJECT, USER, DATA, SUBJECT, TAG, FILE, ANALYSIS）
- 为 `actionType`、`userId`、`createdAt` 添加索引以提升查询性能
- 更新示例数据以包含 `actionType`

### 2. 后端Schema更新

#### 修改的文件：
- `backend/app/schemas/log_entry.py`

#### 主要变更：
- 更新 `LogEntryBase` 添加 `actionType` 字段
- 更新 `LogEntryRead` 使用 Pydantic V2 的 `model_config`
- 添加 `username` 字段用于前端显示
- 新增 `LogEntryQuery` Schema 用于查询参数验证

### 3. 后端Service层增强

#### 修改的文件：
- `backend/app/services/log_entry_service.py`

#### 主要变更：
- `list_log_entries` 函数增强：
  - 支持按 `actionType` 过滤
  - 支持按 `action` 模糊搜索
  - 支持时间范围过滤（`start_time`, `end_time`）
  - 返回总记录数用于分页
- 新增 `get_action_types()` 函数获取所有操作类型

### 4. 后端Router层完善

#### 修改的文件：
- `backend/app/routers/log_entries.py`

#### 主要变更：
- **权限控制**：
  - Admin 和 Tutor 可以查看所有用户的日志
  - 普通用户只能查看自己的日志
- **查询接口增强**：
  - 添加 `actionType`、`action`、`startTime`、`endTime` 查询参数
  - 返回格式改为 `{items: [], total: number}`
  - 自动填充 `username` 字段
- **新增接口**：
  - `GET /log-entries/action-types` - 获取所有操作类型
- **删除接口**：
  - 仅 Admin/Tutor 可以删除日志

### 5. 日志记录工具函数

#### 新增文件：
- `backend/app/utils/log_helper.py`

#### 功能：
- 提供便捷的日志记录函数
- 定义操作类型常量 `ActionType`
- 提供分类日志记录函数：
  - `log_auth()` - 认证相关
  - `log_project()` - 项目管理
  - `log_user()` - 用户管理
  - `log_data()` - 数据项管理
  - `log_subject()` - 受试者管理
  - `log_tag()` - 标签管理
  - `log_file()` - 文件操作
  - `log_analysis()` - 数据分析

### 6. 关键路由添加日志记录

#### 修改的文件：
- `backend/app/routers/auth.py`
  - 登录成功/失败
  - 登出
  
- `backend/app/routers/projects.py`
  - 创建项目
  - 更新项目
  - 删除项目
  
- `backend/app/routers/users.py`
  - 创建用户
  - 更新用户
  - 删除用户
  
- `backend/app/routers/data_items.py`
  - 创建数据项
  - 更新数据项
  - 删除数据项

#### 日志记录内容：
- 操作用户ID
- 操作类型
- 操作名称
- 详细信息（如对象ID、名称、变更内容等）

### 7. 前端API封装

#### 新增文件：
- `frontend/apps/web-antd/src/api/log.ts`

#### 功能：
- `listLogs()` - 查询日志列表
- `getActionTypes()` - 获取操作类型
- `getLog()` - 获取单条日志详情
- `deleteLog()` - 删除日志（仅admin）

### 8. 前端日志查询页面

#### 新增文件：
- `frontend/apps/web-antd/src/views/log/index.vue`

#### 功能特性：
- **查询过滤**：
  - 按用户名筛选
  - 按操作类型筛选
  - 按具体操作筛选
  - 按时间范围筛选
  
- **列表展示**：
  - 日志ID、操作用户、操作类型、具体操作、详情、操作时间
  - 操作类型使用彩色标签显示
  - 详情字段支持展开查看完整JSON
  
- **操作功能**：
  - 查看详情（弹窗显示完整日志信息）
  - 删除日志（仅admin，多选删除）
  - 导出日志（预留功能）
  - 刷新列表
  
- **操作类型映射**：
  - AUTH - 认证（蓝色）
  - PROJECT - 项目（绿色）
  - USER - 用户（橙色）
  - DATA - 数据（紫色）
  - SUBJECT - 受试者（青色）
  - TAG - 标签（洋红色）
  - FILE - 文件（极客蓝）
  - ANALYSIS - 分析（火山色）

### 9. 路由配置

#### 新增文件：
- `frontend/apps/web-antd/src/router/routes/modules/log.ts`

#### 配置：
- 路径：`/log`
- 图标：`lucide:file-text`
- 标题：系统日志
- 排序：99（显示在菜单底部）

## 权限控制设计

### 查询权限：
- **Admin/Tutor**：可以查看所有用户的日志
- **普通用户**：只能查看自己的操作日志

### 删除权限：
- **仅 Admin/Tutor**：可以删除日志记录
- **普通用户**：无删除权限

## 使用方法

### 启动系统：

#### 后端：
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

#### 前端：
```bash
cd frontend
pnpm dev:antd
```

### 访问日志页面：
1. 登录系统
2. 在左侧菜单找到"系统日志"
3. 可以使用各种筛选条件查询日志
4. Admin用户可以删除日志记录

### 在代码中记录日志：

```python
from app.utils.log_helper import log_project, log_user, log_auth

# 在路由函数中
def create_something(
    payload: CreatePayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_access_token),
):
    # ... 业务逻辑 ...
    
    # 记录日志
    log_project(db, current_user.get('userId'), 'create_something', {
        'id': new_item.id,
        'name': new_item.name,
    })
    
    return new_item
```

## 数据库迁移说明

如果数据库已存在，需要执行以下SQL更新：

```sql
-- 添加 actionType 字段
ALTER TABLE LogEntry 
ADD COLUMN actionType VARCHAR(50) COMMENT '操作类型分类：AUTH(认证), PROJECT(项目), USER(用户), DATA(数据), SUBJECT(受试者), TAG(标签), FILE(文件), ANALYSIS(分析)';

-- 添加索引
ALTER TABLE LogEntry ADD INDEX idx_action_type (actionType);
ALTER TABLE LogEntry ADD INDEX idx_user_id (userId);
ALTER TABLE LogEntry ADD INDEX idx_created_at (createdAt);

-- 更新现有日志的 actionType（根据 action 字段推断）
UPDATE LogEntry SET actionType = 'AUTH' WHERE action LIKE '%login%' OR action LIKE '%logout%';
UPDATE LogEntry SET actionType = 'PROJECT' WHERE action LIKE '%project%';
UPDATE LogEntry SET actionType = 'USER' WHERE action LIKE '%user%';
UPDATE LogEntry SET actionType = 'TAG' WHERE action LIKE '%tag%';
UPDATE LogEntry SET actionType = 'FILE' WHERE action LIKE '%file%' OR action LIKE '%upload%';
UPDATE LogEntry SET actionType = 'DATA' WHERE action LIKE '%data%';
```

或者直接删除旧数据重新创建：

```bash
# 备份数据库（可选）
mysqldump -u root -p sci_platform > sci_platform_backup.sql

# 重新执行SQL脚本
mysql -u root -p sci_platform < backend/sql.sql
```

## 测试检查清单

- [ ] 后端启动无错误
- [ ] 前端启动无错误
- [ ] 可以访问日志页面（/log）
- [ ] Admin用户可以看到所有日志
- [ ] 普通用户只能看到自己的日志
- [ ] 操作类型筛选正常工作
- [ ] 时间范围筛选正常工作
- [ ] 查看详情功能正常
- [ ] 删除日志功能正常（仅admin）
- [ ] 创建项目后自动记录日志
- [ ] 登录/登出自动记录日志
- [ ] 用户管理操作自动记录日志
- [ ] 数据项操作自动记录日志

## 后续改进建议

1. **日志导出功能**：实现导出为CSV或Excel文件
2. **日志归档**：定期归档旧日志到历史表
3. **实时日志**：使用WebSocket实现实时日志推送
4. **日志统计**：添加日志统计仪表板
5. **敏感信息脱敏**：对密码等敏感信息自动脱敏
6. **日志清理策略**：定期清理超过保留期的日志
7. **更多操作记录**：为更多模块（如标签、受试者、文件等）添加日志记录

## 相关文件清单

### 后端文件：
- `backend/sql.sql` - 数据库表结构（已更新）
- `backend/app/models/log_entry.py` - LogEntry模型（已更新）
- `backend/app/schemas/log_entry.py` - 日志Schema（已更新）
- `backend/app/services/log_entry_service.py` - 日志服务（已增强）
- `backend/app/routers/log_entries.py` - 日志路由（已完善）
- `backend/app/utils/log_helper.py` - 日志工具函数（新增）
- `backend/app/routers/auth.py` - 认证路由（已添加日志）
- `backend/app/routers/projects.py` - 项目路由（已添加日志）
- `backend/app/routers/users.py` - 用户路由（已添加日志）
- `backend/app/routers/data_items.py` - 数据项路由（已添加日志）

### 前端文件：
- `frontend/apps/web-antd/src/api/log.ts` - 日志API（新增）
- `frontend/apps/web-antd/src/views/log/index.vue` - 日志页面（新增）
- `frontend/apps/web-antd/src/router/routes/modules/log.ts` - 日志路由配置（新增）
