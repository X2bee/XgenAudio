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
            decode_responses=True
        )

        # Config 키 Prefix
        self.config_prefix = "config"

        logger.info(f"Redis Config Manager 초기화 완료: {host}:{port}")

    # ========== Config 값 CRUD ==========

    def set_config(self, config_path: str, config_value: Any,
                   data_type: str = "string", category: Optional[str] = None,
                   env_name: Optional[str] = None) -> bool:
        """
        설정 값 저장

        Args:
            config_path: 설정 경로 (예: "openai.api_key", "vast.vllm.port")
            config_value: 설정 값
            data_type: 데이터 타입 (string, int, float, bool, list, dict)
            category: 설정 카테고리 (예: "openai", "vast")
            env_name: 환경 변수 이름 (예: "OPENAI_API_KEY")

        Returns:
            bool: 성공 여부
        """
        try:
            # 카테고리 자동 추출 (config_path의 첫 번째 부분)
            if not category:
                category = config_path.split('.')[0]

            # env_name이 없으면 config_path 사용
            final_env_name = env_name or config_path

            # 설정 값과 메타데이터를 JSON으로 저장
            config_data = {
                'value': config_value,
                'type': data_type,
                'category': category,
                'path': config_path,
                'env_name': final_env_name
            }

            # Redis에 저장 (키: config:env_name)
            redis_key = f"{self.config_prefix}:{final_env_name}"
            self.redis_client.set(redis_key, json.dumps(config_data))

            # 카테고리별 인덱스도 저장 (키: config:category:name, 값: env_name)
            category_key = f"{self.config_prefix}:category:{category}"
            self.redis_client.sadd(category_key, final_env_name)

            logger.debug(f"Config 저장 완료: {final_env_name} (path: {config_path}) = {config_value}")
            return True

        except Exception as e:
            logger.error(f"Config 저장 실패: {config_path} - {str(e)}")
            return False

    def get_config_value(self, env_name: str, default: Any = None) -> Any:
        """
        설정 값만 조회 (env_name 기준)

        Args:
            env_name: 환경 변수 이름
            default: 기본값

        Returns:
            설정 값 또는 기본값
        """
        try:
            redis_key = f"{self.config_prefix}:{env_name}"
            data = self.redis_client.get(redis_key)

            if data:
                config_data = json.loads(data)
                return config_data.get('value', default)
            return default

        except Exception as e:
            logger.error(f"Config 조회 실패: {env_name} - {str(e)}")
            return default

    def get_config(self, env_name: str) -> Optional[Dict[str, Any]]:
        """
        설정 값과 메타데이터 조회 (env_name 기준)

        Args:
            env_name: 환경 변수 이름

        Returns:
            설정 데이터 (value, type, category, path, env_name)
        """
        try:
            redis_key = f"{self.config_prefix}:{env_name}"
            data = self.redis_client.get(redis_key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            logger.error(f"Config 조회 실패: {env_name} - {str(e)}")
            return None

    def delete_config(self, env_name: str) -> bool:
        """
        설정 삭제 (env_name 기준)

        Args:
            env_name: 환경 변수 이름

        Returns:
            bool: 성공 여부
        """
        try:
            # 설정 데이터 먼저 조회하여 카테고리 확인
            config_data = self.get_config(env_name)
            if not config_data:
                logger.warning(f"삭제할 Config를 찾을 수 없음: {env_name}")
                return False

            category = config_data.get('category')

            # Redis에서 삭제
            redis_key = f"{self.config_prefix}:{env_name}"
            self.redis_client.delete(redis_key)

            # 카테고리 인덱스에서도 제거
            if category:
                category_key = f"{self.config_prefix}:category:{category}"
                self.redis_client.srem(category_key, env_name)

            logger.debug(f"Config 삭제 완료: {env_name}")
            return True

        except Exception as e:
            logger.error(f"Config 삭제 실패: {env_name} - {str(e)}")
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
            env_names = self.redis_client.smembers(category_key)

            configs = []
            for env_name in env_names:
                config = self.get_config(env_name)
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
            env_names = self.redis_client.smembers(category_key)

            # 각 설정 삭제
            for env_name in env_names:
                self.delete_config(env_name)

            # 카테고리 인덱스도 삭제
            self.redis_client.delete(category_key)

            logger.info(f"카테고리 '{category}' 전체 삭제 완료")
            return True

        except Exception as e:
            logger.error(f"카테고리 삭제 실패: {category} - {str(e)}")
            return False

    def exists(self, env_name: str) -> bool:
        """
        설정 존재 여부 확인 (env_name 기준)

        Args:
            env_name: 환경 변수 이름

        Returns:
            bool: 존재 여부
        """
        try:
            redis_key = f"{self.config_prefix}:{env_name}"
            return self.redis_client.exists(redis_key) > 0

        except Exception as e:
            logger.error(f"Config 존재 확인 실패: {env_name} - {str(e)}")
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

    # ========== ConfigComposer 호환성 메서드 ==========

    def get_config_by_name(self, config_name: str) -> Any:
        """
        이름으로 특정 설정 가져오기 (ConfigComposer 호환)

        Args:
            config_name: 설정 이름 (예: "OPENAI_API_KEY", "PORT")

        Returns:
            설정 값

        Raises:
            KeyError: 설정이 존재하지 않는 경우
        """
        try:
            # 1. env_name으로 직접 검색 시도
            value = self.get_config_value(config_name)
            if value is not None:
                return value

            # 2. 모든 config에서 검색 (env_name 또는 path와 일치)
            all_configs = self.get_all_configs()
            for config in all_configs:
                if config.get('env_name') == config_name or config['path'] == config_name:
                    return config['value']

                # path의 마지막 부분이 config_name과 일치하는 경우
                path_parts = config['path'].split('.')
                if path_parts[-1] == config_name:
                    return config['value']

            raise KeyError(f"Configuration '{config_name}' not found")

        except Exception as e:
            logger.error(f"Config 조회 실패: {config_name} - {str(e)}")
            raise KeyError(f"Configuration '{config_name}' not found")

    def get_config_by_category_name(self, category_name: str) -> Dict[str, Any]:
        """
        카테고리 이름으로 특정 설정 그룹 가져오기 (ConfigComposer 호환)

        Args:
            category_name: 카테고리 이름 (예: "openai", "database", "app")

        Returns:
            해당 카테고리의 모든 설정 (중첩 딕셔너리 형태)

        Raises:
            KeyError: 카테고리가 존재하지 않는 경우
        """
        try:
            configs = self.get_category_configs_nested(category_name)

            if not configs:
                raise KeyError(f"Configuration category '{category_name}' not found")

            return configs

        except Exception as e:
            logger.error(f"카테고리 Config 조회 실패: {category_name} - {str(e)}")
            raise KeyError(f"Configuration category '{category_name}' not found")

    def update_config_by_name(self, config_name: str, new_value: Any) -> None:
        """
        이름으로 특정 설정 업데이트 (ConfigComposer 호환)

        Args:
            config_name: 설정 이름
            new_value: 새로운 값

        Raises:
            KeyError: 설정이 존재하지 않는 경우
        """
        try:
            # 1. env_name으로 직접 검색 시도
            if self.exists(config_name):
                config_data = self.get_config(config_name)
                self.set_config(
                    config_path=config_data.get('path', config_name),
                    config_value=new_value,
                    data_type=config_data.get('type', 'string'),
                    category=config_data.get('category'),
                    env_name=config_data.get('env_name')
                )
                logger.info(f"Config 업데이트 완료: {config_name} = {new_value}")
                return

            # 2. 모든 config에서 검색하여 업데이트
            all_configs = self.get_all_configs()
            for config in all_configs:
                if config.get('env_name') == config_name or config['path'] == config_name:
                    self.set_config(
                        config_path=config['path'],
                        config_value=new_value,
                        data_type=config['type'],
                        category=config['category'],
                        env_name=config.get('env_name')
                    )
                    logger.info(f"Config 업데이트 완료: {config_name} = {new_value}")
                    return

                # path의 마지막 부분이 config_name과 일치하는 경우
                path_parts = config['path'].split('.')
                if path_parts[-1] == config_name:
                    self.set_config(
                        config_path=config['path'],
                        config_value=new_value,
                        data_type=config['type'],
                        category=config['category'],
                        env_name=config.get('env_name')
                    )
                    logger.info(f"Config 업데이트 완료: {config['path']} = {new_value}")
                    return

            raise KeyError(f"Configuration '{config_name}' not found")

        except Exception as e:
            logger.error(f"Config 업데이트 실패: {config_name} - {str(e)}")
            raise

    def get_all_config(self, **kwargs) -> Dict[str, Any]:
        """
        모든 설정을 카테고리별로 구조화하여 반환 (ConfigComposer 호환)

        Returns:
            Dict: {
                "category_name": {nested configs},
                "all_configs": [list of all configs]
            }
        """
        try:
            result = {}

            # 모든 카테고리 가져오기
            categories = self.get_all_categories()

            for category in categories:
                result[category] = self.get_category_configs_nested(category)

            # 전체 config 리스트 추가
            result["all_configs"] = self.get_all_configs()

            return result

        except Exception as e:
            logger.error(f"전체 Config 조회 실패: {str(e)}")
            return {"all_configs": []}

    def get_config_summary(self) -> Dict[str, Any]:
        """
        모든 설정의 요약 정보 반환 (ConfigComposer 호환)

        Returns:
            Dict: 설정 요약 정보
        """
        try:
            all_configs = self.get_all_configs()
            categories = self.get_all_categories()

            # 카테고리별 요약
            categories_summary = {}
            for category in categories:
                category_configs = self.get_category_configs(category)
                categories_summary[category] = {
                    "count": len(category_configs),
                    "configs": [
                        {
                            "path": cfg["path"],
                            "type": cfg["type"],
                            "has_value": cfg["value"] is not None
                        }
                        for cfg in category_configs
                    ]
                }

            return {
                "total_configs": len(all_configs),
                "discovered_categories": categories,
                "categories": categories_summary,
                "storage_type": "redis"
            }

        except Exception as e:
            logger.error(f"Config 요약 정보 조회 실패: {str(e)}")
            return {
                "total_configs": 0,
                "discovered_categories": [],
                "categories": {},
                "storage_type": "redis",
                "error": str(e)
            }

    def update_config(self, config_name: str, new_value: Any) -> Dict[str, Any]:
        """
        설정값을 업데이트하고 결과를 반환하는 통합 메서드 (ConfigComposer 호환)

        Args:
            config_name: 설정 이름
            new_value: 새로운 값

        Returns:
            Dict: 업데이트 결과 정보

        Raises:
            KeyError: 설정이 존재하지 않는 경우
            ValueError: 타입 변환 실패 시
        """
        try:
            # 기존 설정 가져오기
            old_value = self.get_config_by_name(config_name)

            # 설정 업데이트
            self.update_config_by_name(config_name, new_value)

            logger.info(f"Config 업데이트 성공: {config_name}: {old_value} -> {new_value}")

            return {
                "config_name": config_name,
                "old_value": old_value,
                "new_value": new_value,
                "success": True
            }

        except KeyError:
            logger.error(f"Config '{config_name}' not found")
            raise KeyError(f"Config '{config_name}' not found")
        except Exception as e:
            logger.error(f"Config 업데이트 실패: {config_name} - {str(e)}")
            raise ValueError(f"Failed to update config '{config_name}': {str(e)}")

    def refresh_all(self) -> None:
        """
        모든 설정을 Redis에서 다시 로드 (ConfigComposer 호환)
        Redis는 항상 최신 상태이므로 실제로는 아무 작업도 하지 않음
        """
        logger.info("=== Redis configs are always up-to-date, no refresh needed ===")

    def save_all(self) -> None:
        """
        모든 설정을 Redis에 저장 (ConfigComposer 호환)
        Redis는 즉시 저장되므로 실제로는 아무 작업도 하지 않음
        """
        logger.info("=== Redis configs are auto-saved, no manual save needed ===")

    def validate_critical_configs(self) -> Dict[str, Any]:
        """
        중요한 설정들이 올바르게 설정되었는지 검증 (ConfigComposer 호환)

        Returns:
            Dict: 검증 결과
        """
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": []
        }

        try:
            # 포트 번호 검증
            try:
                port = self.get_config_by_name("PORT")
                if port is not None:
                    port_int = int(port)
                    if not (1 <= port_int <= 65535):
                        validation_results["errors"].append(f"Invalid port number: {port}")
                        validation_results["valid"] = False
            except (KeyError, ValueError):
                pass

            # API 키 존재 여부 확인
            try:
                api_key = self.get_config_by_name("OPENAI_API_KEY")
                if not api_key or api_key.strip() == "":
                    validation_results["warnings"].append("OpenAI API Key is not set")
            except KeyError:
                pass

            # 데이터베이스 연결 정보 확인
            try:
                db_host = self.get_config_by_name("DATABASE_HOST")
                if not db_host:
                    validation_results["warnings"].append("Database host is not set")
            except KeyError:
                pass

        except Exception as e:
            logger.error(f"Config 검증 실패: {str(e)}")
            validation_results["errors"].append(f"Validation error: {str(e)}")
            validation_results["valid"] = False

        return validation_results
