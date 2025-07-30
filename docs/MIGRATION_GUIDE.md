# 코드 리팩토링 마이그레이션 가이드

이 문서는 기존 이미지 변환 시스템에서 새로운 리팩토링된 구조로 마이그레이션하는 방법을 안내합니다.

## 개요

리팩토링된 시스템은 다음과 같은 주요 개선사항을 제공합니다:

- **의존성 주입**: 테스트 가능하고 확장 가능한 구조
- **Result 패턴**: 예외 대신 명시적인 에러 처리
- **캐싱 시스템**: 성능 향상을 위한 통합 캐싱
- **구조화된 로깅**: 더 나은 디버깅과 모니터링
- **설정 관리**: 단순화된 설정 시스템

## 마이그레이션 전략

### 1단계: 점진적 마이그레이션 (권장)

기존 코드를 한 번에 모두 변경하지 않고, 점진적으로 마이그레이션하는 방법입니다.

#### 1.1 Legacy Adapter 사용

기존 코드를 최소한으로 수정하면서 새로운 기능을 활용할 수 있습니다.

**기존 코드:**
```python
from src.core.converter import ImageConverter
from src.core.file_handler import FileHandler

# 기존 방식
converter = ImageConverter()
file_handler = FileHandler()

result = converter.convert_to_base64("image.jpg")
files = file_handler.find_image_files("/path/to/images")
```

**마이그레이션된 코드:**
```python
from src.core.adapters import ImageConverterAdapter, FileHandlerAdapter

# 어댑터 사용 (기존 인터페이스 유지)
converter = ImageConverterAdapter()
file_handler = FileHandlerAdapter()

# 기존 코드와 동일하게 사용 가능
result = converter.convert_to_base64("image.jpg")
files = file_handler.find_image_files("/path/to/images")

# 추가로 새로운 기능도 사용 가능
cache_stats = converter.get_cache_stats()
converter.clear_cache()
```

#### 1.2 Import 변경만으로 마이그레이션

가장 간단한 마이그레이션 방법입니다:

```python
# 기존 import
# from src.core.converter import ImageConverter
# from src.core.file_handler import FileHandler

# 새로운 import (어댑터 사용)
from src.core.adapters.image_converter_adapter import ImageConverterAdapter as ImageConverter
from src.core.adapters.file_handler_adapter import FileHandlerAdapter as FileHandler

# 나머지 코드는 변경 없음
converter = ImageConverter()
file_handler = FileHandler()
```

### 2단계: 새로운 서비스 레이어 활용

더 나은 성능과 기능을 위해 새로운 서비스 레이어를 직접 사용합니다.

#### 2.1 의존성 주입 패턴 사용

**기존 코드:**
```python
from src.core.converter import ImageConverter

converter = ImageConverter()
result = converter.convert_to_base64("image.jpg")
```

**새로운 코드:**
```python
from src.core.factories.service_factory import ServiceFactory
from src.core.config.app_config import AppConfig
from src.models.processing_options import ProcessingOptions

# 설정 로드
config = AppConfig.from_env()

# 서비스 팩토리를 통한 의존성 주입
conversion_service = ServiceFactory.create_conversion_service(config)

# 처리 옵션 설정
options = ProcessingOptions(
    enable_caching=True,
    max_file_size_mb=10
)

# 변환 실행
result = conversion_service.convert_image("image.jpg", options)
```

#### 2.2 Result 패턴 활용

예외 처리 대신 Result 패턴을 사용하여 더 안전한 코드를 작성할 수 있습니다.

**기존 코드:**
```python
try:
    files = file_handler.find_image_files("/path/to/images")
    for file_path in files:
        result = converter.convert_to_base64(file_path)
        if result.success:
            print(f"Converted: {file_path}")
        else:
            print(f"Failed: {result.error_message}")
except Exception as e:
    print(f"Error: {e}")
```

