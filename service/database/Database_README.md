# Database Management Guide

이 프로젝트는 PostgreSQL 및 SQLite를 지원하는 데이터베이스 관리 시스템을 제공합니다.

## 목차
- [데이터베이스 설정](#데이터베이스-설정)
- [AppDatabaseManager 사용법](#appdatabasemanager-사용법)
- [스키마 정보 조회](#스키마-정보-조회)
- [CRUD 작업](#crud-작업)
- [고급 쿼리](#고급-쿼리)

---

## 데이터베이스 설정

### 1. 환경 변수 설정

PostgreSQL을 사용하는 경우 다음 환경 변수를 설정하세요 (아래는 현재 기본설정 예시):

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=plateerag
POSTGRES_USER=ailab
POSTGRES_PASSWORD=ailab123
AUTO_MIGRATION=true
```

### 2. 데이터베이스 설정 클래스

간단한 설정 클래스를 생성하여 데이터베이스 연결 정보를 제공합니다:

```python
import os

class SimpleDBConfig:
    def __init__(self):
        self.POSTGRES_HOST = type('obj', (object,), {'value': os.getenv("POSTGRES_HOST", "localhost")})()
        self.POSTGRES_PORT = type('obj', (object,), {'value': os.getenv("POSTGRES_PORT", "5432")})()
        self.POSTGRES_DB = type('obj', (object,), {'value': os.getenv("POSTGRES_DB", "plateerag")})()
        self.POSTGRES_USER = type('obj', (object,), {'value': os.getenv("POSTGRES_USER", "ailab")})()
        self.POSTGRES_PASSWORD = type('obj', (object,), {'value': os.getenv("POSTGRES_PASSWORD", "ailab123")})()
        self.DATABASE_TYPE = type('obj', (object,), {'value': "postgresql"})()  # PostgreSQL 고정
        self.AUTO_MIGRATION = type('obj', (object,), {'value': os.getenv("AUTO_MIGRATION", "true").lower() in ('true', '1', 'yes', 'on')})()

database_config = SimpleDBConfig()
```

### 3. 애플리케이션에 데이터베이스 등록

FastAPI 애플리케이션 초기화 시 데이터베이스를 설정합니다:

```python
from service.database.connection import AppDatabaseManager

# 데이터베이스 설정 로드
database_config = SimpleDBConfig()
logger.info("✅ PostgreSQL configuration loaded from environment variables!")

# AppDatabaseManager 초기화
app_db = AppDatabaseManager(database_config)

# 데이터베이스 초기화 (테이블 생성 및 마이그레이션)
if app_db.initialize_database():
    app.state.app_db = app_db
    logger.info("✅ Application database initialized successfully!")
else:
    logger.error("❌ Failed to initialize application database")
```

---

## AppDatabaseManager 사용법

### 다른 서비스에서 데이터베이스 접근

애플리케이션의 다른 서비스나 컨트롤러에서 `app_db`를 가져와 사용할 수 있습니다:

```python
from fastapi import Request

def some_service_function(request: Request):
    # FastAPI request 객체를 통해 app_db 접근
    app_db = request.app.state.app_db

    # 데이터베이스 작업 수행
    users = app_db.find_all(User, limit=100)
    return users
```

또는 직접 import하여 사용:

```python
from service.database.connection import AppDatabaseManager

# 기존에 초기화된 인스턴스 사용
# (애플리케이션 시작 시 app.state.app_db에 등록됨)
```

---

## 스키마 정보 조회

### 1. 테이블 스키마 조회 (`get_table_schema`)

특정 테이블의 스키마 정보를 조회합니다:

```python
app_db = request.app.state.app_db

# 테이블 스키마 조회
schema_info = app_db.get_table_schema("users")

# PostgreSQL 결과 예시:
# [
#     {
#         'column_name': 'id',
#         'data_type': 'integer',
#         'character_maximum_length': None,
#         'is_nullable': 'NO',
#         'column_default': "nextval('users_id_seq'::regclass)"
#     },
#     {
#         'column_name': 'username',
#         'data_type': 'character varying',
#         'character_maximum_length': 100,
#         'is_nullable': 'NO',
#         'column_default': None
#     },
#     ...
# ]

# SQLite 결과 예시:
# [
#     {
#         'cid': 0,
#         'name': 'id',
#         'type': 'INTEGER',
#         'notnull': 1,
#         'dflt_value': None,
#         'pk': 1
#     },
#     ...
# ]

for column in schema_info:
    if app_db.config_db_manager.db_type == "postgresql":
        print(f"Column: {column['column_name']}, Type: {column['data_type']}")
    else:  # SQLite
        print(f"Column: {column['name']}, Type: {column['type']}")
```

### 2. 테이블 이름으로 BaseModel 생성 (`get_base_model_by_table_name`)

데이터베이스 스키마를 기반으로 동적으로 Pydantic BaseModel을 생성합니다:

```python
app_db = request.app.state.app_db

# 테이블 이름으로 동적 모델 생성
DynamicUserModel = app_db.get_base_model_by_table_name("users")

if DynamicUserModel:
    # 생성된 모델로 데이터 조회
    users = app_db.find_all(DynamicUserModel, limit=10)

    for user in users:
        print(f"User ID: {user.id}, Username: {user.username}")
else:
    print("Failed to create model from table schema")
```

**활용 사례:**
- 런타임에 테이블 구조를 파악하여 동적으로 모델 생성
- 관리자 페이지에서 임의의 테이블 데이터 조회
- 스키마 마이그레이션 검증

### 3. 전체 테이블 목록 조회 (`get_table_list`)

데이터베이스의 모든 테이블 목록을 조회합니다:

```python
app_db = request.app.state.app_db

# 전체 테이블 목록 조회
tables = app_db.get_table_list()

# PostgreSQL 결과:
# [
#     {
#         'schema_name': 'public',
#         'table_name': 'users',
#         'table_owner': 'ailab'
#     },
#     ...
# ]

# SQLite 결과:
# [
#     {
#         'table_name': 'users',
#         'table_type': 'table',
#         'create_sql': 'CREATE TABLE users (...)'
#     },
#     ...
# ]

for table in tables:
    print(f"Table: {table['table_name']}")
```

---

## CRUD 작업

### 1. 생성 (Create)

```python
from service.database.models.user import User

app_db = request.app.state.app_db

# 새 사용자 생성
new_user = User(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe"
)

# 데이터베이스에 삽입
result = app_db.insert(new_user)

if result and result.get("result") == "success":
    user_id = result.get("id")
    print(f"User created with ID: {user_id}")
```

### 2. 조회 (Read)

#### ID로 조회

```python
# ID로 사용자 조회
user = app_db.find_by_id(User, record_id=1)

if user:
    print(f"Found user: {user.username}")
```

#### 전체 조회

```python
# 모든 사용자 조회 (페이징)
users = app_db.find_all(User, limit=50, offset=0)

for user in users:
    print(f"User: {user.username}")
```

#### 조건부 조회

```python
# 조건으로 사용자 조회
users = app_db.find_by_condition(
    User,
    conditions={"username__like__": "john"},
    limit=10
)

# 여러 조건 조합
active_users = app_db.find_by_condition(
    User,
    conditions={
        "is_active": True,
        "created_at__gte__": "2024-01-01"
    },
    orderby="created_at",
    orderby_asc=False
)
```

**지원되는 조건 연산자:**
- `__like__`: LIKE 검색 (대소문자 구분 없음)
- `__notlike__`: NOT LIKE 검색
- `__not__`: 같지 않음 (!=)
- `__gte__`: 크거나 같음 (>=)
- `__lte__`: 작거나 같음 (<=)
- `__gt__`: 큼 (>)
- `__lt__`: 작음 (<)
- `__in__`: IN 절 (리스트 값)
- `__notin__`: NOT IN 절 (리스트 값)

### 3. 업데이트 (Update)

```python
# 사용자 조회
user = app_db.find_by_id(User, record_id=1)

if user:
    # 데이터 수정
    user.email = "newemail@example.com"
    user.full_name = "John Updated Doe"

    # 데이터베이스에 반영
    result = app_db.update(user)

    if result and result.get("result") == "success":
        print("User updated successfully")
```

#### 리스트 컬럼 업데이트

```python
# 리스트 필드가 있는 모델 업데이트
from service.database.models.workflow import Workflow

result = app_db.update_list_columns(
    Workflow,
    updates={
        "tags": ["ai", "automation", "production"],
        "name": "Updated Workflow"
    },
    conditions={"id": 1}
)
```

### 4. 삭제 (Delete)

#### ID로 삭제

```python
# ID로 사용자 삭제
success = app_db.delete(User, record_id=1)

if success:
    print("User deleted successfully")
```

#### 조건으로 삭제

```python
# 조건으로 삭제
success = app_db.delete_by_condition(
    User,
    conditions={
        "is_active": False,
        "last_login__lt__": "2023-01-01"
    }
)

if success:
    print("Inactive users deleted")
```

---

## 고급 쿼리

### 1. 원시 SQL 쿼리 실행

```python
# SELECT 쿼리 실행
result = app_db.execute_raw_query(
    "SELECT * FROM users WHERE username LIKE %s",
    params=("%john%",)
)

if result["success"]:
    data = result["data"]
    print(f"Found {result['row_count']} rows")

    for row in data:
        print(row)
else:
    print(f"Query failed: {result['error']}")
```

**보안 제한사항:**
- `DROP`, `DELETE`, `TRUNCATE` 등 위험한 키워드는 차단됨
- 쿼리 길이 제한: 최대 1000자
- 결과 제한: 최대 1000행 (초과 시 자동 truncate)

### 2. 특정 컬럼만 조회

```python
# 특정 컬럼만 선택
users = app_db.find_all(
    User,
    select_columns=["id", "username", "email"],
    limit=100
)

# 특정 컬럼 제외
users = app_db.find_all(
    User,
    ignore_columns=["password_hash", "api_key"],
    limit=100
)
```

### 3. JOIN 쿼리 (User 정보 포함)

```python
from service.database.models.workflow import Workflow

# user 정보와 함께 workflow 조회
workflows = app_db.find_all(
    Workflow,
    join_user=True,
    limit=50
)

for workflow in workflows:
    print(f"Workflow: {workflow.name}")
    print(f"Created by: {workflow.username} ({workflow.full_name})")
```

### 4. 정렬 옵션

```python
# 내림차순 정렬 (기본값)
users = app_db.find_by_condition(
    User,
    conditions={"is_active": True},
    orderby="created_at",
    orderby_asc=False
)

# 오름차순 정렬
users = app_db.find_by_condition(
    User,
    conditions={},
    orderby="username",
    orderby_asc=True
)
```

---

## 주요 클래스 파일

### 1. `/app/service/database/database_manager.py`
- `DatabaseManager`: 저수준 데이터베이스 연결 및 쿼리 실행 관리
- PostgreSQL과 SQLite 모두 지원
- 연결 관리, 쿼리 실행, 마이그레이션 기능 제공

### 2. `/app/service/database/connection.py`
- `AppDatabaseManager`: 고수준 ORM 스타일 데이터베이스 작업 관리
- BaseModel 기반 CRUD 작업
- 스키마 조회 및 동적 모델 생성
- 조건부 쿼리, JOIN, 원시 SQL 실행 지원

---

## 사용 예시: 실제 서비스에서 활용

```python
# controller/workflow_controller.py

from fastapi import APIRouter, Request, HTTPException
from service.database.models.workflow import Workflow

router = APIRouter()

@router.get("/workflows")
async def get_workflows(request: Request, limit: int = 50, offset: int = 0):
    """워크플로우 목록 조회"""
    app_db = request.app.state.app_db

    workflows = app_db.find_all(
        Workflow,
        limit=limit,
        offset=offset,
        join_user=True
    )

    return {
        "success": True,
        "data": workflows,
        "count": len(workflows)
    }

@router.get("/workflows/{workflow_id}")
async def get_workflow(request: Request, workflow_id: int):
    """특정 워크플로우 조회"""
    app_db = request.app.state.app_db

    workflow = app_db.find_by_id(Workflow, record_id=workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "success": True,
        "data": workflow
    }

@router.post("/workflows")
async def create_workflow(request: Request, workflow_data: dict):
    """워크플로우 생성"""
    app_db = request.app.state.app_db

    new_workflow = Workflow(**workflow_data)
    result = app_db.insert(new_workflow)

    if result and result.get("result") == "success":
        return {
            "success": True,
            "workflow_id": result.get("id")
        }

    raise HTTPException(status_code=500, detail="Failed to create workflow")

@router.delete("/workflows/{workflow_id}")
async def delete_workflow(request: Request, workflow_id: int):
    """워크플로우 삭제"""
    app_db = request.app.state.app_db

    success = app_db.delete(Workflow, record_id=workflow_id)

    if success:
        return {"success": True, "message": "Workflow deleted"}

    raise HTTPException(status_code=404, detail="Workflow not found")
```

---

## 마이그레이션

데이터베이스 스키마 변경은 자동으로 감지되어 마이그레이션됩니다:

```python
# AUTO_MIGRATION=true 설정 시 자동 실행
app_db.initialize_database()  # 자동으로 run_migrations() 호출

# 수동 마이그레이션
app_db.run_migrations()
```

마이그레이션은 다음을 수행합니다:
- 등록된 모델과 실제 테이블 스키마 비교
- 누락된 컬럼 자동 추가
- 인덱스 생성

---

## 연결 종료

```python
# 애플리케이션 종료 시 연결 해제
app_db.close()
```

---

## 요약

1. **설정**: `SimpleDBConfig` 클래스로 데이터베이스 연결 정보 제공
2. **초기화**: `AppDatabaseManager`를 초기화하고 `app.state.app_db`에 등록
3. **사용**: 다른 서비스에서 `request.app.state.app_db`로 접근하여 CRUD 작업 수행
4. **스키마 조회**: `get_table_schema()`, `get_base_model_by_table_name()` 등으로 런타임에 스키마 정보 확인
5. **고급 기능**: 조건부 쿼리, JOIN, 원시 SQL 실행 등 다양한 데이터베이스 작업 지원
