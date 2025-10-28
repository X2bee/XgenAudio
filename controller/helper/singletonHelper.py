# controller/helper/singletonHelper.py
from fastapi import HTTPException, Request
from service.redis_client.redis_config_manager import RedisConfigManager
from service.database.connection import AppDatabaseManager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.stt.huggingface_stt import HuggingFaceSTT

def get_db_manager(request: Request) -> AppDatabaseManager:
    """데이터베이스 매니저 의존성 주입"""
    if hasattr(request.app.state, 'app_db') and request.app.state.app_db:
        return request.app.state.app_db
    else:
        raise HTTPException(status_code=500, detail="Database connection not available")

def get_config_composer(request: Request) -> RedisConfigManager:
    """request.app.state에서 config_composer 가져오기"""
    redis_manager = RedisConfigManager()
    request.app.state.config_composer = redis_manager
    return request.app.state.config_composer

def get_stt_service(request: Request) -> 'HuggingFaceSTT':
    """STT 서비스 의존성 주입"""
    if hasattr(request.app.state, 'stt_service') and request.app.state.stt_service:
        return request.app.state.stt_service
    else:
        raise HTTPException(status_code=500, detail="STT service not available")

def get_tts_service(request: Request):
    """TTS 서비스 의존성 주입"""
    if hasattr(request.app.state, 'tts_service') and request.app.state.tts_service:
        return request.app.state.tts_service
    else:
        raise HTTPException(status_code=500, detail="TTS service not available")