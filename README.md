# 이미지 Base64 변환기 (Image to Base64 Converter)

웹 UI와 커맨드라인 인터페이스(CLI)를 모두 지원하는 강력하고 유연한 Python 기반 이미지-Base64 양방향 변환 도구입니다.

## 🚀 주요 기능

- **양방향 변환**: 이미지 ↔ Base64 데이터 간 완벽한 변환 지원
- **다양한 포맷**: PNG, JPG, WEBP, GIF, BMP, TIFF, ICO 등 주요 포맷 지원
- **사용자 친화적 UI**: 실시간 미리보기가 가능한 드래그 앤 드롭 웹 인터페이스
- **강력한 CLI**: 자동화 및 배치 처리에 최적화된 명령줄 도구
- **고급 이미지 처리**: 리사이징, 회전, 뒤집기, 포맷 변환 및 압축 기능
- **고성능**: 멀티스레드 기반의 빠른 배치 처리 및 메모리 최적화

## 📦 시작하기 (Windows)

가장 간편한 실행 방법입니다.

1. **`install_dependencies.bat`** 파일을 더블 클릭하여 필요한 패키지를 설치합니다.
2. **웹 UI 실행**: `run_web.bat`을 실행하고 브라우저에서 `http://localhost:5000`에 접속합니다.
3. **CLI 실행**: `run_cli.bat`을 사용하거나 터미널을 엽니다.

## 🛠️ 수동 설치 및 실행

**설치**
```bash
git clone <repository-url>
cd image-base64-converter
pip install -r requirements.txt
```

**웹 애플리케이션 실행**
```bash
python run_web.py
```

**CLI 실행 예시**
```bash
# 단일 이미지 변환
python main.py image.png

# 디렉토리 내 모든 이미지 일괄 변환
python main.py ./images/ -o ./output/
```

## 📚 상세 문서

더 자세한 기술적 내용과 운영 가이드는 `docs/` 디렉토리에서 확인할 수 있습니다.

- **[개발자 매뉴얼 (Developer Manual)](docs/developer_manual.md)**
    - 시스템 아키텍처 및 디자인 패턴
    - API 엔드포인트 및 WebSocket 명세
    - 코드 마이그레이션 가이드 (v1.x → v2.0)
- **[운영 매뉴얼 (Operations Manual)](docs/operations_manual.md)**
    - 배포 가이드 (프로덕션, Docker)
    - 환경 설정 및 운영 체크리스트
- **[변경 로그 (CHANGELOG.md)](CHANGELOG.md)**: 버전별 변경 내역

## 🤝 기여하기

버그 제보나 기능 제안은 언제나 환영합니다. Pull Request를 보내주시기 전에 이슈를 먼저 등록해 주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.