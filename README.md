# Image Base64 Converter

이미지 파일을 base64 형식으로 변환하는 Python 도구입니다. 명령줄 인터페이스와 웹 UI 두 가지 방식을 모두 제공하여, 웹 개발이나 데이터 전송 시 이미지를 텍스트 형태로 변환해야 할 때 유용합니다.

## ✨ 주요 특징

### 🖼️ 이미지 처리
- **다양한 이미지 형식 지원**: PNG, JPG, JPEG, GIF, BMP, WEBP
- **양방향 변환**: 이미지 ↔ Base64 상호 변환
- **배치 처리**: 디렉토리 내 모든 이미지 파일 일괄 처리
- **이미지 유효성 검사**: Base64 데이터의 이미지 유효성 실시간 확인

### 🌐 사용자 인터페이스
- **웹 UI**: 직관적인 드래그 앤 드롭 인터페이스
- **명령줄 도구**: 스크립트 자동화 및 배치 처리용
- **반응형 디자인**: 데스크톱과 모바일 모두 지원
- **실시간 미리보기**: 변환 전후 이미지 즉시 확인

### 🔧 편의 기능
- **원클릭 복사**: Base64 데이터를 클립보드에 바로 복사
- **파일 다운로드**: 변환 결과를 다양한 형식으로 저장
- **Data URI 형식**: 웹에서 바로 사용 가능한 형식으로 출력
- **상세한 오류 처리**: 명확한 오류 메시지와 사용자 친화적 피드백

## 📦 설치 방법

이 프로그램은 Python 3.6 이상이 필요합니다.

```bash
# 저장소 클론
git clone <repository-url>
cd image-base64-converter

# 의존성 설치
pip install -r requirements.txt
```

### 의존성
- **Pillow**: 이미지 처리
- **Flask**: 웹 UI 프레임워크
- **Werkzeug**: Flask 의존성

## 🚀 사용법

### 🌐 웹 UI 사용법 (추천)

웹 브라우저에서 직관적인 인터페이스를 통해 이미지를 변환할 수 있습니다:

```bash
# 웹 서버 시작
python run_web.py

# 브라우저에서 http://localhost:5000 접속
```

#### 웹 UI 주요 기능

**🖼️ 이미지 → Base64 변환**
- **드래그 앤 드롭**: 이미지 파일을 드래그해서 쉽게 업로드
- **실시간 미리보기**: 업로드한 이미지 즉시 확인
- **파일 정보 표시**: 파일명, 크기, 형식, 이미지 크기 등
- **원클릭 복사**: 변환된 Base64 데이터를 클립보드에 복사
- **텍스트 파일 저장**: Base64 데이터를 .txt 파일로 다운로드

**🔄 Base64 → 이미지 변환**
- **텍스트 입력**: Base64 데이터를 직접 붙여넣기
- **유효성 검사**: Base64 데이터의 유효성을 실시간으로 확인
- **미리보기**: 변환될 이미지를 미리 확인
- **다양한 출력 형식**: PNG, JPEG, GIF, BMP, WEBP 지원
- **즉시 다운로드**: 변환된 이미지를 바로 다운로드

**🎨 사용자 경험**
- **반응형 디자인**: 데스크톱과 모바일 모두 최적화
- **Bootstrap 5**: 현대적이고 깔끔한 UI
- **토스트 알림**: 성공/오류 메시지를 직관적으로 표시
- **로딩 인디케이터**: 변환 진행 상황 실시간 표시
- **탭 기반 네비게이션**: 기능별로 깔끔하게 분리

### 💻 명령줄 사용법

```bash
# 단일 이미지 파일 변환
python main.py image.png

# 결과를 파일로 저장
python main.py image.png -o output.txt

# 디렉토리 내 모든 이미지 파일 변환
python main.py /path/to/images/

# 배치 변환 결과를 파일로 저장
python main.py /path/to/images/ -o batch_output.txt
```

### 명령줄 옵션

```
usage: image-base64-converter [-h] [-o OUTPUT_PATH] [-f] [-v] [--version] input_path

positional arguments:
  input_path            이미지 파일 또는 이미지가 포함된 디렉토리 경로

options:
  -h, --help            도움말 메시지 표시
  -o OUTPUT_PATH, --output OUTPUT_PATH
                        base64 결과를 저장할 출력 파일 경로
  -f, --force           기존 출력 파일을 확인 없이 덮어쓰기
  -v, --verbose         상세한 정보와 함께 자세한 출력 표시
  --version             프로그램 버전 정보 표시
```

## 사용 예제

### 1. 단일 파일 변환

```bash
$ python main.py sample.png
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

### 2. 상세 정보와 함께 변환

```bash
$ python main.py sample.png -v
Processing file: sample.png
✓ Conversion successful
  File size: 95 bytes
  MIME type: image/png
  Base64 length: 128 characters
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

### 3. 결과를 파일로 저장

```bash
$ python main.py sample.png -o output.txt
$ cat output.txt
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

### 4. 디렉토리 배치 처리

```bash
$ python main.py images/ -v
Scanning directory: images/
Found 3 image file(s)

