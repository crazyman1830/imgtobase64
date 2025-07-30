# 이미지 Base64 변환기 문서

이 디렉토리는 이미지 Base64 변환기 프로젝트의 모든 문서를 포함합니다.

## 📋 문서 목록

### 🏗️ 아키텍처 및 설계
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - v2.0 리팩토링된 아키텍처 상세 설명
  - 레이어드 아키텍처 구조
  - 핵심 디자인 패턴 (의존성 주입, Result 패턴, 팩토리 패턴)
  - 데이터 흐름 및 성능 최적화 전략

### 🔄 마이그레이션 및 변경사항
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - v1.x에서 v2.0으로 마이그레이션 가이드
  - 점진적 마이그레이션 전략
  - 레거시 어댑터 사용법
  - 단계별 체크리스트
- **[CHANGELOG.md](CHANGELOG.md)** - 버전별 변경사항 및 개선사항
  - v2.0 대규모 리팩토링 내용
  - 성능 개선사항 및 벤치마크 결과
  - 새로운 기능 및 호환성 정보

### 🚀 배포 및 운영
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 배포 가이드
  - 개발/프로덕션 환경 배포 방법
  - Docker 및 클라우드 배포
  - 모니터링 및 보안 고려사항

### 🔌 API 및 인터페이스
- **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - REST API 및 WebSocket 엔드포인트
  - 모든 API 엔드포인트 상세 설명
  - WebSocket 이벤트 및 실시간 통신
  - 요청/응답 예제 및 에러 처리

### 🧪 테스트 및 품질 보증
- **[TESTING_SUMMARY.md](TESTING_SUMMARY.md)** - 통합 테스트 및 성능 벤치마크 결과
  - 기능 검증 테스트 결과
  - 성능 벤치마크 및 최적화 효과
  - 테스트 인프라 및 도구

## 📖 문서 읽기 순서

### 새로운 개발자를 위한 권장 순서
1. **[../README.md](../README.md)** - 프로젝트 개요 및 빠른 시작
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - 시스템 아키텍처 이해
3. **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - API 사용법 학습
4. **[DEPLOYMENT.md](DEPLOYMENT.md)** - 개발 환경 설정

### 기존 v1.x 사용자를 위한 권장 순서
1. **[CHANGELOG.md](CHANGELOG.md)** - v2.0 변경사항 확인
2. **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - 마이그레이션 계획 수립
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - 새로운 아키텍처 이해
4. **[TESTING_SUMMARY.md](TESTING_SUMMARY.md)** - 성능 개선 효과 확인

### 운영 담당자를 위한 권장 순서
1. **[DEPLOYMENT.md](DEPLOYMENT.md)** - 배포 및 운영 가이드
2. **[TESTING_SUMMARY.md](TESTING_SUMMARY.md)** - 성능 특성 이해
3. **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - 모니터링 엔드포인트 확인

## 🔍 문서 검색 가이드

### 주제별 빠른 찾기

#### 성능 관련
- **캐싱**: [ARCHITECTURE.md](ARCHITECTURE.md#성능-최적화) → [TESTING_SUMMARY.md](TESTING_SUMMARY.md#달성된-성능-개선사항)
- **메모리 최적화**: [ARCHITECTURE.md](ARCHITECTURE.md#메모리-최적화) → [CHANGELOG.md](CHANGELOG.md#성능-최적화)
- **벤치마크**: [TESTING_SUMMARY.md](TESTING_SUMMARY.md#성능-벤치마크-테스트)

#### 개발 관련
- **의존성 주입**: [ARCHITECTURE.md](ARCHITECTURE.md#핵심-디자인-패턴) → [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md#의존성-주입-패턴-사용)
- **에러 처리**: [ARCHITECTURE.md](ARCHITECTURE.md#에러-처리-전략) → [API_ENDPOINTS.md](API_ENDPOINTS.md#에러-응답-형식)
- **테스트**: [TESTING_SUMMARY.md](TESTING_SUMMARY.md) → [ARCHITECTURE.md](ARCHITECTURE.md#테스트-전략)

#### 배포 관련
- **Docker**: [DEPLOYMENT.md](DEPLOYMENT.md#docker-배포)
- **프로덕션**: [DEPLOYMENT.md](DEPLOYMENT.md#프로덕션-배포)
- **모니터링**: [DEPLOYMENT.md](DEPLOYMENT.md#모니터링-및-로깅)

## 📝 문서 기여 가이드

### 문서 작성 규칙
- 모든 문서는 한국어로 작성
- 마크다운 형식 사용
- 코드 예제는 실행 가능한 형태로 제공
- 스크린샷이나 다이어그램은 `docs/images/` 폴더에 저장

### 문서 업데이트 절차
1. 기능 변경 시 관련 문서 동시 업데이트
2. 새로운 API 추가 시 `API_ENDPOINTS.md` 업데이트
3. 아키텍처 변경 시 `ARCHITECTURE.md` 업데이트
4. 버전 릴리즈 시 `CHANGELOG.md` 업데이트

### 문서 리뷰 체크리스트
- [ ] 한국어 맞춤법 및 문법 확인
- [ ] 코드 예제 실행 가능성 확인
- [ ] 링크 유효성 확인
- [ ] 목차 및 인덱스 업데이트

## 🔗 외부 리소스

### 관련 기술 문서
- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [Pillow 문서](https://pillow.readthedocs.io/)
- [Socket.IO 문서](https://socket.io/docs/)

### 아키텍처 패턴 참고자료
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Dependency Injection](https://martinfowler.com/articles/injection.html)
- [Result Pattern](https://www.enterpriseintegrationpatterns.com/patterns/messaging/ReturnAddress.html)

---

이 문서 모음은 이미지 Base64 변환기 프로젝트의 모든 측면을 다루며, 개발자, 운영자, 사용자 모두에게 필요한 정보를 제공합니다.