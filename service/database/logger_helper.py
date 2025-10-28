import logging
import inspect
from typing import Dict, Optional
from fastapi import Request, HTTPException

logger = logging.getLogger("backend-logger")


class BackendLogger:
    def __init__(self, request: Request, user_id: Optional[int] = None):
        self.request = request
        self.user_id = user_id
        self._function_name = None
        self._api_endpoint = None

        # app_db는 request에서 가져옴 (lazy loading)
        self._app_db = None
        # BackendLogs 모델은 app_db에서 가져옴 (lazy loading)
        self._backend_logs_model = None

        # 자동으로 함수명과 API 엔드포인트 추출
        self._extract_context_info()

    @property
    def app_db(self):
        """Request에서 데이터베이스 매니저를 가져옴 (lazy loading)"""
        if self._app_db is None:
            if hasattr(self.request.app.state, 'app_db') and self.request.app.state.app_db:
                self._app_db = self.request.app.state.app_db
            else:
                raise HTTPException(status_code=500, detail="Database connection not available")
        return self._app_db

    @property
    def backend_logs_model(self):
        """app_db에서 BackendLogs 모델을 가져옴 (lazy loading)"""
        if self._backend_logs_model is None:
            self._backend_logs_model = self.app_db.get_base_model_by_table_name('backend_logs')
            if self._backend_logs_model is None:
                raise HTTPException(status_code=500, detail="BackendLogs model not found")
        return self._backend_logs_model

    def _extract_context_info(self):
        try:
            # Request 객체에서 API 엔드포인트 추출
            if self.request:
                # FastAPI의 경우 request.url.path에서 엔드포인트 추출
                path = self.request.url.path
                # '/api/stt/transcribe' -> 'api/stt/transcribe'
                if path.startswith('/'):
                    self._api_endpoint = path[1:]  # '/' 제거
                else:
                    self._api_endpoint = path

        except Exception as e:
            logger.warning(f"Could not extract context info: {str(e)}")

    def _log(self, level: str, message: str, metadata: Optional[Dict] = None,
             function_name: Optional[str] = None, api_endpoint: Optional[str] = None):
        """내부 로깅 메서드"""
        try:
            # 파라미터가 제공되지 않으면 자동 추출된 값 사용
            func_name = function_name or self._function_name or ''
            endpoint = api_endpoint or self._api_endpoint or ''

            log_id = f"LOG__{self.user_id}__{func_name}"

            # app_db에서 동적으로 가져온 BackendLogs 모델 사용
            BackendLogsModel = self.backend_logs_model
            log_entry = BackendLogsModel(
                user_id=self.user_id,
                log_id=log_id,
                log_level=level,
                message=message,
                function_name=func_name,
                api_endpoint=endpoint,
                metadata=metadata or {}
            )
            self.app_db.insert(log_entry)
            logger.info(f"Logged backend data with log_id: {log_id}")

        except Exception as e:
            logger.error(f"Error logging backend data: {str(e)}")

    def success(self, message: str, metadata: Optional[Dict] = None,
                function_name: Optional[str] = None, api_endpoint: Optional[str] = None):
        """성공 로그 기록"""
        self._log("INFO", f"SUCCESS: {message}", metadata, function_name, api_endpoint)

    def info(self, message: str, metadata: Optional[Dict] = None,
             function_name: Optional[str] = None, api_endpoint: Optional[str] = None):
        """정보 로그 기록"""
        self._log("INFO", message, metadata, function_name, api_endpoint)

    def warn(self, message: str, metadata: Optional[Dict] = None,
             function_name: Optional[str] = None, api_endpoint: Optional[str] = None):
        """경고 로그 기록"""
        self._log("WARN", message, metadata, function_name, api_endpoint)

    def warning(self, message: str, metadata: Optional[Dict] = None,
                function_name: Optional[str] = None, api_endpoint: Optional[str] = None):
        """경고 로그 기록 (warn의 별칭)"""
        self.warn(message, metadata, function_name, api_endpoint)

    def error(self, message: str, metadata: Optional[Dict] = None,
              function_name: Optional[str] = None, api_endpoint: Optional[str] = None,
              exception: Optional[Exception] = None):
        """에러 로그 기록"""
        error_message = message
        if exception:
            error_message = f"{message}: {str(exception)}"
            if metadata is None:
                metadata = {}
            metadata['exception_type'] = type(exception).__name__
            metadata['exception_details'] = str(exception)

        self._log("ERROR", error_message, metadata, function_name, api_endpoint)

    def debug(self, message: str, metadata: Optional[Dict] = None,
              function_name: Optional[str] = None, api_endpoint: Optional[str] = None):
        """디버그 로그 기록"""
        self._log("DEBUG", message, metadata, function_name, api_endpoint)

def create_logger(request: Request, user_id: Optional[int] = None) -> BackendLogger:
    """백엔드 로거 생성 팩토리 함수

    Args:
        request: FastAPI Request 객체 (app_db를 가져오기 위해 필요)
        user_id: 사용자 ID (선택)

    Returns:
        BackendLogger 인스턴스

    Example:
        ```python
        @router.get("/some-endpoint")
        async def some_endpoint(request: Request):
            user_id = extract_user_id_from_request(request)
            backend_log = create_logger(request, user_id)
            backend_log.info("Processing request")
        ```
    """
    # 호출한 함수의 이름을 자동으로 추출
    caller_function_name = None
    try:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_function_name = frame.f_back.f_code.co_name
    except Exception:
        pass

    logger_instance = BackendLogger(request, user_id)

    # 자동 추출된 함수명으로 덮어쓰기
    if caller_function_name:
        logger_instance._function_name = caller_function_name

    return logger_instance