[1/3] Processing: images/photo1.jpg
  ✓ Success (15,234 bytes → 20,312 chars)

[2/3] Processing: images/logo.png
  ✓ Success (2,456 bytes → 3,275 chars)

[3/3] Processing: images/icon.gif
  ✓ Success (1,024 bytes → 1,365 chars)

Batch processing completed:
  Successful: 3
  Failed: 0
  Total: 3

============================================================
File: images/photo1.jpg
MIME Type: image/jpeg
Size: 15,234 bytes
Base64 Data:
data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...
============================================================
File: images/logo.png
MIME Type: image/png
Size: 2,456 bytes
Base64 Data:
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB...
============================================================
File: images/icon.gif
MIME Type: image/gif
Size: 1,024 bytes
Base64 Data:
data:image/gif;base64,R0lGODlhEAAQAPIAAAAAAP...
```

### 5. 기존 파일 덮어쓰기

```bash
$ python main.py image.png -o existing_file.txt -f
# 확인 없이 기존 파일을 덮어씁니다
```

## 📋 지원되는 이미지 형식

| 형식 | 확장자 | MIME 타입 | 웹 UI | CLI |
|------|--------|-----------|-------|-----|
| PNG | .png | image/png | ✅ | ✅ |
| JPEG | .jpg, .jpeg | image/jpeg | ✅ | ✅ |
| GIF | .gif | image/gif | ✅ | ✅ |
| BMP | .bmp | image/bmp | ✅ | ✅ |
| WebP | .webp | image/webp | ✅ | ✅ |

### 🔧 API 엔드포인트

웹 UI는 다음 REST API를 제공합니다:

| 엔드포인트 | 메서드 | 설명 | 요청 형식 |
|-----------|--------|------|----------|
| `/api/convert/to-base64` | POST | 이미지를 Base64로 변환 | multipart/form-data |
| `/api/convert/from-base64` | POST | Base64를 이미지로 변환 | application/json |
| `/api/validate-base64` | POST | Base64 데이터 유효성 검사 | application/json |

#### API 사용 예제

**이미지 → Base64 변환**
```bash
curl -X POST -F "file=@image.png" http://localhost:5000/api/convert/to-base64
```

**Base64 → 이미지 변환**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"base64":"iVBORw0KGgo...","format":"PNG"}' \
  http://localhost:5000/api/convert/from-base64 \
  --output converted.png
```

**Base64 유효성 검사**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"base64":"iVBORw0KGgo..."}' \
  http://localhost:5000/api/validate-base64
```

## 출력 형식

변환된 결과는 Data URI 형식으로 출력됩니다:

```
data:image/[mime-type];base64,[base64-encoded-data]
```

예시:
```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

이 형식은 HTML, CSS, JavaScript에서 직접 사용할 수 있습니다:

```html
<!-- HTML에서 사용 -->
<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" alt="이미지">
```

```css
/* CSS에서 사용 */
.background {
    background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==');
}
```

## 오류 처리

프로그램은 다양한 오류 상황에 대해 명확한 메시지를 제공합니다:

### 파일을 찾을 수 없는 경우
```bash
$ python main.py nonexistent.png
Error: Input path does not exist: nonexistent.png
```

### 지원되지 않는 파일 형식
```bash
$ python main.py document.txt
Error: Unsupported image format: .txt. Supported formats: .png, .jpg, .jpeg, .gif, .bmp, .webp
```

### 파일 권한 오류
```bash
$ python main.py protected_image.png
Error: Permission denied: Cannot read file protected_image.png
```

### 출력 파일이 이미 존재하는 경우
```bash
$ python main.py image.png -o existing_file.txt
Error: Output file already exists: existing_file.txt
Use -f/--force to overwrite existing files
```

## 제한사항

1. **파일 크기**: 매우 큰 이미지 파일의 경우 메모리 사용량이 높을 수 있습니다
2. **이미지 형식**: 나열된 형식 외의 이미지는 지원되지 않습니다
3. **파일 검증**: 파일 확장자를 기반으로 형식을 판단하므로, 확장자가 잘못된 파일은 오류가 발생할 수 있습니다

## 🧪 개발 및 테스트

### 테스트 실행

```bash
# 전체 테스트 스위트 실행
python run_tests.py

# 개별 테스트 모듈 실행
python -m unittest tests.test_converter
python -m unittest tests.test_file_handler
python -m unittest tests.test_cli
python -m unittest tests.test_integration

# 웹 앱 테스트
python test_web.py    # 컨버터 기능 테스트
python test_api.py    # API 엔드포인트 테스트 (서버 실행 필요)
```

### 📁 프로젝트 구조

