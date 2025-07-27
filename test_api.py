#!/usr/bin/env python3
"""
웹 API 테스트 스크립트
"""
import sys
import os
import tempfile
import requests
from PIL import Image

def create_test_image():
    """테스트용 이미지 생성"""
    img = Image.new('RGB', (100, 100), color='blue')
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        img.save(tmp_file.name, 'PNG')
        return tmp_file.name

def test_api():
    """API 테스트"""
    print("🧪 웹 API 테스트 시작...")
    
    # 테스트 이미지 생성
    test_image_path = create_test_image()
    print(f"📁 테스트 이미지 생성: {test_image_path}")
    
    try:
        # API 엔드포인트 테스트
        url = 'http://localhost:5000/api/convert/to-base64'
        
        with open(test_image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        print(f"📡 API 응답 상태: {response.status_code}")
        print(f"📄 API 응답 내용: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 테스트 성공!")
            print(f"   Base64 길이: {len(data.get('base64', ''))} 문자")
            print(f"   이미지 형식: {data.get('format', 'Unknown')}")
            print(f"   이미지 크기: {data.get('size', 'Unknown')}")
        else:
            print(f"❌ API 테스트 실패: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 웹 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
    
    finally:
        # 임시 파일 삭제
        if os.path.exists(test_image_path):
            os.unlink(test_image_path)
            print(f"🗑️  임시 파일 삭제: {test_image_path}")

if __name__ == '__main__':
    test_api()