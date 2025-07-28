# Image Base64 Converter

이미지 파일을 Base64 형식으로 변환하는 Python 도구입니다. 웹 UI와 명령줄 인터페이스를 모두 제공합니다.

## 주요 기능

- **다양한 이미지 형식 지원**: PNG, JPG, JPEG, GIF, BMP, WEBP
- **양방향 변환**: 이미지 ↔ Base64 상호 변환
- **웹 UI**: 드래그 앤 드롭으로 쉬운 변환
- **명령줄 도구**: 배치 처리 및 자동화 지원
- **원클릭 복사**: Base64 데이터를 클립보드에 바로 복사

## 설치 및 실행

**Windows 사용자 (추천)**
1. `install_dependencies.bat` 더블클릭 - 의존성 자동 설치
2. `run_web.bat` 더블클릭 - 웹 UI 실행
3. 브라우저에서 http://localhost:5000 접속

**수동 설치**
```bash
pip install -r requirements.txt
python run_web.py
```

**필요 환경**: Python 3.6 이상

## 사용법

### 웹 UI (추천)
1. `run_web.bat` 실행 또는 `python run_web.py`
2. 브라우저에서 http://localhost:5000 접속
3. 이미지 파일을 드래그 앤 드롭하여 Base64로 변환
4. Base64 텍스트를 입력하여 이미지로 변환

### 명령줄 도구
```bash
# 단일 파일 변환
python main.py image.png

# 파일로 저장
python main.py image.png -o output.txt

# 디렉토리 배치 처리
python main.py /path/to/images/

# 또는 run_cli.bat 사용 (Windows)
```

## 출력 형식

변환된 결과는 Data URI 형식으로 출력됩니다:
```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

HTML에서 바로 사용 가능:
```html
<img src="data:image/png;base64,..." alt="이미지">
```

## 지원 형식

PNG, JPG, JPEG, GIF, BMP, WEBP

## 프로젝트 구조

```
image-base64-converter/
├── src/                    # 소스 코드
│   ├── converter.py        # 핵심 변환 로직
│   ├── web_app.py         # Flask 웹 애플리케이션
│   ├── cli.py             # 명령줄 인터페이스
│   └── templates/         # HTML 템플릿
├── main.py                # CLI 진입점
├── run_web.py            # 웹 서버 실행
├── install_dependencies.bat  # 의존성 설치 (Windows)
├── run_web.bat           # 웹 UI 실행 (Windows)
└── run_cli.bat           # CLI 실행 (Windows)
```

## 라이선스

MIT License