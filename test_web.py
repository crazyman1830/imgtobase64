#!/usr/bin/env python3
"""
웹 앱 테스트 스크립트
"""
import sys
import os
import tempfile
from PIL import Image

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from converter import ImageConverter

def create_test_image():
    """테스트용 이미지 생성"""
    # 간단한 빨간색 사각형 이미지 생성
    img = Image.new('RGB', (100, 100), color='red')
    
    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        img.save(tmp_file.name, 'PNG')
        return tmp_file.name

def test_converter():
    """컨버터 테스트"""
    print("🧪 ImageConverter 테스트 시작...")
    
    # 테스트 이미지 생성
    test_image_path = create_test_image()
    print(f"📁 테스트 이미지 생성: {test_image_path}")
    
    try:
        # 컨버터 인스턴스 생성
        converter = ImageConverter()
        
        # Base64 변환 테스트
        result = converter.convert_to_base64(test_image_path)
        
        if result.success:
            print("✅ Base64 변환 성공!")
            print(f"   파일 크기: {result.file_size} bytes")
            print(f"   MIME 타입: {result.mime_type}")
            print(f"   Base64 길이: {len(result.base64_data)} 문자")
            
            # Base64 유효성 검사 테스트
            is_valid = converter.validate_base64_image(result.base64_data)
            print(f"   Base64 유효성: {'✅ 유효' if is_valid else '❌ 무효'}")
            
            # Base64를 이미지로 변환 테스트
            img_result = converter.base64_to_image(result.base64_data, 'PNG')
            if img_result.success:
                print("✅ Base64 → 이미지 변환 성공!")
                print(f"   이미지 크기: {img_result.size}")
                print(f"   이미지 형식: {img_result.format}")
            else:
                print(f"❌ Base64 → 이미지 변환 실패: {img_result.error_message}")
        else:
            print(f"❌ Base64 변환 실패: {result.error_message}")
    
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 임시 파일 삭제
        if os.path.exists(test_image_path):
            os.unlink(test_image_path)
            print(f"🗑️  임시 파일 삭제: {test_image_path}")

if __name__ == '__main__':
    test_converter()