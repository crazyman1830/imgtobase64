# ⚙️ 운영 매뉴얼 (Operations Manual)

이 문서는 이미지 Base64 변환기의 배포, 설정 및 운영 방법을 다룹니다.

---

## 🚀 1. 배포 (Deployment)

### 1.1 개발 환경 (Development)
빠른 실행 및 테스트를 위한 환경입니다.
1.  **설치**: `pip install -r requirements.txt`
2.  **실행**: `python run_web.py`
    *   기본 포트: 5000
    *   디버그 모드 활성화됨

### 1.2 프로덕션 환경 (Production)
안정성과 성능을 위한 배포 구성입니다.

**요구사항:**
*   Python 3.7+
*   Redis (캐싱 및 세션용, 권장)
*   Nginx (리버스 프록시)

**Gunicorn 실행 (권장):**
```bash
# worker-class eventlet은 WebSocket 지원을 위해 필수입니다.
gunicorn --bind 0.0.0.0:8080 --workers 4 --worker-class eventlet src.web.web_app:app
```

### 1.3 Docker 배포
컨테이너 기반 배포를 권장합니다.
```bash
# 이미지 빌드
docker build -t image-converter .

# 컨테이너 실행 (환경변수 설정 포함)
docker run -d -p 8080:8080 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=your_secure_key \
  image-converter
```

---

## 🔧 2. 설정 (Configuration)

환경 변수 또는 `config.production.json` 파일을 통해 설정합니다.

| 환경 변수 | 설명 | 기본값 |
|-----------|------|--------|
| `ENVIRONMENT` | 실행 환경 (`development` / `production`) | `development` |
| `CACHE_TYPE` | 캐시 백엔드 (`memory`, `redis`, `disk`) | `disk` |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | 보안 키 (세션 암호화 등) | 필수 (프로덕션) |
| `MAX_FILE_SIZE_MB` | 업로드 파일 크기 제한 (MB) | `10` |
| `LOG_LEVEL` | 로깅 레벨 (`debug`, `info`, `warning`) | `info` |

---

## 🛡️ 3. 운영 체크리스트

프로덕션 배포 전 확인 사항:
*   [ ] **보안**: `SECRET_KEY`가 안전하게 설정되었는가?
*   [ ] **SSL**: Nginx 등을 통해 HTTPS가 적용되었는가?
*   [ ] **캐시**: Redis가 구성되어 있는가? (메모리 누수 방지 및 성능 향상)
*   [ ] **제한**: Rate Limiting 및 파일 크기 제한이 올바른가?
