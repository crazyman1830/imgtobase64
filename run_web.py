#!/usr/bin/env python3
"""
웹 UI 실행 스크립트
"""
import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from web_app import app

if __name__ == '__main__':
    print("🚀 이미지 Base64 변환기 웹 UI를 시작합니다...")
    print("📱 브라우저에서 http://localhost:5000 으로 접속하세요")
    print("⏹️  종료하려면 Ctrl+C를 누르세요")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 웹 서버를 종료합니다.")