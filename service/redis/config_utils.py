"""
Config 유틸리티 함수들

Redis에서 설정을 dictionary 형태로 쉽게 가져오는 함수들
"""
import logging
from typing import Dict, Any, Optional, List
from service.redis.redis_config_manager import RedisConfigManager
from types import SimpleNamespace

logger = logging.getLogger(__name__)

def dict_to_namespace(data):
    """
    dict를 재귀적으로 SimpleNamespace로 변환
    자동으로 'vast', 'config' 같은 단일 래퍼 키를 언래핑합니다
    
    Args:
        data: 변환할 데이터 (dict, list, 또는 기본 타입)
    
    Returns:
        SimpleNamespace 또는 변환된 데이터
    
    Examples:
        >>> # 일반 dict
        >>> data = {'port': 8080, 'host': 'localhost'}
        >>> obj = dict_to_namespace(data)
        >>> obj.port
        8080
        
        >>> # 래퍼가 있는 경우 (자동 언래핑)
        >>> wrapped = {'vast': {'vllm': {'port': 12434}}}
        >>> obj = dict_to_namespace(wrapped)
        >>> obj.vllm.port  # 'vast'가 자동으로 제거됨
        12434
        
        >>> # 중첩 구조
        >>> nested = {'server': {'db': {'host': 'localhost'}}}
        >>> obj = dict_to_namespace(nested)
        >>> obj.server.db.host
        'localhost'
    """
    if isinstance(data, dict):
        # 🎯 자동 언래핑: 단일 키만 있고 그 값이 dict인 경우
        if len(data) == 1:
            key, value = next(iter(data.items()))
            # 일반적인 래퍼 키를 자동으로 건너뜀
            common_wrappers = {'vast', 'config', 'data', 'settings', 'options', 
                              'result', 'response', 'payload'}
            if key in common_wrappers and isinstance(value, dict):
                data = value  # 래퍼를 벗김
                logger.debug(f"자동 언래핑: '{key}' 키 제거됨")
        
        # dict의 모든 값을 재귀적으로 변환
        return SimpleNamespace(**{
            key: dict_to_namespace(value) 
            for key, value in data.items()
        })
    elif isinstance(data, list):
        # list의 각 요소를 재귀적으로 변환
        return [dict_to_namespace(item) for item in data]
    else:
        # 기본 타입은 그대로 반환
        return data


def get_config_dict(
    redis_manager: Optional[RedisConfigManager] = None,
    category: Optional[str] = None,
    flatten: bool = False,
    as_namespace: bool = False
) -> Dict[str, Any]:
    """
    Redis에서 설정을 dictionary 형태로 가져옵니다.

    Args:
        redis_manager: RedisConfigManager 인스턴스 (없으면 자동 생성)
        category: 특정 카테고리만 가져오기 (None이면 전체)
        flatten: True면 평탄화된 구조 {"app.environment": "dev"},
                False면 중첩 구조 {"app": {"environment": "dev"}}
        as_namespace: True면 SimpleNamespace로 변환 (속성 접근 가능)

    Returns:
        Dict 또는 SimpleNamespace: 설정

    Examples:
        >>> # 모든 설정을 중첩 구조로
        >>> configs = get_config_dict()
        >>> print(configs["app"]["environment"])  # "development"

        >>> # SimpleNamespace로 변환 (속성 접근)
        >>> configs = get_config_dict(as_namespace=True)
        >>> print(configs.app.environment)  # "development"

        >>> # 특정 카테고리만 중첩 구조로
        >>> openai_config = get_config_dict(category="openai")
        >>> print(openai_config["openai"]["api_key"])

        >>> # 평탄화된 구조로
        >>> flat_config = get_config_dict(flatten=True)
        >>> print(flat_config["app.environment"])  # "development"
    """
    if redis_manager is None:
        redis_manager = RedisConfigManager()

    try:
        if category:
            # 특정 카테고리만 가져오기
            if flatten:
                # 평탄화된 구조
                configs = redis_manager.get_category_configs(category)
                result = {config['path']: config['value'] for config in configs}
            else:
                # 중첩 구조
                result = redis_manager.get_category_configs_nested(category)
        else:
            # 모든 설정 가져오기
            all_configs = redis_manager.get_all_configs()

            if flatten:
                # 평탄화된 구조
                result = {config['path']: config['value'] for config in all_configs}
            else:
                # 중첩 구조
                result = {}
                for config in all_configs:
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

        # SimpleNamespace로 변환 (자동 언래핑 포함)
        if as_namespace:
            return dict_to_namespace(result)
        
        return result

    except Exception as e:
        logger.error(f"설정 가져오기 실패: {str(e)}")
        return {} if not as_namespace else SimpleNamespace()