**새로운 코드:**
```python
from src.core.services.file_handler_service import FileHandlerService

file_service = FileHandlerService()

# Result 패턴 사용
files_result = file_service.find_image_files_safe("/path/to/images")

if files_result.is_success:
    files = files_result.value
    for file_path in files:
        result = conversion_service.convert_image(file_path)
        if result.success:
            print(f"Converted: {file_path}")
        else:
            print(f"Failed: {result.error_message}")
else:
    print(f"Error finding files: {files_result.error}")
```

## 단계별 마이그레이션 체크리스트

### Phase 1: 준비 단계
- [ ] 새로운 의존성 설치 확인
- [ ] 기존 코드 백업
- [ ] 테스트 환경에서 어댑터 테스트
- [ ] 설정 파일 검토 및 업데이트

### Phase 2: 어댑터 도입
- [ ] 기존 import 문을 어댑터로 변경
- [ ] 기본 기능 테스트
- [ ] 에러 처리 동작 확인
- [ ] 성능 비교 테스트

### Phase 3: 새로운 기능 활용
- [ ] 캐싱 기능 활성화
- [ ] 구조화된 로깅 설정
- [ ] 성능 모니터링 도구 연결
- [ ] 새로운 설정 옵션 적용

### Phase 4: 완전 마이그레이션
- [ ] 서비스 레이어 직접 사용으로 전환
- [ ] Result 패턴 적용
- [ ] 의존성 주입 패턴 적용
- [ ] 레거시 코드 제거

## 주요 변경사항 및 주의사항

### 1. 예외 처리 변경

**기존 방식:**
```python
try:
    result = converter.convert_to_base64("image.jpg")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except UnsupportedFormatError as e:
    print(f"Unsupported format: {e}")
```

**새로운 방식 (어댑터 사용 시):**
```python
# 어댑터는 기존 예외 처리 방식 유지
try:
    result = converter.convert_to_base64("image.jpg")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except UnsupportedFormatError as e:
    print(f"Unsupported format: {e}")
```

**새로운 방식 (서비스 직접 사용 시):**
```python
# Result 패턴 사용 (예외 없음)
result = conversion_service.convert_image("image.jpg")
if not result.success:
    print(f"Conversion failed: {result.error_message}")
```

### 2. 설정 관리 변경

**기존 방식:**
```python
from src.config import AppConfig

config = AppConfig()
# 복잡한 설정 관리
```

**새로운 방식:**
```python
from src.core.config.app_config import AppConfig

# 환경변수에서 자동 로드
config = AppConfig.from_env()

# 또는 파일에서 로드
config = AppConfig.from_file("config.json")
```

### 3. 로깅 시스템 변경

**기존 방식:**
```python
import logging

logger = logging.getLogger(__name__)
logger.info("Processing image")
```

**새로운 방식:**
```python
from src.core.logging.unified_logger import get_unified_logger

logger = get_unified_logger("image_processing")
logger.log_operation_start("convert_image", file_path="image.jpg")
```

## 성능 최적화 활용

### 캐싱 활용

```python
from src.core.factories.service_factory import ServiceFactory
from src.core.config.app_config import AppConfig

# 캐싱이 활성화된 설정
config = AppConfig(
    cache_enabled=True,
    cache_type="memory",  # 또는 "disk", "redis"
    cache_ttl_seconds=3600
)

service = ServiceFactory.create_conversion_service(config)

# 첫 번째 호출 - 실제 변환 수행
result1 = service.convert_image("image.jpg")
print(f"Cache hit: {result1.cache_hit}")  # False

# 두 번째 호출 - 캐시에서 반환
result2 = service.convert_image("image.jpg")
print(f"Cache hit: {result2.cache_hit}")  # True
```

### 스트리밍 처리 활용

```python
from src.core.services.streaming_file_handler import StreamingFileHandler

# 대용량 파일 처리
streaming_handler = StreamingFileHandler()

# 청크 단위로 파일 처리
for chunk in streaming_handler.read_file_chunks("large_image.jpg", chunk_size=1024*1024):
    # 메모리 효율적인 처리
    process_chunk(chunk)
```

## 테스트 전략

### 1. 기존 기능 검증

