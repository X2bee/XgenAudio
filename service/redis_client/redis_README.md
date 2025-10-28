# XgenConfig

**PostgreSQL + Redis 기반 설정 관리 시스템**

XgenConfig는 PostgreSQL 데이터베이스와 Redis를 활용하여 애플리케이션 설정을 효율적으로 관리하는 시스템입니다. 설정 값의 우선순위를 DB → Redis → 기본값 순으로 관리하여 데이터 정합성을 보장합니다.

---

### 0. 마이그레이션 - 외부 서비스에서 설정 사용하기 (권장)

**⭐ 권장 방법: `RedisConfigManager`를 직접 사용**

다른 서비스에서 XgenConfig의 설정을 사용하려면 `RedisConfigManager`를 직접 사용하세요.

#### **FastAPI 서비스 예시**

```python
from service.redis_client.redis_config_manager import RedisConfigManager

redis_manager = RedisConfigManager()
app.state.config_composer = redis_manager

# 설정 사용
@app.get("/api/endpoint")
async def some_endpoint(request):
    # env_name으로 설정 값 조회
    api_key = app.state.config_composer.get_config_by_name("OPENAI_API_KEY")
    model = app.state.config_composer.get_config_by_name("OPENAI_MODEL_DEFAULT")

    config_composer = request.app.state.config_composer

    # 카테고리별 설정 조회
    openai_configs = config_composer.get_config_by_category_name("openai")
    # openai_configs = {"openai": {"api_key": "...", "model_default": "..."}}

    return {"api_key": api_key, "model": model}
```
