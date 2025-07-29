"""
웹 기반 UI를 위한 Flask 애플리케이션
"""
import os
import base64
import uuid
import asyncio
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from io import BytesIO
from PIL import Image
import tempfile
from typing import List, Dict, Any, Optional

from ..core.converter import ImageConverter
from ..core.image_processor import ImageProcessor
from ..core.multi_file_handler import MultiFileHandler
from ..models.models import ConversionResult, ConversionError
from ..models.processing_options import ProcessingOptions, ProgressInfo
from .async_handler import AsyncProcessingHandler, WebSocketProgressTracker

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production

# Initialize SocketIO with eventlet for async support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize components
converter = ImageConverter()
image_processor = ImageProcessor()
multi_file_handler = MultiFileHandler(max_concurrent=3, max_queue_size=100)

# Initialize async processing handler
async_handler = AsyncProcessingHandler(socketio, multi_file_handler)
progress_tracker = WebSocketProgressTracker(socketio)

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


@app.route('/api/convert/to-base64-advanced', methods=['POST'])
def convert_to_base64_advanced():
    """이미지를 고급 처리 옵션과 함께 Base64로 변환"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        # 처리 옵션 파싱
        options_data = {}
        if request.form.get('options'):
            import json
            try:
                options_data = json.loads(request.form.get('options'))
            except json.JSONDecodeError:
                return jsonify({'error': '잘못된 옵션 형식입니다.'}), 400
        
        # ProcessingOptions 객체 생성
        try:
            processing_options = ProcessingOptions(
                resize_width=options_data.get('resize_width'),
                resize_height=options_data.get('resize_height'),
                maintain_aspect_ratio=options_data.get('maintain_aspect_ratio', True),
                quality=options_data.get('quality', 85),
                target_format=options_data.get('target_format'),
                rotation_angle=options_data.get('rotation_angle', 0),
                flip_horizontal=options_data.get('flip_horizontal', False),
                flip_vertical=options_data.get('flip_vertical', False)
            )
        except ValueError as e:
            return jsonify({'error': f'잘못된 처리 옵션: {str(e)}'}), 400
        
        # 임시 파일로 저장
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
        try:
            file.save(tmp_file.name)
            tmp_file.close()
            
            # 고급 이미지 처리 수행
            result = _process_image_with_options(tmp_file.name, processing_options)
            
        finally:
            # 임시 파일 삭제
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        
        if not result.success:
            return jsonify({'error': result.error_message}), 400
        
        # 원본 이미지 정보 추출
        try:
            file.stream.seek(0)
            original_image = Image.open(file.stream)
            original_format = original_image.format
            original_size = original_image.size
            original_image.close()
        except Exception:
            original_format = 'Unknown'
            original_size = (0, 0)
        
        return jsonify({
            'base64': result.base64_data,
            'original_format': original_format,
            'original_size': original_size,
            'processed_format': result.format,
            'processed_size': result.size,
            'file_size': result.file_size,
            'processing_options': {
                'resize_width': processing_options.resize_width,
                'resize_height': processing_options.resize_height,
                'maintain_aspect_ratio': processing_options.maintain_aspect_ratio,
                'quality': processing_options.quality,
                'target_format': processing_options.target_format,
                'rotation_angle': processing_options.rotation_angle,
                'flip_horizontal': processing_options.flip_horizontal,
                'flip_vertical': processing_options.flip_vertical
            }
        })
    
    except Exception as e:
        print(f"Advanced conversion error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'변환 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/convert/batch-start', methods=['POST'])
def batch_start():
    """다중 파일 배치 처리 시작"""
    try:
        # 파일 목록 확인
        if 'files' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        # 처리 옵션 파싱
        options_data = {}
        if request.form.get('options'):
            import json
            try:
                options_data = json.loads(request.form.get('options'))
            except json.JSONDecodeError:
                return jsonify({'error': '잘못된 옵션 형식입니다.'}), 400
        
        # ProcessingOptions 객체 생성
        try:
            processing_options = ProcessingOptions(
                resize_width=options_data.get('resize_width'),
                resize_height=options_data.get('resize_height'),
                maintain_aspect_ratio=options_data.get('maintain_aspect_ratio', True),
                quality=options_data.get('quality', 85),
                target_format=options_data.get('target_format'),
                rotation_angle=options_data.get('rotation_angle', 0),
                flip_horizontal=options_data.get('flip_horizontal', False),
                flip_vertical=options_data.get('flip_vertical', False)
            )
        except ValueError as e:
            return jsonify({'error': f'잘못된 처리 옵션: {str(e)}'}), 400
        
        # 임시 파일들 저장
        temp_files = []
        try:
            for file in files:
                if file.filename != '':
                    tmp_file = tempfile.NamedTemporaryFile(
                        delete=False, 
                        suffix=os.path.splitext(file.filename)[1]
                    )
                    file.save(tmp_file.name)
                    tmp_file.close()
                    temp_files.append(tmp_file.name)
            
            if not temp_files:
                return jsonify({'error': '유효한 파일이 없습니다.'}), 400
            
            # 큐에 추가 (진행률 콜백은 async_handler에서 처리)
            queue_id = multi_file_handler.add_to_queue(
                files=temp_files,
                options=processing_options,
                priority=0
            )
            
            # 진행률 추적 시작
            progress_tracker.start_tracking(queue_id)
            
            # 백그라운드에서 비동기 처리 시작
            success = async_handler.start_batch_processing(
                queue_id=queue_id,
                temp_files=temp_files,
                processing_options=processing_options,
                processor_func=_process_image_with_options
            )
            
            if not success:
                return jsonify({'error': '배치 처리 시작에 실패했습니다.'}), 500
            
            return jsonify({
                'queue_id': queue_id,
                'total_files': len(temp_files),
                'status': 'started',
                'message': f'{len(temp_files)}개 파일의 배치 처리가 시작되었습니다.'
            })
        
        except Exception as e:
            # 오류 발생 시 임시 파일들 정리
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            raise e
    
    except Exception as e:
        print(f"Batch start error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'배치 처리 시작 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/convert/batch-progress/<queue_id>', methods=['GET'])
def batch_progress(queue_id: str):
    """배치 처리 진행률 확인"""
    try:
        progress_info = multi_file_handler.get_progress(queue_id)
        
        if progress_info is None:
            return jsonify({'error': '큐를 찾을 수 없습니다.'}), 404
        
        # 처리 결과 정보 추가
        processing_summary = multi_file_handler.get_processing_summary(queue_id)
        failed_files = multi_file_handler.get_failed_files(queue_id)
        
        response_data = {
            'queue_id': progress_info.queue_id,
            'total_files': progress_info.total_files,
            'completed_files': progress_info.completed_files,
            'current_file': progress_info.current_file,
            'estimated_time_remaining': progress_info.estimated_time_remaining,
            'status': progress_info.status,
            'error_count': progress_info.error_count,
            'start_time': progress_info.start_time,
            'current_file_progress': progress_info.current_file_progress,
            'progress_percentage': progress_info.progress_percentage,
            'success_rate': progress_info.success_rate
        }
        
        # 완료된 경우 결과 정보 추가
        if progress_info.status in ['completed', 'cancelled', 'error']:
            if processing_summary:
                response_data.update({
                    'successful_files': processing_summary['successful_files'],
                    'failed_files': processing_summary['failed_files'],
                    'average_processing_time': processing_summary['average_processing_time'],
                    'total_processing_time': processing_summary['total_processing_time']
                })
            
            # 실패한 파일 정보 추가
            if failed_files:
                response_data['failed_file_details'] = [
                    {
                        'file_path': f['file_path'],
                        'error': f['error']
                    }
                    for f in failed_files
                ]
            
            # 성공한 파일들의 결과 추가 (Base64 데이터는 제외하고 메타데이터만)
            results = multi_file_handler.get_processing_results(queue_id)
            successful_results = []
            for result in results:
                if result.success:
                    successful_results.append({
                        'file_path': result.file_path,
                        'format': result.format,
                        'size': result.size,
                        'file_size': result.file_size,
                        'processing_time': getattr(result, 'processing_time', 0.0)
                    })
            response_data['successful_results'] = successful_results
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Batch progress error: {str(e)}")
        return jsonify({'error': f'진행률 확인 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/convert/batch-cancel/<queue_id>', methods=['DELETE'])
def batch_cancel(queue_id: str):
    """배치 처리 취소"""
    try:
        success = async_handler.cancel_batch_processing(queue_id)
        
        if not success:
            return jsonify({'error': '큐를 찾을 수 없습니다.'}), 404
        
        # 진행률 추적 중지
        progress_tracker.stop_tracking(queue_id)
        
        return jsonify({
            'queue_id': queue_id,
            'status': 'cancelled',
            'message': '배치 처리가 취소되었습니다.'
        })
    
    except Exception as e:
        print(f"Batch cancel error: {str(e)}")
        return jsonify({'error': f'배치 처리 취소 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/convert/batch-status', methods=['GET'])
def batch_status():
    """전체 배치 처리 상태 확인"""
    try:
        # 활성 작업 정보
        active_tasks = async_handler.get_active_tasks()
        
        # 전체 큐 정보
        all_queues = multi_file_handler.get_all_queues()
        
        # 통계 정보
        statistics = multi_file_handler.get_statistics()
        
        return jsonify({
            'active_tasks': active_tasks,
            'all_queues': all_queues,
            'statistics': statistics,
            'timestamp': time.time()
        })
    
    except Exception as e:
        print(f"Batch status error: {str(e)}")
        return jsonify({'error': f'배치 상태 확인 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/convert/batch-cleanup', methods=['POST'])
def batch_cleanup():
    """완료된 배치 작업 정리"""
    try:
        # 완료된 작업 정리
        cleaned_tasks = async_handler.cleanup_completed_tasks()
        
        # 오래된 큐 정리
        max_age_hours = request.json.get('max_age_hours', 24.0) if request.json else 24.0
        cleaned_queues = multi_file_handler.cleanup_completed_queues(max_age_hours)
        
        # 오래된 진행률 추적 정리
        cleaned_tracking = progress_tracker.cleanup_stale_tracking(max_age_hours * 3600)
        
        return jsonify({
            'cleaned_tasks': cleaned_tasks,
            'cleaned_queues': cleaned_queues,
            'cleaned_tracking': cleaned_tracking,
            'message': f'{cleaned_tasks}개 작업, {cleaned_queues}개 큐, {cleaned_tracking}개 추적이 정리되었습니다.'
        })
    
    except Exception as e:
        print(f"Batch cleanup error: {str(e)}")
        return jsonify({'error': f'배치 정리 중 오류가 발생했습니다: {str(e)}'}), 500


# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """클라이언트 연결 처리"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'WebSocket 연결이 성공했습니다.'})


