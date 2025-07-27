"""
웹 기반 UI를 위한 Flask 애플리케이션
"""
import os
import base64
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image
import tempfile

from converter import ImageConverter
from models import ConversionResult, ConversionError

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

converter = ImageConverter()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/convert/to-base64', methods=['POST'])
def convert_to_base64():
    """이미지를 Base64로 변환"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        # 임시 파일로 저장
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
        try:
            file.save(tmp_file.name)
            tmp_file.close()  # 파일을 닫아서 다른 프로세스가 접근할 수 있도록 함
            
            # Base64 변환
            result = converter.convert_to_base64(tmp_file.name)
            
        finally:
            # 임시 파일 삭제
            try:
                os.unlink(tmp_file.name)
            except:
                pass
            
            if not result.success:
                return jsonify({'error': result.error_message}), 400
            
            # 업로드된 파일에서 직접 이미지 정보 추출
            from PIL import Image
            try:
                # 파일 스트림을 직접 사용
                file.stream.seek(0)  # 스트림 시작으로 이동
                image = Image.open(file.stream)
                image_format = image.format
                image_size = image.size
                image.close()
            except Exception as img_error:
                print(f"Image info extraction error: {img_error}")
                # 파일 확장자에서 형식 추정
                ext = os.path.splitext(file.filename)[1].lower()
                format_map = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', 
                             '.gif': 'GIF', '.bmp': 'BMP', '.webp': 'WEBP'}
                image_format = format_map.get(ext, 'Unknown')
                image_size = (0, 0)
            
            return jsonify({
                'base64': result.base64_data,
                'format': image_format,
                'size': image_size,
                'file_size': result.file_size
            })
    
    except Exception as e:
        print(f"To-base64 conversion error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'변환 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/convert/from-base64', methods=['POST'])
def convert_from_base64():
    """Base64를 이미지로 변환"""
    try:
        data = request.get_json()
        if not data or 'base64' not in data:
            return jsonify({'error': 'Base64 데이터가 필요합니다.'}), 400
        
        base64_data = data['base64']
        output_format = data.get('format', 'PNG').upper()
        
        # Base64를 이미지로 변환
        result = converter.base64_to_image(base64_data, output_format=output_format)
        
        if not result.success:
            return jsonify({'error': result.error_message}), 400
        
        # 이미지를 메모리에서 바이트로 변환
        img_io = BytesIO()
        result.image.save(img_io, format=output_format)
        img_io.seek(0)
        
        return send_file(
            img_io,
            mimetype=f'image/{output_format.lower()}',
            as_attachment=True,
            download_name=f'converted.{output_format.lower()}'
        )
    
    except Exception as e:
        return jsonify({'error': f'변환 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/validate-base64', methods=['POST'])
def validate_base64():
    """Base64 데이터 유효성 검사"""
    try:
        data = request.get_json()
        if not data or 'base64' not in data:
            return jsonify({'error': 'Base64 데이터가 필요합니다.'}), 400
        
        base64_data = data['base64']
        is_valid = converter.validate_base64_image(base64_data)
        
        if is_valid:
            # 이미지 정보 추출
            try:
                image_data = base64.b64decode(base64_data.split(',')[1] if ',' in base64_data else base64_data)
                image = Image.open(BytesIO(image_data))
                
                return jsonify({
                    'valid': True,
                    'format': image.format,
                    'size': image.size,
                    'mode': image.mode
                })
            except:
                return jsonify({'valid': True})
        else:
            return jsonify({'valid': False, 'error': '유효하지 않은 Base64 이미지 데이터입니다.'})
    
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)