```
image-base64-converter/
├── src/                     # 소스 코드
│   ├── __init__.py
│   ├── converter.py         # 핵심 변환 로직 (ImageConverter)
│   ├── file_handler.py      # 파일 I/O 처리
│   ├── cli.py              # 명령줄 인터페이스
│   ├── models.py           # 데이터 모델 및 예외 클래스
│   ├── utils.py            # 유틸리티 함수
│   ├── web_app.py          # Flask 웹 애플리케이션
│   ├── templates/          # HTML 템플릿
│   │   └── index.html      # 메인 웹 UI
│   └── static/             # 정적 파일
│       ├── js/
│       │   └── app.js      # JavaScript 로직
│       └── css/
│           └── custom.css  # 커스텀 스타일
├── tests/                  # 테스트 코드
│   ├── __init__.py
│   ├── test_converter.py   # ImageConverter 테스트
│   ├── test_file_handler.py # FileHandler 테스트
│   ├── test_cli.py         # CLI 테스트
│   ├── test_integration.py # 통합 테스트
│   └── test_data/          # 테스트용 샘플 이미지
├── main.py                 # CLI 프로그램 진입점
├── run_web.py             # 웹 서버 실행 스크립트
├── run_tests.py           # 테스트 실행 스크립트
├── test_web.py            # 웹 앱 기능 테스트
├── test_api.py            # API 테스트 스크립트
├── requirements.txt       # 의존성 목록
├── .gitignore            # Git 제외 파일 목록
└── README.md             # 이 파일
```

### 🏗️ 아키텍처 개요

#### 핵심 컴포넌트

- **ImageConverter** (`src/converter.py`): 이미지 ↔ Base64 변환 핵심 로직
- **FileHandler** (`src/file_handler.py`): 파일 시스템 작업 및 디렉토리 스캔
- **CLI** (`src/cli.py`): 명령줄 인터페이스 및 사용자 상호작용
- **WebApp** (`src/web_app.py`): Flask 기반 웹 애플리케이션
- **Models** (`src/models.py`): 데이터 구조 및 사용자 정의 예외

#### 설계 원칙

- **모듈화**: 각 컴포넌트는 독립적이고 재사용 가능
- **단일 책임**: 각 클래스는 하나의 명확한 책임을 가짐
- **오류 처리**: 계층별 예외 처리로 사용자 친화적 메시지 제공
- **확장성**: 새로운 이미지 형식이나 기능을 쉽게 추가 가능

## 🚀 성능 및 제한사항

### 성능 특징
- **메모리 효율성**: 스트리밍 방식으로 대용량 파일 처리
- **배치 처리**: 여러 파일 동시 처리 시 진행률 표시
- **오류 복구**: 개별 파일 실패 시에도 다른 파일 계속 처리
- **웹 UI 최적화**: 16MB 파일 크기 제한으로 안정성 보장

### 제한사항
- **파일 크기**: 웹 UI에서 최대 16MB 파일 지원
- **동시 접속**: 개발 서버 기준, 프로덕션 환경에서는 WSGI 서버 사용 권장
- **브라우저 호환성**: 모던 브라우저 (Chrome, Firefox, Safari, Edge) 지원

## 🔧 고급 사용법

### 프로덕션 배포

웹 애플리케이션을 프로덕션 환경에 배포할 때는 WSGI 서버를 사용하세요:

```bash
# Gunicorn 설치
pip install gunicorn

# 프로덕션 서버 실행
cd src
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
```

### Docker 사용

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "run_web.py"]
```

### 환경 변수 설정

```bash
# 개발 환경
export FLASK_ENV=development
export FLASK_DEBUG=1

# 프로덕션 환경
export FLASK_ENV=production
export FLASK_DEBUG=0
```

## 🤝 기여하기

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다!

### 기여 가이드라인

1. **이슈 생성**: 버그나 기능 요청은 GitHub Issues에 등록
2. **포크 및 브랜치**: 개발용 브랜치를 생성하여 작업
3. **테스트 실행**: 모든 테스트가 통과하는지 확인
4. **코드 스타일**: Python PEP 8 스타일 가이드 준수
5. **풀 리퀘스트**: 명확한 설명과 함께 PR 생성

### 개발 환경 설정

```bash
# 개발 의존성 설치
pip install -r requirements.txt
pip install pytest black flake8

# 코드 포맷팅
black src/ tests/

# 린팅
flake8 src/ tests/

# 테스트 실행
python run_tests.py
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📈 버전 히스토리

### v2.0.0 (현재)
- ✨ **웹 UI 추가**: 드래그 앤 드롭 인터페이스
- 🔄 **양방향 변환**: Base64 → 이미지 변환 지원
- 🌐 **REST API**: 웹 서비스 API 제공
- 📱 **반응형 디자인**: 모바일 최적화
- ✅ **실시간 유효성 검사**: Base64 데이터 검증

### v1.0.0
- 🖼️ **기본 변환 기능**: 이미지 → Base64
- 💻 **CLI 인터페이스**: 명령줄 도구
- 📁 **배치 처리**: 디렉토리 일괄 처리
- 🛡️ **오류 처리**: 포괄적인 예외 처리
- 🎨 **다중 형식**: PNG, JPG, JPEG, GIF, BMP, WEBP 지원

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 라이브러리들을 사용합니다:
- **Pillow**: 이미지 처리
- **Flask**: 웹 프레임워크
- **Bootstrap**: UI 프레임워크
- **Font Awesome**: 아이콘