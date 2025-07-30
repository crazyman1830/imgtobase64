# 아키텍처 문서 (v2.0)

이 문서는 이미지 Base64 변환기의 리팩토링된 아키텍처에 대한 상세한 설명을 제공합니다.

## 개요

v2.0에서는 기존 시스템을 대폭 리팩토링하여 다음과 같은 아키텍처 원칙을 적용했습니다:

- **의존성 역전 원칙**: 고수준 모듈이 저수준 모듈에 의존하지 않도록 인터페이스 사용
- **단일 책임 원칙**: 각 클래스와 모듈이 하나의 책임만 가지도록 구조화
- **개방-폐쇄 원칙**: 확장에는 열려있고 수정에는 닫혀있는 구조
- **레이어드 아키텍처**: 명확한 레이어 분리로 관심사 분리

## 아키텍처 레이어

### 1. 프레젠테이션 레이어 (Presentation Layer)

사용자 인터페이스와 외부 요청을 처리하는 레이어입니다.

```
src/
├── cli.py                    # 명령줄 인터페이스
└── web/                      # 웹 인터페이스
    ├── web_app.py           # Flask 애플리케이션
    ├── refactored_app.py    # 리팩토링된 웹 앱
    ├── handlers.py          # 요청 핸들러
    ├── middleware.py        # 미들웨어
    └── error_formatter.py   # 에러 포매터
```

**주요 특징:**
- 의존성 주입 컨테이너를 통한 서비스 접근
- Result 패턴을 사용한 일관된 응답 처리
- 중앙화된 에러 처리 및 포매팅

### 2. 애플리케이션 레이어 (Application Layer)

비즈니스 로직을 조율하고 서비스 간 상호작용을 관리하는 레이어입니다.

```
src/core/
├── services/                 # 비즈니스 로직 서비스
│   ├── image_conversion_service.py
│   ├── file_handler_service.py
│   ├── cache_manager_service.py
│   ├── streaming_image_processor.py
│   └── memory_optimized_conversion_service.py
├── factories/               # 객체 생성 팩토리
│   ├── service_factory.py
│   └── cache_factory.py
└── container.py            # 의존성 주입 컨테이너
```

**주요 특징:**
- 서비스 레이어 패턴으로 비즈니스 로직 캡슐화
- 팩토리 패턴으로 객체 생성 관리
- 의존성 주입으로 테스트 가능성 향상

### 3. 도메인 레이어 (Domain Layer)

핵심 비즈니스 규칙과 도메인 모델을 포함하는 레이어입니다.

```
src/
├── domain/
│   └── exceptions/          # 도메인 예외
│       ├── base.py
│       ├── validation.py
│       ├── file_system.py
│       ├── processing.py
│       ├── cache.py
│       ├── security.py
│       └── queue.py
└── models/                  # 데이터 모델
    ├── models.py
    └── processing_options.py
```

**주요 특징:**
- 도메인 특화 예외 계층 구조
- 비즈니스 규칙을 반영한 데이터 모델
- 외부 의존성이 없는 순수한 도메인 로직

### 4. 인프라스트럭처 레이어 (Infrastructure Layer)

외부 시스템과의 통신 및 기술적 구현을 담당하는 레이어입니다.

```
src/core/
├── interfaces/              # 인터페이스 정의
│   ├── image_converter.py
│   ├── file_handler.py
│   └── cache_manager.py
├── adapters/               # 어댑터 패턴
│   ├── legacy_image_converter_adapter.py
│   ├── image_converter_adapter.py
│   ├── file_handler_adapter.py
│   └── config_adapter.py
├── config/                 # 설정 관리
│   ├── app_config.py
│   ├── config_factory.py
│   └── unified_config_manager.py
├── logging/                # 로깅 시스템
│   ├── unified_logger.py
│   ├── log_handlers.py
│   └── log_formatters.py
└── utils/                  # 유틸리티
    ├── memory_optimizer.py
    ├── memory_pool.py
    ├── path_utils.py
    ├── type_utils.py
    └── validation_utils.py
```

**주요 특징:**
- 인터페이스 기반 설계로 구현체 교체 가능
- 어댑터 패턴으로 레거시 코드 호환성 유지
- 통합 설정 관리 시스템

## 핵심 디자인 패턴

