# controller/helper/singletonHelper.py
from fastapi import HTTPException, Request

def get_stt_service(request: Request):
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