def get_category_config(
    category: str,
    redis_manager: Optional[RedisConfigManager] = None,
    as_namespace: bool = True
) -> Any:
    """
    특정 카테고리의 설정을 가져옵니다.
    
    기본적으로 SimpleNamespace로 반환하여 속성으로 접근 가능합니다.
    자동으로 카테고리 래퍼 키를 언래핑합니다.

    Args:
        category: 카테고리 이름 (예: "openai", "app", "vast")
        redis_manager: RedisConfigManager 인스턴스 (없으면 자동 생성)
        as_namespace: True면 SimpleNamespace, False면 dict

    Returns:
        SimpleNamespace 또는 Dict: 설정 객체

    Examples:
        >>> # SimpleNamespace로 (기본값, 속성 접근)
        >>> openai = get_category_config("openai")
        >>> print(openai.api_key)  # 바로 접근!
        >>> print(openai.model_default)
        
        >>> # dict로 (as_namespace=False)
        >>> openai = get_category_config("openai", as_namespace=False)
        >>> print(openai["openai"]["api_key"])  # 키 접근
        
        >>> # vast 설정 (자동 언래핑)
        >>> vast = get_category_config("vast")
        >>> print(vast.vllm.gpu_memory_utilization)  # 바로 접근!
    """
    result = get_config_dict(
        redis_manager=redis_manager, 
        category=category, 
        flatten=False,
        as_namespace=False  # 일단 dict로 받음
    )
    
    # 카테고리 키로 래핑되어 있으면 언래핑
    if isinstance(result, dict) and category in result:
        result = result[category]
        logger.debug(f"카테고리 '{category}' 자동 언래핑")
    
    # SimpleNamespace로 변환 (필요시)
    if as_namespace:
        return dict_to_namespace(result)
    
    return result


def get_flat_config(
    category: Optional[str] = None,
    redis_manager: Optional[RedisConfigManager] = None
) -> Dict[str, Any]:
    """
    설정을 평탄화된 dictionary로 가져옵니다.

    Args:
        category: 특정 카테고리만 (None이면 전체)
        redis_manager: RedisConfigManager 인스턴스

    Returns:
        Dict: 평탄화된 설정 딕셔너리 {"path.to.config": value}

    Example:
        >>> flat = get_flat_config(category="app")
        >>> print(flat)
        {
            "app.environment": "development",
            "app.port": 8000,
            "app.debug_mode": True
        }
    """
    return get_config_dict(redis_manager=redis_manager, category=category, flatten=True)


def get_config_value(
    config_path: str,
    default: Any = None,
    redis_manager: Optional[RedisConfigManager] = None
) -> Any:
    """
    특정 설정 값만 가져옵니다.

    Args:
        config_path: 설정 경로 (예: "app.environment", "openai.api_key")
        default: 기본값
        redis_manager: RedisConfigManager 인스턴스

    Returns:
        설정 값 또는 기본값

    Example:
        >>> env = get_config_value("app.environment")
        >>> print(env)  # "development"

        >>> api_key = get_config_value("openai.api_key", default="")
    """
    try:
        if redis_manager is None:
            redis_manager = RedisConfigManager()

        logger.debug(f"Redis에서 설정 조회 중: {config_path}")
        value = redis_manager.get_config_value(config_path, default=default)
        logger.debug(f"설정 조회 완료: {config_path} = {value}")
        return value
    except Exception as e:
        logger.warning(f"설정 조회 실패: {config_path}, 기본값 사용: {default} (에러: {e})")
        return default