### 1. 의존성 주입 (Dependency Injection)

```python
class ImageConversionService:
    def __init__(
        self,
        converter: IImageConverter,
        file_handler: IFileHandler,
        cache_manager: ICacheManager
    ):
        self._converter = converter
        self._file_handler = file_handler
        self._cache_manager = cache_manager
```

**장점:**
- 테스트 가능성 향상
- 느슨한 결합
- 확장성 개선

### 2. Result 패턴

```python
@dataclass
class ConversionResult:
    success: bool
    data: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**장점:**
- 명시적인 에러 처리
- 예외 없는 안전한 코드
- 일관된 반환 타입

### 3. 팩토리 패턴

```python
class ServiceFactory:
    @staticmethod
    def create_conversion_service(config: AppConfig) -> ImageConversionService:
        converter = ServiceFactory._create_converter(config)
        file_handler = ServiceFactory._create_file_handler(config)
        cache_manager = ServiceFactory._create_cache_manager(config)
        
        return ImageConversionService(converter, file_handler, cache_manager)
```

**장점:**
- 객체 생성 로직 중앙화
- 설정 기반 구현체 선택
- 복잡한 의존성 관리

### 4. 어댑터 패턴

```python
class ImageConverterAdapter:
    def __init__(self):
        self._container = DIContainer.create_default()
        self._service = self._container.get('image_conversion_service')
    
    def convert_to_base64(self, file_path: str) -> ConversionResult:
        # 기존 인터페이스를 새로운 서비스로 연결
        return self._service.convert_image(file_path)
```

**장점:**
- 레거시 코드 호환성
- 점진적 마이그레이션 지원
- 기존 API 유지

## 데이터 흐름

### 1. CLI 요청 처리 흐름

```
CLI Input → CLI Class → DI Container → Service Layer → Domain Logic → Infrastructure
```

1. **CLI 입력**: 사용자가 명령줄에서 이미지 변환 요청
2. **CLI 클래스**: 인자 파싱 및 검증
3. **DI 컨테이너**: 필요한 서비스 인스턴스 제공
4. **서비스 레이어**: 비즈니스 로직 실행
5. **도메인 로직**: 핵심 변환 규칙 적용
6. **인프라스트럭처**: 파일 I/O, 캐싱 등 기술적 구현

### 2. 웹 요청 처리 흐름

```
HTTP Request → Web Handler → Service Layer → Result → Response Formatter → HTTP Response
```

1. **HTTP 요청**: 클라이언트에서 API 호출
2. **웹 핸들러**: 요청 파라미터 추출 및 검증
3. **서비스 레이어**: 비즈니스 로직 실행
4. **Result 객체**: 성공/실패 결과 반환
5. **응답 포매터**: 일관된 JSON 응답 생성
6. **HTTP 응답**: 클라이언트로 결과 전송

## 성능 최적화

### 1. 메모리 최적화

```python
class MemoryOptimizer:
    def __init__(self, max_memory_mb: int = 100):
        self._max_memory_mb = max_memory_mb
        self._memory_pool = MemoryPool()
    
    def optimize_memory_usage(self):
        # 메모리 사용량 모니터링 및 최적화
        pass
```

**특징:**
- 메모리 풀링으로 객체 재사용
- 가비지 컬렉션 최적화
- 메모리 사용량 모니터링

### 2. 스트리밍 처리

```python
class StreamingImageProcessor:
    def process_large_file(self, file_path: str, chunk_size: int = 1024*1024):
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield self._process_chunk(chunk)
```

**특징:**
- 대용량 파일을 청크 단위로 처리
- 메모리 사용량 제한
- 실시간 처리 가능

### 3. 캐싱 전략

```python
class CacheManagerService:
    def get_cache_key(self, file_path: str, options: ProcessingOptions) -> str:
        # 파일 경로와 처리 옵션을 기반으로 고유 키 생성
        file_hash = self._get_file_hash(file_path)
        options_hash = self._get_options_hash(options)
        return f"{file_hash}:{options_hash}"
```

**특징:**
- 지능형 캐시 키 생성
- 다중 백엔드 지원 (메모리, 디스크, Redis)
- TTL 및 LRU 정책 지원

## 에러 처리 전략

### 1. 계층별 에러 처리

```python
# 도메인 레이어
class ValidationError(ImageConverterError):
    error_code = "VALIDATION_ERROR"

