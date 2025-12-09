# 이미지 Base64 변환기

고급 처리 기능을 갖춘 포괄적인 Python 이미지 Base64 변환 도구입니다. 최대한의 유연성을 위해 웹 UI와 명령줄 인터페이스를 모두 제공합니다.

## 🚀 주요 기능

### 핵심 기능
- **다중 포맷 지원**: PNG, JPG, JPEG, GIF, BMP, WEBP, TIFF, ICO
- **양방향 변환**: 이미지 ↔ Base64 완전 변환 지원
- **고급 처리**: 크기 조정, 회전, 뒤집기, 압축, 포맷 변환
- **배치 처리**: 진행률 추적과 함께 여러 파일 동시 처리

### 사용자 경험
- **현대적 웹 UI**: 실시간 미리보기가 있는 드래그 앤 드롭 인터페이스
- **명령줄 도구**: 자동화 및 배치 처리에 완벽
- **실시간 진행률**: WebSocket 기반 실시간 처리 업데이트
- **원클릭 복사**: Base64 데이터를 클립보드로 직접 복사

### 성능 및 보안
- **지능형 캐싱**: 스마트 캐싱으로 중복 처리 방지
- **메모리 최적화**: 스트리밍으로 대용량 파일 효율적 처리
- **보안 검증**: 포괄적인 파일 보안 스캔
- **병렬 처리**: 더 나은 성능을 위한 멀티스레드 처리

### 고급 기능
- **이미지 편집**: 기본 편집 작업 (회전, 뒤집기, 크기 조정)
- **품질 제어**: 조정 가능한 압축 및 품질 설정
- **포맷 변환**: 다양한 이미지 포맷 간 변환
- **처리 기록**: 이전 변환 추적 및 재사용

### 아키텍처 개선사항 (v2.0)
- **의존성 주입**: 유지보수가 쉽고 확장 가능한 아키텍처
- **서비스 레이어**: 비즈니스 로직과 인프라 관심사 분리
- **인터페이스 기반 설계**: 확장성과 모듈성 향상
- **통합 에러 처리**: 일관된 에러 처리 및 사용자 친화적 메시지
- **성능 최적화**: 메모리 효율성 및 스트리밍 처리 개선

## 📦 설치 및 설정

### 빠른 시작 (Windows - 권장)
1. **의존성 설치**: `install_dependencies.bat` 더블클릭
2. **웹 UI 실행**: `run_web.bat` 더블클릭
3. **애플리케이션 접속**: 브라우저에서 http://localhost:5000 열기

### 수동 설치
```bash
# 저장소 복제
git clone <repository-url>
cd image-base64-converter

# 의존성 설치
pip install -r requirements.txt

# 웹 애플리케이션 실행
python run_web.py

# 또는 CLI 사용
python main.py image.png
```

### 시스템 요구사항
- **Python**: 3.7 이상
- **메모리**: 최소 2GB RAM (대용량 파일의 경우 4GB 권장)
- **저장공간**: 애플리케이션용 100MB + 캐시 공간
- **운영체제**: Windows, macOS, Linux

### 의존성
- **PIL/Pillow**: 이미지 처리
- **Flask**: 웹 프레임워크
- **Flask-SocketIO**: 실시간 통신
- **psutil**: 시스템 모니터링
- **추가**: 전체 목록은 `requirements.txt` 참조

## 🎯 사용 가이드

### 웹 인터페이스 (권장)

#### 기본 변환
1. **실행**: `run_web.bat` 실행 또는 `python run_web.py`
2. **접속**: 브라우저에서 http://localhost:5000 열기
3. **변환**: 이미지를 드래그 앤 드롭하거나 클릭하여 파일 선택
4. **복사**: 복사 버튼을 클릭하여 Base64 데이터 가져오기

#### 고급 처리
1. **옵션 선택**: 크기 조정, 품질, 포맷, 회전 설정 선택
2. **미리보기**: 변환 전후 비교 확인
3. **배치 처리**: 여러 파일을 동시에 처리하도록 선택
4. **진행률 모니터링**: WebSocket 업데이트로 실시간 진행률 확인

#### 웹 UI에서 사용 가능한 기능
- **이미지 편집**: 이미지 크기 조정, 회전, 뒤집기, 압축
- **포맷 변환**: PNG, JPEG, WEBP 등 간 변환
- **품질 제어**: 압축 레벨 및 품질 조정
- **배치 작업**: 진행률 추적과 함께 여러 파일 처리
- **기록**: 이전 변환 보기 및 재사용
- **캐시 관리**: 캐시 모니터링 및 정리

