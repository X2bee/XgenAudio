# 🎤 XgenAudio API

음성 인식(STT, Speech-to-Text)과 음성 합성(TTS, Text-to-Speech) 서비스를 제공하는 FastAPI 기반 REST API 서버입니다.

## ✨ 주요 기능

### 🎯 STT (Speech-to-Text)
- **HuggingFace Transformers 기반**: Whisper 등 최신 음성 인식 모델 지원
- **다양한 포맷 지원**: wav, mp3, flac, m4a, ogg, webm, mp4
- **실시간 처리**: 빠른 음성-텍스트 변환
- **GPU 가속**: CUDA 지원으로 고속 처리

### 🔊 TTS (Text-to-Speech)
- **Zonos TTS 엔진**: 고품질 한국어 음성 합성
- **감정 제어**: 8가지 감정 조절 (행복, 슬픔, 혐오, 공포, 놀람, 분노, 기타, 중립)
- **화자 선택**: 다양한 화자 음색 지원
- **실시간 생성**: 빠른 텍스트-음성 변환

### ⚙️ Redis 기반 동적 설정 관리
- **실시간 설정 업데이트**: 서버 재시작 없이 설정 변경
- **카테고리별 관리**: STT, TTS 설정을 독립적으로 관리
- **타임아웃 및 에러 핸들링**: 안정적인 설정 조회

---

## 📋 목차