def get_multiple_configs(
    config_paths: List[str],
    redis_manager: Optional[RedisConfigManager] = None
) -> Dict[str, Any]:
    """
    여러 설정을 한 번에 가져옵니다.

    Args:
        config_paths: 설정 경로 리스트
        redis_manager: RedisConfigManager 인스턴스

    Returns:
        Dict: {config_path: value}

    Example:
        >>> configs = get_multiple_configs([
        ...     "app.environment",
        ...     "openai.api_key",
        ...     "vast.vllm.port"
        ... ])
        >>> print(configs)
        {
            "app.environment": "development",
            "openai.api_key": "sk-...",
            "vast.vllm.port": 12434
        }
    """
    if redis_manager is None:
        redis_manager = RedisConfigManager()

    result = {}
    for path in config_paths:
        try:
            result[path] = redis_manager.get_config_value(path)
        except Exception as e:
            logger.warning(f"설정 가져오기 실패: {path} - {str(e)}")
            result[path] = None

    return result


def get_all_categories(
    redis_manager: Optional[RedisConfigManager] = None
) -> List[str]:
    """
    모든 카테고리 목록을 가져옵니다.

    Args:
        redis_manager: RedisConfigManager 인스턴스

    Returns:
        List[str]: 카테고리 목록

    Example:
        >>> categories = get_all_categories()
        >>> print(categories)
        ['app', 'openai', 'anthropic', 'vast', ...]
    """
    if redis_manager is None:
        redis_manager = RedisConfigManager()

    return redis_manager.get_all_categories()


def update_config(
    config_path: str,
    new_value: Any,
    data_type: Optional[str] = None,
    redis_manager: Optional[RedisConfigManager] = None
) -> bool:
    """
    설정 값을 업데이트합니다.

    Args:
        config_path: 설정 경로
        new_value: 새로운 값
        data_type: 데이터 타입 (자동 추론 가능)
        redis_manager: RedisConfigManager 인스턴스

    Returns:
        bool: 성공 여부

    Example:
        >>> update_config("app.environment", "production")
        >>> update_config("app.port", 9000)
    """
    if redis_manager is None:
        redis_manager = RedisConfigManager()

    # 데이터 타입 자동 추론
    if data_type is None:
        if isinstance(new_value, bool):
            data_type = "bool"
        elif isinstance(new_value, int):
            data_type = "int"
        elif isinstance(new_value, float):
            data_type = "float"
        elif isinstance(new_value, list):
            data_type = "list"
        elif isinstance(new_value, dict):
            data_type = "dict"
        else:
            data_type = "string"

    # 카테고리 추출
    category = config_path.split('.')[0]

    return redis_manager.set_config(
        config_path=config_path,
        config_value=new_value,
        data_type=data_type,
        category=category
    )


# ============================================
# 편의 함수들 (자동으로 SimpleNamespace 반환)
# ============================================

def get_app_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """
    app 카테고리 설정 가져오기 (SimpleNamespace)
    
    Returns:
        SimpleNamespace: app.* 설정들을 속성으로 접근 가능
    
    Example:
        >>> app = get_app_config()
        >>> print(app.environment)
        >>> print(app.port)
    """
    return get_category_config("app", redis_manager, as_namespace=True)


def get_openai_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """
    openai 카테고리 설정 가져오기 (SimpleNamespace)
    
    Returns:
        SimpleNamespace: openai.* 설정들을 속성으로 접근 가능
    
    Example:
        >>> openai = get_openai_config()
        >>> print(openai.api_key)
        >>> print(openai.model_default)
    """
    return get_category_config("openai", redis_manager, as_namespace=True)


def get_anthropic_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """
    anthropic 카테고리 설정 가져오기 (SimpleNamespace)
    
    Returns:
        SimpleNamespace: anthropic.* 설정들을 속성으로 접근 가능
    
    Example:
        >>> anthropic = get_anthropic_config()
        >>> print(anthropic.api_key)
        >>> print(anthropic.model_default)
    """
    return get_category_config("anthropic", redis_manager, as_namespace=True)


def get_vast_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """
    vast 카테고리 설정 가져오기 (SimpleNamespace, 자동 언래핑)
    
    Returns:
        SimpleNamespace: vast.* 설정들을 속성으로 접근 가능
        'vast' 래퍼 키가 있으면 자동으로 제거됨
    
    Example:
        >>> vast = get_vast_config()
        >>> print(vast.vllm.gpu_memory_utilization)  # 바로 접근!
        >>> print(vast.vllm.port)
        >>> print(vast.image.name)
    """
    return get_category_config("vast", redis_manager, as_namespace=True)