### 명령줄 인터페이스 (v2.0 개선)

#### 기본 사용법
```bash
# 단일 이미지 변환
python main.py image.png

# 파일로 저장
python main.py image.png -o output.txt

# 디렉토리 배치 처리
python main.py /path/to/images/ -o /path/to/output/

# Windows 배치 파일
run_cli.bat
```

#### 고급 CLI 옵션
```bash
# 상세 출력으로 단일 파일 변환
python main.py image.png --verbose

# 강제 덮어쓰기로 파일 저장
python main.py image.png -o output.txt --force

# 디렉토리의 모든 이미지 처리
python main.py ./images/ --verbose

# 환경 변수로 설정 파일 지정
CONFIG_FILE=config.production.json python main.py image.png
```

#### 새로운 아키텍처 기능
- **의존성 주입**: 모든 서비스가 컨테이너를 통해 관리됨
- **개선된 에러 처리**: 사용자 친화적인 에러 메시지
- **통합 로깅**: 구조화된 로그와 컨텍스트 정보
- **캐싱 최적화**: 지능형 캐시 키 생성 및 관리
- **메모리 효율성**: 대용량 파일을 위한 스트리밍 처리

### API 통합

#### REST API
```python
import requests

# 기본 변환
files = {'file': open('image.png', 'rb')}
response = requests.post('http://localhost:5000/api/convert/to-base64', files=files)
result = response.json()

# 고급 처리
options = {
    'resize_width': 800,
    'quality': 90,
    'target_format': 'JPEG'
}
data = {'options': json.dumps(options)}
response = requests.post('http://localhost:5000/api/convert/to-base64-advanced', 
                        files=files, data=data)
```

#### WebSocket 통합
```javascript
const socket = io();

// 업데이트를 위한 큐 참여
socket.emit('join_queue', {queue_id: 'your-queue-id'});

// 진행률 수신
socket.on('batch_progress', (data) => {
    console.log(`진행률: ${data.progress_percentage}%`);
});
```

## 📋 출력 형식 및 예제

