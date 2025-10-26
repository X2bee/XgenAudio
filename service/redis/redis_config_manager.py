"""
Redis Config Manager

PostgreSQL 대신 Redis를 사용한 설정 관리 시스템
"""
import os
import redis
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class RedisConfigManager:
    """Redis를 사용한 설정 관리자"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 db: Optional[int] = None, password: Optional[str] = None):
        # 환경 변수에서 Redis 연결 정보 읽기
        host = host or os.getenv('REDIS_HOST', '192.168.2.242')
        port = port or int(os.getenv('REDIS_PORT', '6379'))
        db = db or int(os.getenv('REDIS_DB', '0'))
        password = password or os.getenv('REDIS_PASSWORD', 'redis_secure_password123!')

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,  # 연결 타임아웃 5초
            socket_timeout=5,           # 소켓 타임아웃 5초
        )

        # Config 키 Prefix
        self.config_prefix = "config"

        logger.info(f"Redis Config Manager 초기화 완료: {host}:{port}")

        # 연결 테스트
        try:
            self.redis_client.ping()
            logger.info("Redis 연결 테스트 성공")
        except Exception as e:
            logger.warning(f"Redis 연결 테스트 실패: {e}")

    # ========== Config 값 CRUD ==========

    def set_config(self, config_path: str, config_value: Any,
                   data_type: str = "string", category: Optional[str] = None) -> bool:
        """
        설정 값 저장

        Args:
            config_path: 설정 경로 (예: "openai.api_key", "vast.vllm.port")
            config_value: 설정 값
            data_type: 데이터 타입 (string, int, float, bool, list, dict)
            category: 설정 카테고리 (예: "openai", "vast")

        Returns:
            bool: 성공 여부
        """
        try:
            # 카테고리 자동 추출 (config_path의 첫 번째 부분)
            if not category:
                category = config_path.split('.')[0]

            # 설정 값과 메타데이터를 JSON으로 저장
            config_data = {
                'value': config_value,
                'type': data_type,
                'category': category,
                'path': config_path
            }

            # Redis에 저장 (키: config:path)
            redis_key = f"{self.config_prefix}:{config_path}"
            self.redis_client.set(redis_key, json.dumps(config_data))

            # 카테고리별 인덱스도 저장 (키: config:category:name)
            category_key = f"{self.config_prefix}:category:{category}"
            self.redis_client.sadd(category_key, config_path)

            logger.debug(f"Config 저장 완료: {config_path} = {config_value}")
            return True

        except Exception as e:
            logger.error(f"Config 저장 실패: {config_path} - {str(e)}")
            return False

    def get_config_value(self, config_path: str, default: Any = None) -> Any:
        """
        설정 값만 조회

        Args:
            config_path: 설정 경로
            default: 기본값

        Returns:
            설정 값 또는 기본값
        """
        try:
            redis_key = f"{self.config_prefix}:{config_path}"
            data = self.redis_client.get(redis_key)

            if data:
                config_data = json.loads(data)
                return config_data.get('value', default)
            return default

        except Exception as e:
            logger.error(f"Config 조회 실패: {config_path} - {str(e)}")
            return default

    def get_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        설정 값과 메타데이터 조회

        Args:
            config_path: 설정 경로

        Returns:
            설정 데이터 (value, type, category, path)
        """
        try:
            redis_key = f"{self.config_prefix}:{config_path}"
            data = self.redis_client.get(redis_key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            logger.error(f"Config 조회 실패: {config_path} - {str(e)}")
            return None

    def delete_config(self, config_path: str) -> bool:
        """
        설정 삭제

        Args:
            config_path: 설정 경로

        Returns:
            bool: 성공 여부
        """
        try:
            # 카테고리 추출
            category = config_path.split('.')[0]

            # Redis에서 삭제
            redis_key = f"{self.config_prefix}:{config_path}"
            self.redis_client.delete(redis_key)

            # 카테고리 인덱스에서도 제거
            category_key = f"{self.config_prefix}:category:{category}"
            self.redis_client.srem(category_key, config_path)

            logger.debug(f"Config 삭제 완료: {config_path}")
            return True

        except Exception as e:
            logger.error(f"Config 삭제 실패: {config_path} - {str(e)}")
            return False

    def get_category_configs(self, category: str) -> List[Dict[str, Any]]:
        """
        특정 카테고리의 모든 설정 조회 (리스트 형태)

        Args:
            category: 카테고리 이름

        Returns:
            설정 리스트
        """
        try:
            category_key = f"{self.config_prefix}:category:{category}"
            config_paths = self.redis_client.smembers(category_key)

            configs = []
            for path in config_paths:
                config = self.get_config(path)
                if config:
                    configs.append(config)

            return configs

        except Exception as e:
            logger.error(f"카테고리 Config 조회 실패: {category} - {str(e)}")
            return []

    def get_category_configs_nested(self, category: str) -> Dict[str, Any]:
        """
        특정 카테고리의 모든 설정 조회 (중첩 딕셔너리 형태)

        Args:
            category: 카테고리 이름

        Returns:
            중첩된 딕셔너리 형태의 설정
            예: {"openai": {"api_key": "...", "model": "..."}}
        """
        try:
            configs = self.get_category_configs(category)
            result = {}

            for config in configs:
                path = config['path']
                value = config['value']

                # 경로를 '.'로 분리하여 중첩 딕셔너리 생성
                keys = path.split('.')
                current = result

                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                current[keys[-1]] = value

            return result

        except Exception as e:
            logger.error(f"카테고리 중첩 Config 조회 실패: {category} - {str(e)}")
            return {}

    def get_all_configs(self) -> List[Dict[str, Any]]:
        """
        모든 설정 조회

        Returns:
            모든 설정 리스트
        """
        try:
            # config:* 패턴으로 모든 설정 키 검색
            pattern = f"{self.config_prefix}:*"
            keys = self.redis_client.keys(pattern)

            configs = []
            for key in keys:
                # category 인덱스 키는 제외
                if ':category:' not in key:
                    data = self.redis_client.get(key)
                    if data:
                        configs.append(json.loads(data))

            return configs

        except Exception as e:
            logger.error(f"전체 Config 조회 실패: {str(e)}")
            return []

    def clear_category(self, category: str) -> bool:
        """
        특정 카테고리의 모든 설정 삭제

        Args:
            category: 카테고리 이름

        Returns:
            bool: 성공 여부
        """
        try:
            category_key = f"{self.config_prefix}:category:{category}"
            config_paths = self.redis_client.smembers(category_key)

            # 각 설정 삭제
            for path in config_paths:
                self.delete_config(path)

            # 카테고리 인덱스도 삭제
            self.redis_client.delete(category_key)

            logger.info(f"카테고리 '{category}' 전체 삭제 완료")
            return True

        except Exception as e:
            logger.error(f"카테고리 삭제 실패: {category} - {str(e)}")
            return False

    def exists(self, config_path: str) -> bool:
        """
        설정 존재 여부 확인

        Args:
            config_path: 설정 경로

        Returns:
            bool: 존재 여부
        """
        try:
            redis_key = f"{self.config_prefix}:{config_path}"
            return self.redis_client.exists(redis_key) > 0

        except Exception as e:
            logger.error(f"Config 존재 확인 실패: {config_path} - {str(e)}")
            return False

    def get_all_categories(self) -> List[str]:
        """
        모든 카테고리 목록 조회

        Returns:
            카테고리 목록
        """
        try:
            pattern = f"{self.config_prefix}:category:*"
            keys = self.redis_client.keys(pattern)

            # 카테고리 이름만 추출
            categories = [key.split(':')[-1] for key in keys]
            return sorted(categories)

        except Exception as e:
            logger.error(f"카테고리 목록 조회 실패: {str(e)}")
            return []