def get_vllm_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """
    vllm 카테고리 설정 가져오기 (SimpleNamespace)
    
    Returns:
        SimpleNamespace: vllm.* 설정들을 속성으로 접근 가능
    
    Example:
        >>> vllm = get_vllm_config()
        >>> print(vllm.port)
        >>> print(vllm.gpu_memory_utilization)
    """
    return get_category_config("vllm", redis_manager, as_namespace=True)


def get_stt_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """STT 설정 조회"""
    try:
        return get_category_config("stt", redis_manager, as_namespace=True)
    except Exception as e:
        logger.error(f"STT 설정 조회 실패: {e}", exc_info=True)
        raise

def get_tts_config(redis_manager: Optional[RedisConfigManager] = None) -> SimpleNamespace:
    """TTS 설정 조회"""
    try:
        return get_category_config("tts", redis_manager, as_namespace=True)
    except Exception as e:
        logger.error(f"TTS 설정 조회 실패: {e}", exc_info=True)
        raise


def check_tts_config():
    """TTS 설정 상세 확인"""
    print("=" * 60)
    print("🔍 TTS 설정 확인")
    print("=" * 60)
    
    redis_manager = RedisConfigManager()
    
    # 1. TTS 카테고리의 모든 설정 조회 (raw)
    print("\n1️⃣ TTS 카테고리 전체 설정 (Redis raw data):")
    print("-" * 60)
    try:
        tts_configs = redis_manager.get_category_configs("tts")
        if tts_configs:
            for config in tts_configs:
                print(f"  Path: {config['path']}")
                print(f"  Value: {config['value']}")
                print(f"  Type: {config['data_type']}")
                print(f"  Category: {config['category']}")
                print()
        else:
            print("  ⚠️  TTS 설정이 비어있습니다!")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 2. 중첩 구조로 조회
    print("\n2️⃣ TTS 설정 (중첩 구조):")
    print("-" * 60)
    try:
        tts_nested = redis_manager.get_category_configs_nested("tts")
        print(json.dumps(tts_nested, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 3. SimpleNamespace로 조회
    print("\n3️⃣ TTS 설정 (SimpleNamespace):")
    print("-" * 60)
    try:
        tts_config = get_tts_config()
        print(f"  Type: {type(tts_config)}")
        print(f"  Attributes: {dir(tts_config)}")
        print(f"  Dict: {vars(tts_config)}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 4. 특정 설정값 직접 조회
    print("\n4️⃣ 주요 TTS 설정값 직접 조회:")
    print("-" * 60)
    check_keys = [
        "tts.is_tts_available",
        "tts.provider",
        "tts.model",
        "tts.voice",
        "tts.api_key",
        "tts.base_url"
    ]
    
    for key in check_keys:
        try:
            value = redis_manager.get_config_value(key, default="<NOT FOUND>")
            print(f"  {key}: {value}")
        except Exception as e:
            print(f"  {key}: ❌ {e}")
    
    # 5. 모든 카테고리 목록
    print("\n5️⃣ 사용 가능한 모든 카테고리:")
    print("-" * 60)
    try:
        categories = redis_manager.get_all_categories()
        print(f"  {', '.join(categories)}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 6. TTS 관련 모든 키 검색
    print("\n6️⃣ Redis에서 'tts'로 시작하는 모든 키:")
    print("-" * 60)
    try:
        all_configs = redis_manager.get_all_configs()
        tts_related = [c for c in all_configs if c['path'].startswith('tts')]
        if tts_related:
            for config in tts_related:
                print(f"  {config['path']} = {config['value']} ({config['data_type']})")
        else:
            print("  ⚠️  'tts'로 시작하는 설정이 없습니다!")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    print("\n" + "=" * 60)


def check_all_categories():
    """모든 카테고리 설정 간단 확인"""
    print("\n" + "=" * 60)
    print("📋 전체 카테고리별 설정 개수")
    print("=" * 60)
    
    redis_manager = RedisConfigManager()
    
    try:
        categories = redis_manager.get_all_categories()
        for category in sorted(categories):
            configs = redis_manager.get_category_configs(category)
            print(f"  {category}: {len(configs)}개 설정")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    print("=" * 60)