### Data URI 형식
변환된 결과는 즉시 사용 가능한 Data URI 형식으로 출력됩니다:
```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

### 사용 예제

#### HTML 통합
```html
<img src="data:image/png;base64,..." alt="변환된 이미지">
<div style="background-image: url('data:image/jpeg;base64,...')"></div>
```

#### CSS 통합
```css
.background {
    background-image: url('data:image/webp;base64,...');
}
```

#### JavaScript 통합
```javascript
const img = new Image();
img.src = 'data:image/png;base64,...';
document.body.appendChild(img);
```

## 🎨 지원 포맷

### 입력 포맷
- **PNG**: 무손실 압축, 투명도 지원
- **JPEG/JPG**: 손실 압축, 작은 파일 크기
- **WEBP**: 현대적 포맷, 뛰어난 압축률
- **GIF**: 애니메이션 지원, 제한된 색상
- **BMP**: 비압축, 큰 파일 크기
- **TIFF**: 고품질, 다중 페이지
- **ICO**: 아이콘 포맷, 다중 크기

### 출력 포맷
모든 입력 포맷과 최적화된 변형:
- **PNG**: 최적화된 압축 레벨
- **JPEG**: 품질 제어 (1-100)
- **WEBP**: 고급 압축 옵션
- **포맷 변환**: 지원되는 모든 포맷 간 변환

### 처리 기능
- **크기 조정**: 종횡비 유지 또는 사용자 정의 크기
- **회전**: 90°, 180°, 270° 회전
- **뒤집기**: 수평 및 수직 뒤집기
- **압축**: 품질 조정 및 최적화
- **변환**: 처리 중 포맷 변경

## 📁 프로젝트 구조 (v2.0 리팩토링)

```
image-base64-converter/
├── src/                                    # 소스 코드
│   ├── core/                              # 핵심 레이어
│   │   ├── interfaces/                    # 인터페이스 정의
│   │   │   ├── image_converter.py        # 이미지 변환 인터페이스
│   │   │   ├── file_handler.py           # 파일 처리 인터페이스
│   │   │   └── cache_manager.py          # 캐시 관리 인터페이스
│   │   ├── services/                      # 비즈니스 로직 서비스
│   │   │   ├── image_conversion_service.py # 이미지 변환 서비스
│   │   │   ├── file_handler_service.py   # 파일 처리 서비스
│   │   │   ├── cache_manager_service.py  # 캐시 관리 서비스
│   │   │   ├── streaming_image_processor.py # 스트리밍 처리
│   │   │   └── memory_optimized_conversion_service.py # 메모리 최적화
│   │   ├── factories/                     # 객체 생성 팩토리
│   │   │   ├── service_factory.py        # 서비스 팩토리
│   │   │   └── cache_factory.py          # 캐시 팩토리
│   │   ├── config/                        # 설정 관리
│   │   │   ├── app_config.py             # 애플리케이션 설정
│   │   │   ├── config_factory.py         # 설정 팩토리
│   │   │   └── unified_config_manager.py # 통합 설정 관리자
│   │   ├── logging/                       # 로깅 시스템
│   │   │   ├── unified_logger.py         # 통합 로거
│   │   │   ├── log_handlers.py           # 로그 핸들러
│   │   │   └── log_formatters.py         # 로그 포매터
│   │   ├── utils/                         # 유틸리티
│   │   │   ├── memory_optimizer.py       # 메모리 최적화
│   │   │   ├── memory_pool.py            # 메모리 풀
│   │   │   ├── path_utils.py             # 경로 유틸리티
│   │   │   ├── type_utils.py             # 타입 유틸리티
│   │   │   └── validation_utils.py       # 검증 유틸리티
│   │   ├── adapters/                      # 어댑터 패턴
│   │   │   ├── legacy_image_converter_adapter.py # 레거시 호환성
│   │   │   ├── image_converter_adapter.py # 이미지 변환 어댑터
│   │   │   ├── file_handler_adapter.py   # 파일 처리 어댑터
│   │   │   └── config_adapter.py         # 설정 어댑터
│   │   ├── base/                          # 기본 클래스
│   │   │   └── result.py                 # Result 패턴
│   │   ├── container.py                   # 의존성 주입 컨테이너
│   │   ├── error_handler.py              # 중앙화된 에러 처리
│   │   └── structured_logger.py          # 구조화된 로깅
│   ├── domain/                            # 도메인 레이어
│   │   └── exceptions/                    # 도메인 예외
│   │       ├── base.py                   # 기본 예외
│   │       ├── validation.py             # 검증 예외
│   │       ├── file_system.py            # 파일 시스템 예외
│   │       ├── processing.py             # 처리 예외
│   │       ├── cache.py                  # 캐시 예외
│   │       ├── security.py               # 보안 예외
│   │       └── queue.py                  # 큐 예외
│   ├── models/                            # 데이터 모델
│   │   ├── models.py                     # 핵심 모델
│   │   └── processing_options.py         # 처리 옵션
│   ├── web/                               # 웹 애플리케이션
│   │   ├── web_app.py                    # Flask 애플리케이션
│   │   ├── refactored_app.py             # 리팩토링된 앱
│   │   ├── handlers.py                   # 요청 핸들러
│   │   ├── middleware.py                 # 미들웨어
│   │   ├── error_formatter.py            # 에러 포매터
│   │   └── test_integration.py           # 통합 테스트
│   ├── templates/                         # HTML 템플릿
│   ├── static/                            # 정적 자산
│   ├── cli.py                            # CLI 인터페이스
│   └── __init__.py

├── .kiro/                                # Kiro 설정
│   └── specs/code-refactoring/           # 리팩토링 스펙
│       ├── requirements.md               # 요구사항
│       ├── design.md                     # 설계 문서
│       ├── tasks.md                      # 작업 목록
│       ├── MIGRATION_GUIDE.md           # 마이그레이션 가이드
│       └── examples/                     # 예제 코드
├── logs/                                  # 애플리케이션 로그
├── cache/                                 # 캐시 디렉토리
├── data/                                  # 데이터 디렉토리
├── temp/                                  # 임시 파일
├── main.py                               # CLI 진입점
├── run_web.py                            # 웹 서버 런처
├── performance_demo.py                   # 성능 데모
├── requirements.txt                      # Python 의존성
├── config.json                           # 기본 설정
├── config.production.json                # 프로덕션 설정
├── docker-compose.yml                    # Docker Compose
├── Dockerfile                            # Docker 설정
├── install_dependencies.bat              # Windows 설치 스크립트
├── run_web.bat                          # Windows 웹 런처
├── run_cli.bat                          # Windows CLI 런처
├── docs/                                # 문서 디렉토리
│   ├── API_ENDPOINTS.md                # API 문서
│   ├── ARCHITECTURE.md                 # 아키텍처 문서
│   ├── CHANGELOG.md                    # 변경 로그
│   ├── DEPLOYMENT.md                   # 배포 가이드
│   ├── MIGRATION_GUIDE.md              # 마이그레이션 가이드