```python
import unittest
from src.core.adapters import ImageConverterAdapter, FileHandlerAdapter

class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.converter = ImageConverterAdapter()
        self.file_handler = FileHandlerAdapter()
    
    def test_backward_compatibility(self):
        """기존 인터페이스가 정상 작동하는지 확인"""
        # 기존 메서드들이 동일하게 작동하는지 테스트
        self.assertTrue(hasattr(self.converter, 'convert_to_base64'))
        self.assertTrue(hasattr(self.file_handler, 'find_image_files'))
    
    def test_new_features(self):
        """새로운 기능이 추가되었는지 확인"""
        # 새로운 메서드들이 사용 가능한지 테스트
        self.assertTrue(hasattr(self.converter, 'get_cache_stats'))
        self.assertTrue(hasattr(self.file_handler, 'read_file_safe'))
```

### 2. 성능 비교 테스트

```python
import time
from src.core.converter import ImageConverter  # 기존
from src.core.adapters import ImageConverterAdapter  # 새로운

def performance_comparison():
    old_converter = ImageConverter()
    new_converter = ImageConverterAdapter()
    
    test_file = "test_image.jpg"
    
    # 기존 방식 성능 측정
    start_time = time.time()
    old_result = old_converter.convert_to_base64(test_file)
    old_time = time.time() - start_time
    
    # 새로운 방식 성능 측정
    start_time = time.time()
    new_result = new_converter.convert_to_base64(test_file)
    new_time = time.time() - start_time
    
    print(f"기존 방식: {old_time:.4f}초")
    print(f"새로운 방식: {new_time:.4f}초")
    print(f"성능 개선: {((old_time - new_time) / old_time * 100):.2f}%")
```

## 문제 해결 가이드

### 자주 발생하는 문제들

#### 1. Import 에러
```
ImportError: cannot import name 'ImageConverterAdapter'
```

**해결방법:**
```python
# 올바른 import 경로 확인
from src.core.adapters.image_converter_adapter import ImageConverterAdapter
```

#### 2. 설정 파일 에러
```
ConfigurationError: Invalid configuration
```

**해결방법:**
```python
# 설정 파일 형식 확인
from src.core.config.app_config import AppConfig

try:
    config = AppConfig.from_file("config.json")
except Exception as e:
    # 기본 설정 사용
    config = AppConfig.from_env()
```

#### 3. 캐시 관련 에러
```
CacheError: Redis connection failed
```

**해결방법:**
```python
# 캐시 타입을 메모리로 변경
config = AppConfig(
    cache_enabled=True,
    cache_type="memory"  # Redis 대신 메모리 캐시 사용
)
```

## 롤백 계획

마이그레이션 중 문제가 발생할 경우를 대비한 롤백 계획:

### 1. 즉시 롤백
```python
# 어댑터 사용 중 문제 발생 시
# from src.core.adapters import ImageConverterAdapter as ImageConverter
from src.core.converter import ImageConverter  # 원래 클래스로 복원
```

### 2. 점진적 롤백
1. 새로운 기능 사용 중단
2. 어댑터를 통한 기본 기능만 사용
3. 필요시 완전히 기존 코드로 복원

### 3. 데이터 백업
- 캐시 데이터 백업
- 로그 파일 백업
- 설정 파일 백업

## 추가 리소스

- [API 문서](./API_DOCUMENTATION.md)
- [성능 최적화 가이드](./PERFORMANCE_GUIDE.md)
- [트러블슈팅 가이드](./TROUBLESHOOTING.md)
- [예제 코드 저장소](./examples/)

## 지원 및 문의

마이그레이션 과정에서 문제가 발생하거나 추가 지원이 필요한 경우:

1. 기존 코드와 새로운 코드의 동작 차이점 문서화
2. 성능 비교 결과 공유
3. 발생한 에러와 해결 방법 기록

이 가이드를 따라 단계적으로 마이그레이션을 진행하면 안전하고 효율적으로 새로운 시스템으로 전환할 수 있습니다.