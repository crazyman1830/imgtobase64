"""
Refactored Flask web application using the new service layer architecture.

This module provides a Flask application that integrates with the refactored
service layer, using dependency injection and consistent error handling.
"""
import os
import sys
import time
from pathlib import Path
from flask import Flask, render_template, request
from flask_socketio import SocketIO

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..core.container import DIContainer
from .handlers import WebHandlers
from .middleware import ErrorHandlingMiddleware, SecurityMiddleware


def create_app(config_file: str = None) -> tuple[Flask, SocketIO, DIContainer]:
    """
    Create and configure the Flask application with dependency injection.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Tuple of (Flask app, SocketIO instance, DI container)
    """
    # Initialize dependency injection container
    if config_file:
        container = DIContainer.create_from_config_file(config_file)
    else:
        container = DIContainer.create_default()
    
    # Get configuration
    config = container.get_config()
    
    # Create Flask app
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )
    
    # Configure Flask app
    app.config.update({
        'SECRET_KEY': getattr(config, 'secret_key', 'dev-secret-key'),
        'MAX_CONTENT_LENGTH': getattr(config, 'max_file_size_mb', 16) * 1024 * 1024,
        'JSON_SORT_KEYS': False,
        'JSONIFY_PRETTYPRINT_REGULAR': True
    })
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )
    
    # Initialize handlers with dependency injection
    handlers = WebHandlers(container)
    
    # Initialize middleware
    error_middleware = ErrorHandlingMiddleware(container)
    security_middleware = SecurityMiddleware(container)
    
    # Register middleware
    app.before_request(security_middleware.before_request)
    app.after_request(security_middleware.after_request)
    app.errorhandler(Exception)(error_middleware.handle_error)
    
    # Register routes
    _register_routes(app, handlers)
    
    # Register SocketIO events
    _register_socketio_events(socketio, container)
    
    # Store container in app context for access in routes
    app.container = container
    
    return app, socketio, container


def _register_routes(app: Flask, handlers: WebHandlers) -> None:
    """
    Register all Flask routes with the handlers.
    
    Args:
        app: Flask application instance
        handlers: WebHandlers instance
    """
    
    @app.route('/')
    def index():
        """메인 페이지"""
        return render_template('index.html')
    
    @app.route('/api/convert/to-base64', methods=['POST'])
    def convert_to_base64():
        """이미지를 Base64로 변환"""
        return handlers.convert_to_base64()
    
    @app.route('/api/convert/from-base64', methods=['POST'])
    def convert_from_base64():
        """Base64를 이미지로 변환"""
        return handlers.convert_from_base64()
    
    @app.route('/api/validate-base64', methods=['POST'])
    def validate_base64():
        """Base64 데이터 유효성 검사"""
        return handlers.validate_base64()
    
    @app.route('/api/convert/to-base64-advanced', methods=['POST'])
    def convert_to_base64_advanced():
        """이미지를 고급 처리 옵션과 함께 Base64로 변환"""
        return handlers.convert_to_base64_advanced()
    
    @app.route('/api/formats', methods=['GET'])
    def get_supported_formats():
        """지원되는 이미지 형식 조회"""
        return handlers.get_supported_formats()
    
    @app.route('/api/cache/stats', methods=['GET'])
    def get_cache_stats():
        """캐시 통계 조회"""
        return handlers.get_cache_stats()
    
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_cache():
        """캐시 삭제"""
        return handlers.clear_cache()
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """헬스 체크 엔드포인트"""
        return {
            'status': 'healthy',
            'service': 'image-converter',
            'version': '2.0.0',
            'timestamp': time.time()
        }


def _register_socketio_events(socketio: SocketIO, container: DIContainer) -> None:
    """
    Register SocketIO event handlers.
    
    Args:
        socketio: SocketIO instance
        container: Dependency injection container
    """
    logger = container.get('logger')
    
    @socketio.on('connect')
    def handle_connect():
        """클라이언트 연결 처리"""
        logger.info(f"Client connected: {request.sid}")
        socketio.emit('connected', {
            'message': 'WebSocket 연결이 성공했습니다.',
            'sid': request.sid
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """클라이언트 연결 해제 처리"""
        logger.info(f"Client disconnected: {request.sid}")
    
    @socketio.on('ping')
    def handle_ping(data):
        """핑 요청 처리"""
        socketio.emit('pong', {
            'timestamp': time.time(),
            'data': data
        })


# Create the application instance
app, socketio, container = create_app()


if __name__ == '__main__':
    """Development server entry point."""
    config = container.get_config()
    
    print("🚀 Starting Refactored Image Base64 Converter")
    print(f"📍 Server: http://localhost:5000")
    print(f"🔧 Debug Mode: {config.debug if hasattr(config, 'debug') else True}")
    print(f"💾 Cache: {config.cache_backend if hasattr(config, 'cache_backend') else 'memory'}")
    print("=" * 60)
    
    try:
        socketio.run(
            app,
            debug=True,
            host='0.0.0.0',
            port=5000,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()