└── README.md                           # 이 파일
```

## 🔧 설정 (v2.0 통합 설정 시스템)

### 환경 변수
```bash
# 캐시 설정
CACHE_DIR=./cache
CACHE_MAX_SIZE_MB=100
CACHE_MAX_AGE_HOURS=24

# 보안 설정
MAX_FILE_SIZE_MB=10
ENABLE_SECURITY_SCAN=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# 성능 설정
MAX_CONCURRENT_PROCESSING=3
ENABLE_MEMORY_OPTIMIZATION=true
PARALLEL_PROCESSING_WORKERS=4

# 로깅 설정
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true
LOG_DIR=./logs

# 설정 파일 지정
CONFIG_FILE=config.production.json
```

### 설정 파일 (통합 관리)
- **config.json**: 개발 환경 기본 설정
- **config.production.json**: 프로덕션 환경 설정
- **통합 설정 관리자**: 환경변수, 파일, 기본값의 우선순위 관리
- **의존성 주입**: 설정 기반 서비스 구성 자동화

### 새로운 설정 기능
- **설정 팩토리**: 다양한 소스에서 설정 로드
- **설정 검증**: 시작 시 설정 유효성 검사
- **동적 설정**: 런타임 설정 업데이트 지원
- **환경별 설정**: 개발/프로덕션 환경 분리

## 🧪 성능 데모

### 성능 데모 실행
```bash
# 성능 데모 (배치 처리 및 메모리 최적화 시연)
python performance_demo.py
```

이 데모는 다음을 시연합니다:
- 배치 처리 성능
- 메모리 최적화 효과
- 병렬 처리 효율성

## 🚀 배포

### 프로덕션 고려사항
- **보안**: 인증 및 권한 부여 구현
- **확장성**: 로드 밸런서 및 다중 인스턴스 사용
- **모니터링**: 로깅 및 성능 모니터링 설정
- **캐싱**: 분산 캐싱을 위한 Redis 또는 유사한 도구 구성

### Docker 배포
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "run_web.py"]
```

## 📚 문서

상세한 문서는 **[docs/](docs/)** 폴더에서 확인할 수 있습니다:

- **[아키텍처 가이드](docs/ARCHITECTURE.md)** - v2.0 리팩토링된 시스템 구조
- **[API 문서](docs/API_ENDPOINTS.md)** - REST API 및 WebSocket 가이드  
- **[배포 가이드](docs/DEPLOYMENT.md)** - 개발/프로덕션 환경 배포
- **[마이그레이션 가이드](docs/MIGRATION_GUIDE.md)** - v1.x → v2.0 업그레이드
- **[변경 로그](docs/CHANGELOG.md)** - 버전별 개선사항


## 🤝 기여하기

1. **저장소 포크**
2. **기능 브랜치 생성** (`git checkout -b feature/amazing-feature`)
3. **변경사항 커밋** (`git commit -m 'Add amazing feature'`)
4. **브랜치에 푸시** (`git push origin feature/amazing-feature`)
5. **Pull Request 열기**

### 개발 환경 설정
```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 모드로 웹 서버 실행
python run_web.py
```

### 아키텍처 가이드라인
- **의존성 주입**: 새로운 서비스는 인터페이스를 통해 주입받도록 구현
- **Result 패턴**: 에러 처리는 Result 패턴을 사용
- **단일 책임 원칙**: 각 클래스는 하나의 책임만 가지도록 설계
- **인터페이스 분리**: 큰 인터페이스는 작은 인터페이스로 분리
- **코드 품질**: 타입 힌트와 docstring 작성

## 📄 라이선스

MIT 라이선스 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- **Pillow**: 이미지 처리를 위한 Python 이미징 라이브러리
- **Flask**: 경량 웹 프레임워크
- **Socket.IO**: 실시간 통신
- **기여자들**: 이 프로젝트 개선에 도움을 주신 모든 기여자분들께 감사드립니다