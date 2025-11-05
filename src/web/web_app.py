"""
웹 기반 UI를 위한 Flask 애플리케이션

Note: 이 파일은 레거시 코드와 새 아키텍처가 혼재되어 있습니다.
향후 완전히 새 아키텍처로 마이그레이션 예정입니다.
"""
import os
import atexit
import signal
import tempfile
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from PIL import Image

# Legacy components (배치 처리에 사용)
from ..core.image_processor import ImageProcessor
from ..core.multi_file_handler import MultiFileHandler
from ..models.processing_options import ProcessingOptions
from .async_handler import AsyncProcessingHandler, WebSocketProgressTracker

# New DI-based architecture (단일 파일 처리에 사용)
from ..core.container import DIContainer
from .handlers import WebHandlers
from .middleware import ErrorHandlingMiddleware, SecurityMiddleware

# Initialize dependency injection container
container = DIContainer.create_default()
config = container.get_config()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['MAX_CONTENT_LENGTH'] = getattr(config, 'max_file_size_mb', 16) * 1024 * 1024
app.config['SECRET_KEY'] = getattr(config, 'secret_key', 'your-secret-key-here')

# Initialize SocketIO with eventlet for async support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize new DI-based components (단일 파일 처리용)
web_handlers = WebHandlers(container)
error_middleware = ErrorHandlingMiddleware(container)
security_middleware = SecurityMiddleware(container)

# Initialize legacy components (배치 처리용 - 향후 마이그레이션 예정)
image_processor = ImageProcessor()
multi_file_handler = MultiFileHandler(max_concurrent=3, max_queue_size=100)

# Initialize async processing handler
async_handler = AsyncProcessingHandler(socketio, multi_file_handler)
progress_tracker = WebSocketProgressTracker(socketio)

# Register middleware
app.before_request(security_middleware.before_request)
app.after_request(security_middleware.after_request)
app.errorhandler(Exception)(error_middleware.handle_error)

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/convert/to-base64', methods=['POST'])
def convert_to_base64():
    """이미지를 Base64로 변환 (리팩토링된 핸들러 사용)"""
    return web_handlers.convert_to_base64()

@app.route('/api/convert/from-base64', methods=['POST'])
def convert_from_base64():
    """Base64를 이미지로 변환 (리팩토링된 핸들러 사용)"""
    return web_handlers.convert_from_base64()

@app.route('/api/validate-base64', methods=['POST'])
def validate_base64():
    """Base64 데이터 유효성 검사 (리팩토링된 핸들러 사용)"""
    return web_handlers.validate_base64()


@app.route('/api/convert/to-base64-advanced', methods=['POST'])
def convert_to_base64_advanced():
    """이미지를 고급 처리 옵션과 함께 Base64로 변환 (리팩토링된 핸들러 사용)"""
    return web_handlers.convert_to_base64_advanced()


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


# New refactored API endpoints
@app.route('/api/formats', methods=['GET'])
def get_supported_formats():
    """지원되는 이미지 형식 조회 (리팩토링된 핸들러 사용)"""
    return web_handlers.get_supported_formats()


@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """캐시 통계 조회 (리팩토링된 핸들러 사용)"""
    return web_handlers.get_cache_stats()


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """캐시 삭제 (리팩토링된 핸들러 사용)"""
    return web_handlers.clear_cache()


@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'service': 'image-converter',
        'version': '2.0.0-refactored',
        'architecture': 'service-layer',
        'timestamp': time.time(),
        'cache_enabled': config.cache_enabled if hasattr(config, 'cache_enabled') else True,
        'security_scan_enabled': getattr(config, 'enable_security_scan', False)
    })


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