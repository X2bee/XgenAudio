"""
STT (Speech-to-Text) API 컨트롤러
"""

from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import logging
from typing import Optional
from controller.helper.singletonHelper import get_stt_service
from service.stt.stt_factory import STTFactory
from service.redis.config_utils import get_config_value

logger = logging.getLogger("controller.stt")

router = APIRouter(prefix="/stt", tags=["STT"])

@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio_file: UploadFile = File(...),
    audio_format: Optional[str] = Form(None)
):
    """
    오디오 파일을 텍스트로 변환

    Args:
        audio_file: 업로드된 오디오 파일
        audio_format: 오디오 형식 (선택사항, 파일 확장자에서 자동 추출)

    Returns:
        변환된 텍스트
    """
    
    try:
        stt_service = get_stt_service(request)

        if not audio_format:
            file_extension = audio_file.filename.split('.')[-1].lower() if audio_file.filename else 'wav'
            audio_format = file_extension

        # 지원되는 형식 확인 (webm과 mp4 추가)
        supported_formats = ['wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm', 'mp4']
        if audio_format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {audio_format}. Supported formats: {supported_formats}"
            )

        # 오디오 데이터 읽기
        audio_data = await audio_file.read()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # STT 서비스 사용 가능성 확인
        if not await stt_service.is_available():
            raise HTTPException(status_code=503, detail="STT service is not available")

        # 오디오를 텍스트로 변환
        transcription = await stt_service.transcribe_audio(audio_data, audio_format)

        logger.info("Audio transcription completed for file: %s", audio_file.filename)

        return JSONResponse(content={
            "transcription": transcription,
            "filename": audio_file.filename,
            "audio_format": audio_format,
            "provider": stt_service.get_provider_info().get("provider", "unknown")
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error during audio transcription: %s", e)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.get("/status")
async def get_stt_status(request: Request):
    """
    STT 서비스 상태 확인

    Returns:
        STT 서비스 상태 정보
    """
    try:
        stt_service = get_stt_service(request)
        provider_info = stt_service.get_provider_info()
        is_available = await stt_service.is_available()

        return JSONResponse(content={
            "available": is_available,
            "provider": provider_info.get("provider"),
            "model": provider_info.get("model"),
            "api_key_configured": provider_info.get("api_key_configured", False)
        })

    except Exception as e:
        logger.error("Error getting STT status: %s", e)
        return JSONResponse(content={
            "available": False,
            "provider": None,
            "model": None,
            "error": str(e)
        })

@router.get("/simple-status")
async def get_stt_simple_status(request: Request):
    """
    STT 서비스 상태 확인

    Returns:
        STT 서비스 상태 정보
    """
    try:
        stt_service = get_stt_service(request)
        provider_info = stt_service.get_provider_info()
        is_available = get_config_value("stt.IS_AVAILABLE_STT", default=False)

        return JSONResponse(content={
            "available": is_available,
            "provider": provider_info.get("provider"),
            "model": provider_info.get("model"),
            "api_key_configured": provider_info.get("api_key_configured", False)
        })

    except Exception as e:
        logger.error("Error getting STT status: %s", e)
        return JSONResponse(content={
            "available": False,
            "provider": None,
            "model": None,
            "error": str(e)
        })

@router.post("/refresh")
async def refresh_stt_factory(request: Request):
    try:
        is_available = get_config_value("stt.IS_AVAILABLE_STT", default=False)
        if is_available:
            stt_client = STTFactory.create_stt_client()
            request.app.state.stt_service = stt_client

            logger.info("STT configuration refreshed successfully")
            return {
                "message": "STT configuration refreshed successfully"
            }
        else:
            if hasattr(request.app.state, 'stt_service') and request.app.state.stt_service is not None:
                try:
                    await request.app.state.stt_service.cleanup()
                except Exception as cleanup_e:
                    logger.warning(f"Error during existing STT service cleanup: {cleanup_e}")

                request.app.state.stt_service = None
                import gc
                gc.collect()
            else:
                request.app.state.stt_service = None

            logger.info("STT service disabled in configuration")
            return {
                "message": "STT service is disabled in configuration"
            }

    except Exception as e:
        logger.error(f"Failed to refresh STT config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh STT config: {str(e)}")