@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제 처리"""
    print(f"Client disconnected: {request.sid}")


@socketio.on('join_queue')
def handle_join_queue(data):
    """큐 룸에 참가"""
    queue_id = data.get('queue_id')
    if queue_id:
        join_room(f'queue_{queue_id}')
        emit('joined_queue', {'queue_id': queue_id, 'message': f'큐 {queue_id}에 참가했습니다.'})


@socketio.on('leave_queue')
def handle_leave_queue(data):
    """큐 룸에서 나가기"""
    queue_id = data.get('queue_id')
    if queue_id:
        leave_room(f'queue_{queue_id}')
        emit('left_queue', {'queue_id': queue_id, 'message': f'큐 {queue_id}에서 나갔습니다.'})


@socketio.on('request_progress')
def handle_request_progress(data):
    """진행률 요청 처리"""
    queue_id = data.get('queue_id')
    if queue_id:
        progress_info = multi_file_handler.get_progress(queue_id)
        if progress_info:
            emit('batch_progress', {
                'queue_id': progress_info.queue_id,
                'total_files': progress_info.total_files,
                'completed_files': progress_info.completed_files,
                'current_file': progress_info.current_file,
                'estimated_time_remaining': progress_info.estimated_time_remaining,
                'status': progress_info.status,
                'error_count': progress_info.error_count,
                'progress_percentage': progress_info.progress_percentage,
                'current_file_progress': progress_info.current_file_progress,
                'timestamp': time.time()
            })
        else:
            emit('error', {'message': f'큐 {queue_id}를 찾을 수 없습니다.'})


@socketio.on('cancel_batch')
def handle_cancel_batch(data):
    """WebSocket을 통한 배치 처리 취소"""
    queue_id = data.get('queue_id')
    if queue_id:
        success = async_handler.cancel_batch_processing(queue_id)
        if success:
            emit('batch_cancelled', {
                'queue_id': queue_id,
                'message': '배치 처리가 취소되었습니다.',
                'timestamp': time.time()
            })
        else:
            emit('error', {'message': f'큐 {queue_id}를 찾을 수 없거나 취소할 수 없습니다.'})


@socketio.on('get_queue_status')
def handle_get_queue_status(data):
    """큐 상태 정보 요청"""
    queue_id = data.get('queue_id')
    if queue_id:
        queue_info = multi_file_handler.get_queue_info(queue_id)
        task_status = async_handler.get_task_status(queue_id)
        
        if queue_info:
            emit('queue_status', {
                'queue_info': queue_info,
                'task_status': task_status,
                'timestamp': time.time()
            })
        else:
            emit('error', {'message': f'큐 {queue_id}를 찾을 수 없습니다.'})


@socketio.on('get_active_queues')
def handle_get_active_queues():
    """활성 큐 목록 요청"""
    active_tasks = async_handler.get_active_tasks()
    all_queues = multi_file_handler.get_all_queues()
    
    emit('active_queues', {
        'active_tasks': active_tasks,
        'all_queues': all_queues,
        'timestamp': time.time()
    })



def _process_image_with_options(file_path: str, options: ProcessingOptions) -> ConversionResult:
    """
    처리 옵션을 적용하여 이미지를 처리하고 Base64로 변환
    
    Args:
        file_path: 처리할 이미지 파일 경로
        options: 처리 옵션
        
    Returns:
        ConversionResult 객체
    """
    try:
        # 이미지 로드
        with Image.open(file_path) as image:
            # 이미지 복사 (원본 보존)
            processed_image = image.copy()
            
            # 회전 적용
            if options.rotation_angle != 0:
                processed_image = image_processor.rotate_image(processed_image, options.rotation_angle)
            
            # 뒤집기 적용
            if options.flip_horizontal:
                processed_image = image_processor.flip_image(processed_image, 'horizontal')
            
            if options.flip_vertical:
                processed_image = image_processor.flip_image(processed_image, 'vertical')
            
            # 리사이징 적용
            if options.resize_width or options.resize_height:
                processed_image = image_processor.resize_image(
                    processed_image,
                    width=options.resize_width,
                    height=options.resize_height,
                    maintain_aspect=options.maintain_aspect_ratio
                )
            
            # 포맷 변환 적용
            target_format = options.target_format or processed_image.format or 'PNG'
            if target_format != processed_image.format:
                processed_image = image_processor.convert_format(processed_image, target_format)
            
            # 압축 적용
            processed_image = image_processor.compress_image(
                processed_image,
                quality=options.quality,
                format=target_format
            )
            
            # Base64로 변환
            img_buffer = BytesIO()
            save_kwargs = {}
            
            if target_format == 'JPEG':
                save_kwargs['quality'] = options.quality
                save_kwargs['optimize'] = True
            elif target_format == 'PNG':
                save_kwargs['optimize'] = True
            elif target_format == 'WEBP':
                save_kwargs['quality'] = options.quality
                save_kwargs['method'] = 6
            
            processed_image.save(img_buffer, format=target_format, **save_kwargs)
            img_buffer.seek(0)
            
            # Base64 인코딩
            base64_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # 결과 생성
            result = ConversionResult(
                file_path=file_path,
                success=True,
                base64_data=base64_data,
                format=target_format,
                size=processed_image.size,
                file_size=len(img_buffer.getvalue())
            )
            
            return result
    
    except Exception as e:
        return ConversionResult(
            file_path=file_path,
            success=False,
            error_message=str(e)
        )


# Graceful shutdown handler
import atexit
import signal

def cleanup_on_exit():
    """애플리케이션 종료 시 정리 작업"""
    print("Shutting down gracefully...")
    try:
        # 비동기 핸들러 종료
        async_handler.shutdown()
        
        # 진행률 추적 정리
        progress_tracker.cleanup_stale_tracking(0)  # 모든 추적 정리
        
        print("Cleanup completed.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# 종료 시 정리 함수 등록
atexit.register(cleanup_on_exit)

# 시그널 핸들러 등록
def signal_handler(signum, frame):
    print(f"Received signal {signum}")
    cleanup_on_exit()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    try:
        print("Starting Flask-SocketIO server with WebSocket support...")
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("Server interrupted by user")
    finally:
        cleanup_on_exit()