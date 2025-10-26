"""
XgenAudio FastAPI Application
음성 인식(STT) 및 음성 합성(TTS) 서비스를 제공하는 API 서버
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from controller.router import audio_router
from service.stt.stt_factory import STTFactory
from service.tts.tts_factory import TTSFactory
from service.redis.config_utils import get_stt_config, get_tts_config

# 환경 변수 로드
load_dotenv()

# 로깅 설정
log_level = logging.DEBUG if os.getenv("DEBUG_MODE", "false").lower() == "true" else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info(f"로그 레벨: {logging.getLevelName(log_level)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시
    logger.info("🚀 XgenAudio API 서버 시작 중...")

    # STT 서비스 초기화
    try:
        logger.info("STT 설정 확인 중...")
        stt_config = get_stt_config()
        is_stt_available = stt_config.is_available_stt
        logger.info(f"STT 활성화 상태: {is_stt_available}")

        if is_stt_available:
            logger.info("STT 서비스 초기화 중...")
            app.state.stt_service = STTFactory.create_stt_client()
            logger.info("✅ STT 서비스 초기화 완료")
        else:
            app.state.stt_service = None
            logger.info("⚠️  STT 서비스 비활성화됨")
    except Exception as e:
        logger.error(f"❌ STT 서비스 초기화 실패: {e}", exc_info=True)
        app.state.stt_service = None

    # TTS 서비스 초기화
    try:
        tts_config = get_tts_config()
        logger.info("TTS 설정 확인 중...")
        is_tts_available = tts_config.is_available_tts
        logger.info(f"TTS 활성화 상태: {is_tts_available}")

        if is_tts_available:
            logger.info("TTS 서비스 초기화 중...")
            app.state.tts_service = TTSFactory.create_tts_client()
            logger.info("✅ TTS 서비스 초기화 완료")
        else:
            app.state.tts_service = None
            logger.info("⚠️  TTS 서비스 비활성화됨")
    except Exception as e:
        logger.error(f"❌ TTS 서비스 초기화 실패: {e}", exc_info=True)
        app.state.tts_service = None

    logger.info("✨ XgenAudio API 서버 시작 완료")

    yield

    # 종료 시
    logger.info("🛑 XgenAudio API 서버 종료 중...")

    # STT 서비스 정리
    if hasattr(app.state, 'stt_service') and app.state.stt_service:
        try:
            await STTFactory.cleanup_instance()
            logger.info("✅ STT 서비스 정리 완료")
        except Exception as e:
            logger.error(f"❌ STT 서비스 정리 실패: {e}")

    # TTS 서비스 정리
    if hasattr(app.state, 'tts_service') and app.state.tts_service:
        try:
            await TTSFactory.cleanup_instance()
            logger.info("✅ TTS 서비스 정리 완료")
        except Exception as e:
            logger.error(f"❌ TTS 서비스 정리 실패: {e}")

    logger.info("👋 XgenAudio API 서버 종료 완료")


# FastAPI 앱 생성
app = FastAPI(
    title="XgenAudio API",
    description="음성 인식(STT) 및 음성 합성(TTS) 서비스를 제공하는 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(audio_router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "XgenAudio API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "stt": "/api/stt",
            "tts": "/api/tts"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "services": {
            "stt": hasattr(app.state, 'stt_service') and app.state.stt_service is not None,
            "tts": hasattr(app.state, 'tts_service') and app.state.tts_service is not None
        }
    }


if __name__ == "__main__":
    import uvicorn

    # 환경 변수에서 설정 읽기
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8020"))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
