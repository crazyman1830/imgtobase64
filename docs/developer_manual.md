# 🛠️ 개발자 매뉴얼 (Developer Manual)

이 문서는 이미지 Base64 변환기의 시스템 구조, API 명세, 그리고 코드 마이그레이션 방법을 다룹니다.

---

## 🏗️ 1. 아키텍처 (Architecture)

v2.0은 **레이어드 아키텍처**와 **의존성 주입(DI)**을 기반으로 설계되었습니다.

### 1.1 시스템 레이어
| 레이어 | 설명 | 구성 요소 |
|--------|------|-----------|
| **Presentation** | 입출력 처리 | CLI(`cli.py`), Web App(`web/`), API 핸들러 |
| **Application** | 비즈니스 로직 | Services(`core/services`), Facades |
| **Domain** | 핵심 모델/규칙 | Models(`src/models`), Exceptions(`domain/exceptions`) |
| **Infrastructure** | 기술 구현체 | File I/O, Caching, Logging, Adapters |

### 1.2 핵심 디자인 패턴
1.  **Dependency Injection**: `ServiceFactory`와 `DIContainer`를 통해 객체 의존성 관리.
2.  **Result Pattern**: 모든 서비스 메서드는 `ConversionResult`(`success`, `data`, `error_message`) 반환.
3.  **Adapter Pattern**: 레거시(v1.x) 인터페이스 호환성 지원.

---

## 🔌 2. API 레퍼런스 (API Reference)

Base URL: `http://localhost:5000`
모든 응답은 JSON 형식을 반환합니다.

### 2.1 이미지 변환 API
| Method | Endpoint | 설명 | 핵심 파라미터 |
|--------|----------|------|---------------|
| `POST` | `/api/convert/to-base64` | 기본 변환 | `file` |
| `POST` | `/api/convert/to-base64-advanced` | 고급 변환 | `file`, `options` (JSON) |
| `POST` | `/api/convert/from-base64` | 이미지 복원 | `base64`, `format` |

**Options JSON 예시:**
```json
{
  "resize_width": 800,
  "quality": 85,
  "target_format": "JPEG",
  "rotation_angle": 90
}
```

### 2.2 배치 처리 API
- **시작**: `POST /api/convert/batch-start` (Files + Options → Returns `queue_id`)
- **진행률**: `GET /api/convert/batch-progress/{queue_id}`
- **취소**: `DELETE /api/convert/batch-cancel/{queue_id}`

### 2.3 WebSocket (Socket.IO)
- **URL**: `ws://localhost:5000/socket.io/`
- **Events**:
    - `join_queue` (`{queue_id}`): 진행률 수신 시작
    - `batch_progress`: 진행률 데이터 수신 (`progress_percentage`, `eta`)
    - `file_processed`: 개별 파일 완료 알림

---

## 🔄 3. 마이그레이션 가이드 (v1.x → v2.0)

### 3.1 어댑터 사용 (가장 쉬운 방법)
기존 `ImageConverter` 등을 사용하는 코드를 어댑터로 교체하여 호환성을 유지합니다.

```python
# [변경 전]
# from src.core.converter import ImageConverter

# [변경 후]
from src.core.adapters import ImageConverterAdapter as ImageConverter

converter = ImageConverter()
result = converter.convert_to_base64("image.jpg")
```

### 3.2 서비스 레이어 사용 (권장)
새로운 기능(캐싱, Result 패턴 등)을 온전히 활용하려면 서비스 팩토리를 사용하세요.

```python
from src.core.factories.service_factory import ServiceFactory
from src.core.config.app_config import AppConfig

config = AppConfig.from_env()
service = ServiceFactory.create_conversion_service(config)

result = service.convert_image("image.jpg")
if result.success:
    print(result.data)
else:
    print(result.error_message)
```