# 애플리케이션 레이어
class ImageConversionService:
    def convert_image(self, file_path: str) -> ConversionResult:
        try:
            # 비즈니스 로직 실행
            pass
        except ValidationError as e:
            return ConversionResult(success=False, error_message=str(e))

# 프레젠테이션 레이어
class CLI:
    def process_single_file(self, file_path: str):
        result = self._conversion_service.convert_image(file_path)
        if not result.success:
            print(f"Error: {result.error_message}")
```

**특징:**
- 계층별 적절한 에러 처리
- 사용자 친화적 에러 메시지
- 구조화된 로깅

### 2. 중앙화된 에러 핸들러

```python
class ErrorHandler:
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> ErrorResponse:
        # 에러 타입별 처리 로직
        error_response = self._create_error_response(error)
        self._log_error(error, context)
        return error_response
```

**특징:**
- 일관된 에러 처리 로직
- 컨텍스트 정보 포함
- 자동 로깅 및 모니터링

## 테스트 전략

### 1. 단위 테스트

```python
class TestImageConversionService:
    def setUp(self):
        # 모킹된 의존성으로 테스트 환경 구성
        self.mock_converter = Mock(spec=IImageConverter)
        self.mock_file_handler = Mock(spec=IFileHandler)
        self.mock_cache_manager = Mock(spec=ICacheManager)
        
        self.service = ImageConversionService(
            self.mock_converter,
            self.mock_file_handler,
            self.mock_cache_manager
        )
```

**특징:**
- 의존성 주입으로 쉬운 모킹
- 각 컴포넌트 독립적 테스트
- 높은 테스트 커버리지

### 2. 통합 테스트

```python
class TestIntegration:
    def test_end_to_end_conversion(self):
        # 실제 DI 컨테이너 사용
        container = DIContainer.create_for_testing()
        service = container.get('image_conversion_service')
        
        # 실제 파일로 테스트
        result = service.convert_image("test_image.jpg")
        self.assertTrue(result.success)
```

**특징:**
- 실제 환경과 유사한 테스트
- 전체 워크플로우 검증
- 성능 및 메모리 사용량 측정

## 확장성 고려사항

### 1. 새로운 이미지 포맷 지원

```python
class WebPConverter(IImageConverter):
    def convert_to_base64(self, file_path: str, options: ProcessingOptions) -> ConversionResult:
        # WebP 특화 변환 로직
        pass

# 팩토리에서 새로운 컨버터 등록
ServiceFactory.register_converter("webp", WebPConverter)
```

### 2. 새로운 캐시 백엔드 추가

```python
class RedisCache(ICacheManager):
    def get(self, key: str) -> Optional[Any]:
        # Redis 구현
        pass

# 팩토리에서 새로운 캐시 등록
CacheFactory.register_cache_type("redis", RedisCache)
```

### 3. 새로운 처리 옵션 추가

```python
@dataclass
class ProcessingOptions:
    # 기존 옵션들...
    watermark_text: Optional[str] = None  # 새로운 옵션 추가
    
    def __post_init__(self):
        # 새로운 옵션 검증 로직
        pass
```

## 모니터링 및 관찰성

### 1. 구조화된 로깅

```python
logger.log_operation_start("convert_image", extra={
    "file_path": file_path,
    "file_size": file_size,
    "options": options.to_dict()
})
```

### 2. 메트릭 수집

```python
class MetricsCollector:
    def record_conversion_time(self, duration: float):
        # 변환 시간 메트릭 기록
        pass
    
    def record_cache_hit_rate(self, hit_rate: float):
        # 캐시 히트율 메트릭 기록
        pass
```

### 3. 헬스 체크

```python
class HealthChecker:
    def check_system_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "cache_status": self._check_cache(),
            "memory_usage": self._check_memory(),
            "disk_space": self._check_disk_space()
        }
```

이 아키텍처는 확장 가능하고 유지보수가 쉬우며, 테스트 가능한 시스템을 제공합니다. 각 레이어가 명확히 분리되어 있어 개별적으로 수정하거나 확장할 수 있으며, 의존성 주입을 통해 높은 유연성을 제공합니다.