- [시작하기](#-시작하기)
  - [필수 요구사항](#필수-요구사항)
  - [설치](#설치)
  - [환경 설정](#환경-설정)
  - [Redis 설정](#redis-설정)
- [서버 실행](#-서버-실행)
- [API 문서](#-api-문서)
- [API 엔드포인트](#-api-엔드포인트)
- [사용 예제](#-사용-예제)
- [프로젝트 구조](#-프로젝트-구조)
- [개발](#-개발)
- [트러블슈팅](#-트러블슈팅)

---

## 🚀 시작하기

### 필수 요구사항

- **Python**: 3.9 이상 (3.10, 3.11 권장)
- **Redis**: 5.0 이상
- **시스템 라이브러리**:
  - `libsndfile` (오디오 파일 처리)
  - `cmake` (의존성 빌드용, macOS: `brew install cmake`)
- **선택사항**:
  - CUDA 11.8+ (GPU 가속 사용 시)
  - 16GB+ RAM (대형 모델 사용 시)

### 설치

#### 1. 저장소 클론

```bash
git clone <repository-url>
cd XgenAudio
```

#### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

#### 3. 의존성 설치

**방법 A: uv 사용 (권장, 빠름)**
```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치 및 실행
uv run main.py
```

**방법 B: pip 사용**
```bash
pip install -r requirements.txt
```

**방법 C: poetry 사용**
```bash
poetry install
poetry run python main.py
```

### 환경 설정

#### 1. .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성하세요:

```bash
# Redis 설정
REDIS_HOST=192.168.2.242
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# API 서버 설정
API_HOST=0.0.0.0
API_PORT=8010

# 애플리케이션 설정
ENVIRONMENT=development
DEBUG_MODE=true  # 상세 로깅 활성화
```

### Redis 설정

XgenAudio는 Redis를 설정 저장소로 사용합니다. 서비스를 시작하기 전에 Redis에 설정을 추가해야 합니다.

#### 방법 1: Python 스크립트로 설정

`setup_config.py` 파일을 생성하고 실행:

```python
from service.redis.config_utils import update_config

# ====== STT 설정 ======
# STT 서비스 활성화
update_config("stt.IS_AVAILABLE_STT", True, data_type="bool")
update_config("stt.STT_PROVIDER", "huggingface")
update_config("stt.HUGGINGFACE_STT_MODEL_NAME", "openai/whisper-large-v3")
update_config("stt.HUGGINGFACE_STT_MODEL_DEVICE", "cuda")  # 또는 "cpu"
update_config("stt.HUGGING_FACE_HUB_TOKEN", "your_hf_token")  # HuggingFace 토큰

# ====== TTS 설정 ======
# TTS 서비스 활성화
update_config("tts.IS_AVAILABLE_TTS", True, data_type="bool")
update_config("tts.TTS_PROVIDER", "zonos")
update_config("tts.ZONOS_TTS_MODEL_NAME", "/path/to/zonos/model")
update_config("tts.ZONOS_TTS_MODEL_DEVICE", "cuda")  # 또는 "cpu"
update_config("tts.ZONOS_TTS_DEFAULT_SPEAKER", "default")

print("✅ Redis 설정 완료!")
```

```bash
python setup_config.py
```

#### 방법 2: Redis CLI로 직접 설정

```bash
redis-cli -h 192.168.2.242 -p 6379 -a your_password

# STT 설정
SET config:stt.IS_AVAILABLE_STT '{"value": true, "data_type": "bool", "category": "stt"}'
SET config:stt.STT_PROVIDER '{"value": "huggingface", "data_type": "string", "category": "stt"}'
SET config:stt.HUGGINGFACE_STT_MODEL_NAME '{"value": "openai/whisper-large-v3", "data_type": "string", "category": "stt"}'

# TTS 설정
SET config:tts.IS_AVAILABLE_TTS '{"value": true, "data_type": "bool", "category": "tts"}'
SET config:tts.TTS_PROVIDER '{"value": "zonos", "data_type": "string", "category": "tts"}'
```

---

## 🎯 서버 실행

### 기본 실행

```bash
# uv 사용
uv run main.py

# 또는 직접 실행
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

### 프로덕션 실행

```bash
# 워커 수 지정
uvicorn main:app --host 0.0.0.0 --port 8010 --workers 4

# 또는 gunicorn 사용
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8010
```

서버가 시작되면 다음 주소에서 확인할 수 있습니다:

- 🏠 **홈**: http://localhost:8010
- 📚 **API 문서 (Swagger)**: http://localhost:8010/docs
- 📖 **API 문서 (ReDoc)**: http://localhost:8010/redoc
- 💚 **헬스 체크**: http://localhost:8010/health

---

## 📚 API 문서

서버 실행 후 브라우저에서 자동 생성된 API 문서를 확인하세요:

- **Swagger UI**: http://localhost:8010/docs - 대화형 API 테스트
- **ReDoc**: http://localhost:8010/redoc - 깔끔한 문서 뷰

---

## 🔌 API 엔드포인트

### 기본 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | 서비스 정보 |
| `GET` | `/health` | 헬스 체크 (STT/TTS 상태 포함) |

### STT (Speech-to-Text) 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/stt/transcribe` | 음성 파일을 텍스트로 변환 |
| `GET` | `/api/stt/status` | STT 서비스 상태 확인 (상세) |
| `GET` | `/api/stt/simple-status` | STT 서비스 상태 확인 (간단) |
| `POST` | `/api/stt/refresh` | STT 서비스 설정 새로고침 |

### TTS (Text-to-Speech) 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tts/generate` | 텍스트를 음성으로 변환 |
| `GET` | `/api/tts/info` | TTS 서비스 정보 |
| `GET` | `/api/tts/simple-status` | TTS 서비스 상태 확인 |
| `POST` | `/api/tts/refresh` | TTS 서비스 설정 새로고침 |

---

## 💡 사용 예제

### STT: 음성을 텍스트로 변환

#### cURL

```bash
curl -X POST "http://localhost:8010/api/stt/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@/path/to/audio.wav" \
  -F "audio_format=wav"
```

#### Python

```python
import requests

url = "http://localhost:8010/api/stt/transcribe"
files = {"audio_file": open("audio.wav", "rb")}
data = {"audio_format": "wav"}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"인식된 텍스트: {result['transcription']}")
print(f"제공자: {result['provider']}")
```

#### 응답 예시

```json
{
  "transcription": "안녕하세요, 음성 인식 테스트입니다.",
  "filename": "audio.wav",
  "audio_format": "wav",
  "provider": "huggingface"
}
```

---

### TTS: 텍스트를 음성으로 변환

#### cURL

```bash
curl -X POST "http://localhost:8010/api/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요, 만나서 반갑습니다!",
    "speaker": "default",
    "output_format": "wav",
    "happiness": 0.6,
    "neutral": 0.4
  }' \
  --output speech.wav
```

#### Python

```python
import requests

url = "http://localhost:8010/api/tts/generate"
payload = {
    "text": "안녕하세요, 만나서 반갑습니다!",
    "speaker": "default",
    "output_format": "wav",
    # 감정 값 (합계 1.0)
    "happiness": 0.6,
    "sadness": 0.0,
    "disgust": 0.0,
    "fear": 0.0,
    "surprise": 0.0,
    "anger": 0.0,
    "other": 0.0,
    "neutral": 0.4
}

response = requests.post(url, json=payload)

# 음성 파일 저장
with open("speech.wav", "wb") as f:
    f.write(response.content)

print("✅ 음성 파일 생성 완료: speech.wav")
```

#### 감정 파라미터 설명

| 감정 | 파라미터 | 기본값 | 설명 |
|------|----------|--------|------|
| 행복 | `happiness` | 0.3077 | 밝고 긍정적인 톤 |
| 슬픔 | `sadness` | 0.0256 | 침착하고 가라앉은 톤 |
| 혐오 | `disgust` | 0.0256 | 거부감을 표현하는 톤 |
| 공포 | `fear` | 0.0256 | 긴장되고 떨리는 톤 |
| 놀람 | `surprise` | 0.0256 | 놀라움을 표현하는 톤 |
| 분노 | `anger` | 0.0256 | 강하고 거친 톤 |
| 기타 | `other` | 0.2564 | 혼합된 감정 |
| 중립 | `neutral` | 0.3077 | 평범한 톤 |

**참고**: 모든 감정 값의 합은 1.0이 되어야 합니다.

---

### 헬스 체크

```bash
curl http://localhost:8010/health
```

```json
{
  "status": "healthy",
  "services": {
    "stt": true,
    "tts": true
  }
}
```

---

## 📁 프로젝트 구조

```
XgenAudio/
├── main.py                      # 🚀 FastAPI 애플리케이션 엔트리포인트
├── pyproject.toml               # 📦 프로젝트 설정 및 의존성 (Poetry/uv)
├── requirements.txt             # 📋 pip 의존성 목록
├── .env                         # 🔐 환경 변수 (gitignore)
├── .gitignore                   # 🚫 Git 제외 파일
├── README.md                    # 📖 프로젝트 문서
│
├── controller/                  # 🎮 API 컨트롤러 (라우팅 및 요청 처리)
│   ├── router.py                # 라우터 통합
│   ├── sttController.py         # STT API 엔드포인트
│   ├── ttsController.py         # TTS API 엔드포인트
│   └── helper/
│       └── singletonHelper.py   # 의존성 주입 헬퍼
│
└── service/                     # 🔧 비즈니스 로직 및 서비스
    ├── redis/                   # Redis 설정 관리
    │   ├── config_utils.py      # 설정 조회 유틸리티
    │   └── redis_config_manager.py  # Redis 설정 관리자
    │
    ├── stt/                     # 🎤 STT 서비스
    │   ├── base_stt.py          # STT 베이스 클래스
    │   ├── stt_factory.py       # STT 팩토리 (제공자 선택)
    │   └── huggingface_stt.py   # HuggingFace Transformers STT
    │
    └── tts/                     # 🔊 TTS 서비스
        ├── base_tts.py          # TTS 베이스 클래스
        ├── tts_factory.py       # TTS 팩토리 (제공자 선택)
        ├── zonos_tts.py         # Zonos TTS 구현
        └── zonos/               # Zonos TTS 모델 코드
            ├── model.py
            ├── config.py
            ├── conditioning.py
            └── ...
```

---

## 🛠 개발

### 코드 포맷팅

```bash
# Black으로 코드 포맷팅
black .

# isort로 import 정리
isort .

# 한 번에 실행
black . && isort .
```

### 린팅

```bash
# Flake8 린팅
flake8 .

# MyPy 타입 체크
mypy .
```

### 테스트

```bash
# pytest 실행
pytest

# 커버리지 포함
pytest --cov=controller --cov=service

# 특정 테스트 파일 실행
pytest tests/test_stt.py -v
```

### 개발 서버 (자동 리로드)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

---

## 🐛 트러블슈팅

### 1. Redis 연결 실패

**증상**: `Redis Config Manager 초기화 완료` 후 서버가 멈춤

**해결책**:
```bash
# Redis 연결 확인
redis-cli -h 192.168.2.242 -p 6379 -a your_password ping

# Redis 서버 시작 (없는 경우)
redis-server

# .env 파일의 Redis 설정 확인
cat .env | grep REDIS
```

### 2. llvmlite 빌드 에러

**증상**: `llvmlite` 설치 중 cmake 에러

**해결책**:
```bash
# macOS
brew install cmake

# Ubuntu/Debian
sudo apt-get install cmake

# 또는 librosa 없이 설치 (requirements.txt에서 이미 제거됨)
pip install -r requirements.txt
```

### 3. CUDA 메모리 부족

**증상**: `CUDA out of memory`

**해결책**:
```python
# Redis 설정에서 디바이스를 CPU로 변경
update_config("stt.HUGGINGFACE_STT_MODEL_DEVICE", "cpu")
update_config("tts.ZONOS_TTS_MODEL_DEVICE", "cpu")

# 또는 더 작은 모델 사용
update_config("stt.HUGGINGFACE_STT_MODEL_NAME", "openai/whisper-base")
```

### 4. 서비스 초기화 실패

**증상**: STT/TTS 서비스 초기화 중 에러

**해결책**:
```bash
# 디버그 모드로 실행
DEBUG_MODE=true python main.py

# Redis 설정 확인
redis-cli -h 192.168.2.242 -p 6379 -a your_password
> KEYS config:*
> GET config:stt.IS_AVAILABLE_STT
```

### 5. 모델 다운로드 느림

**증상**: HuggingFace 모델 다운로드가 느리거나 실패

**해결책**:
```bash
# HuggingFace 토큰 설정
export HUGGING_FACE_HUB_TOKEN=your_token

# 또는 수동으로 모델 다운로드
from transformers import WhisperProcessor, WhisperForConditionalGeneration

model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v3")
processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")
```

### 6. 포트 충돌

**증상**: `Address already in use`

**해결책**:
```bash
# 사용 중인 프로세스 확인 및 종료
lsof -ti:8010 | xargs kill -9

# 또는 다른 포트 사용
API_PORT=8011 python main.py
```

---

## 📝 설정 관리

### Redis 설정 조회

```python
from service.redis.config_utils import get_config_value, get_stt_config, get_tts_config

# 단일 값 조회
is_available = get_config_value("stt.IS_AVAILABLE_STT", default=False)

# 카테고리 전체 조회 (SimpleNamespace)
stt_config = get_stt_config()
print(stt_config.STT_PROVIDER)
print(stt_config.HUGGINGFACE_STT_MODEL_NAME)

tts_config = get_tts_config()
print(tts_config.TTS_PROVIDER)
```

### Redis 설정 업데이트

```python
from service.redis.config_utils import update_config

# 설정 업데이트
update_config("stt.HUGGINGFACE_STT_MODEL_NAME", "openai/whisper-medium")

# 서비스 새로고침 (API 호출)
import requests
requests.post("http://localhost:8010/api/stt/refresh")
```

---

## 🤝 기여

기여는 언제나 환영합니다! 다음 절차를 따라주세요:

1. 이 저장소를 포크합니다
2. 새 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

### 코딩 스타일

- PEP 8 준수
- Black으로 포맷팅
- 타입 힌트 사용
- Docstring 작성

---

## 📄 라이선스

MIT License

---

## 📧 문의

- **Issues**: GitHub Issues 페이지에서 버그 리포트 및 기능 요청
- **Discussions**: GitHub Discussions에서 질문 및 토론

---

## 🙏 감사의 말

- [FastAPI](https://fastapi.tiangolo.com/) - 웹 프레임워크
- [HuggingFace Transformers](https://huggingface.co/transformers/) - STT 모델
- [OpenAI Whisper](https://github.com/openai/whisper) - 음성 인식 모델
- [Redis](https://redis.io/) - 설정 저장소

---

**Happy Coding! 🚀**
