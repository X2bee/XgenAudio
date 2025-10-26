"""
TTS 팩토리
설정에 따라 적절한 TTS 클라이언트를 생성
"""

from typing import Dict, Any
import logging
from service.tts.base_tts import BaseTTS
from service.tts.zonos_tts import ZonosTTS
from service.redis.config_utils import get_tts_config

logger = logging.getLogger("tts.factory")

class TTSFactory:
    """TTS 클라이언트 팩토리"""

    PROVIDERS = {
        "zonos": ZonosTTS,
        # 추후 OpenAI TTS 등 추가 가능
        # "openai": OpenAITTS,
    }

    _instance = None
    _last_config_hash = None

    @classmethod
    def create_tts_client(cls) -> BaseTTS:
        tts_config = get_tts_config()
        provider = tts_config.TTS_PROVIDER.lower()

        # 설정 해시 생성 (설정이 변경되었는지 확인용)
        config_hash = cls._generate_config_hash(provider, tts_config)

        # 기존 인스턴스가 있고 설정이 동일하면 재사용
        if cls._instance is not None and cls._last_config_hash == config_hash:
            logger.info("Reusing existing TTS client instance")
            return cls._instance

        # 기존 인스턴스가 있지만 설정이 변경된 경우
        if cls._instance is not None:
            logger.info("Configuration changed, replacing TTS client")
            cls._instance = None

        if provider not in cls.PROVIDERS:
            available_providers = list(cls.PROVIDERS.keys())
            raise ValueError(f"Unsupported TTS provider: {provider}. Available: {available_providers}")

        config = cls._prepare_config(provider, tts_config)

        try:
            tts_class = cls.PROVIDERS[provider]
            client = tts_class(config)

            logger.info("Created %s TTS client", provider)

            # 새 인스턴스와 설정 해시 저장
            cls._instance = client
            cls._last_config_hash = config_hash
            return client

        except ImportError as e:
            logger.error("Missing dependencies for %s TTS client: %s", provider, e)
            raise ValueError(f"Cannot create {provider} TTS client. Missing dependencies: {e}") from e
        except (RuntimeError, OSError, ValueError) as e:
            logger.error("Failed to create %s TTS client: %s", provider, e)
            raise

    @classmethod
    def _generate_config_hash(cls, provider: str, tts_config) -> str:
        """설정 변경 감지를 위한 해시 생성"""
        if provider == "zonos":
            config_str = f"{provider}:{tts_config.ZONOS_TTS_MODEL_NAME}:{tts_config.ZONOS_TTS_MODEL_DEVICE}"
        elif provider == "openai":
            config_str = f"{provider}:{tts_config.OPENAI_API_KEY}:{tts_config.OPENAI_TTS_MODEL_NAME}"
        else:
            config_str = provider

        return str(hash(config_str))

    @classmethod
    def _prepare_config(cls, provider: str, tts_config) -> Dict[str, Any]:
        if provider == "zonos":
            return {
                "model_name": tts_config.ZONOS_TTS_MODEL_NAME,
                "model_device": tts_config.ZONOS_TTS_MODEL_DEVICE,
                "default_speaker": tts_config.ZONOS_TTS_DEFAULT_SPEAKER
            }

        elif provider == "openai":
            return {
                "api_key": tts_config.OPENAI_API_KEY,
                "model": tts_config.OPENAI_TTS_MODEL_NAME
            }

        else:
            raise ValueError(f"Unknown provider: {provider}")

    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        """
        사용 가능한 제공자 목록 반환

        Returns:
            제공자명과 설명
        """
        return {
            "zonos": "Zonos TTS",
            # "openai": "OpenAI TTS"
        }

    @classmethod
    async def cleanup_instance(cls):
        """인스턴스 정리"""
        if cls._instance:
            try:
                await cls._instance.cleanup()
            except (RuntimeError, AttributeError) as e:
                logger.warning("Error during TTS client cleanup: %s", e)
            finally:
                cls._instance = None
                cls._last_config_hash = None
