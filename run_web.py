#!/usr/bin/env python3
"""
웹 애플리케이션 실행 스크립트
Enhanced with configuration management and production-ready features.
"""
import os
import sys
import argparse
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import get_config_manager, get_config


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Image Base64 Converter Web Server')
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (JSON or YAML)'
    )
    parser.add_argument(
        '--host',
        type=str,
        help='Host to bind to (overrides config)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        help='Port to bind to (overrides config)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (overrides config)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Run in production mode with optimized settings'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of worker processes (for production)'
    )
    return parser.parse_args()


def setup_logging(config):
    """Setup application logging."""
    import logging
    import logging.handlers
    from pathlib import Path
    
    # Create log directory
    log_dir = Path(config.logging.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format
    )
    
    if config.logging.enable_file_logging:
        # Add file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'app.log',
            maxBytes=config.logging.max_file_size_mb * 1024 * 1024,
            backupCount=config.logging.backup_count
        )
        file_handler.setFormatter(logging.Formatter(config.logging.format))
        logging.getLogger().addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('eventlet').setLevel(logging.WARNING)


def run_development_server(app, socketio, config, args):
    """Run development server with Flask's built-in server."""
    host = args.host or config.web.host
    port = args.port or config.web.port
    debug = args.debug or config.web.debug
    
    print(f"🚀 Starting Image Base64 Converter Development Server")
    print(f"📍 Server: http://{host}:{port}")
    print(f"🔧 Debug Mode: {'Enabled' if debug else 'Disabled'}")
    print(f"🌍 Environment: {config.environment}")
    print(f"💾 Cache: {config.cache.backend} ({config.cache.max_size_mb}MB)")
    print(f"🔒 Security Scan: {'Enabled' if config.security.enable_content_scan else 'Disabled'}")
    print(f"⚡ Memory Optimization: {'Enabled' if config.processing.enable_memory_optimization else 'Disabled'}")
    print("=" * 60)
    
    try:
        socketio.run(
            app,
            debug=debug,
            host=host,
            port=port,
            use_reloader=debug,
            log_output=debug
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_production_server(app, config, args):
    """Run production server with Gunicorn."""
    try:
        import gunicorn.app.wsgiapp as wsgi
    except ImportError:
        print("❌ Gunicorn not installed. Install with: pip install gunicorn")
        print("🔄 Falling back to development server...")
        from src.web.web_app import socketio
        return run_development_server(app, socketio, config, args)
    
    host = args.host or config.web.host
    port = args.port or config.web.port
    workers = args.workers
    
    print(f"🚀 Starting Image Base64 Converter Production Server")
    print(f"📍 Server: http://{host}:{port}")
    print(f"👥 Workers: {workers}")
    print(f"🌍 Environment: {config.environment}")
    print("=" * 60)
    
    # Gunicorn configuration
    gunicorn_config = {
        'bind': f'{host}:{port}',
        'workers': workers,
        'worker_class': 'eventlet',
        'worker_connections': 1000,
        'timeout': 120,
        'keepalive': 2,
        'max_requests': 1000,
        'max_requests_jitter': 100,
        'preload_app': True,
        'access_log_format': '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
        'accesslog': str(Path(config.logging.log_dir) / 'access.log') if config.logging.enable_file_logging else '-',
        'errorlog': str(Path(config.logging.log_dir) / 'error.log') if config.logging.enable_file_logging else '-',
        'loglevel': config.logging.level.lower(),
    }
    
    # Set Gunicorn configuration
    sys.argv = ['gunicorn'] + [f'--{k}={v}' for k, v in gunicorn_config.items()] + ['src.web.web_app:app']
    
    try:
        wsgi.run()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Production server error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Initialize configuration
    config_manager = get_config_manager(args.config)
    config = config_manager.load_config()
    
    # Override config with command line arguments
    if args.production:
        config.environment = 'production'
        config.web.debug = False
    
    # Setup logging
    setup_logging(config)
    
    # Import and create Flask app with config
    from src.web.web_app import app, socketio
    
    # Apply configuration to Flask app
    app.config['SECRET_KEY'] = config.web.secret_key
    app.config['MAX_CONTENT_LENGTH'] = config.web.max_content_length_bytes
    
    # Run server
    if config.is_production() or args.production:
        run_production_server(app, config, args)
    else:
        run_development_server(app, socketio, config, args)


if __name__ == '__main__':
    main()