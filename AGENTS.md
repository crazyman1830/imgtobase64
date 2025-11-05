# Image Base64 Converter - AI Agent Guide

Python-based image conversion tool with dependency injection architecture, web UI, CLI, and batch processing capabilities.

**Version**: 2.0.0 | **Language**: Python | **Architecture**: Layered DI Container

## Quick Start

- **CLI**: `python main.py image.png` or `python main.py image.png -o output.txt`
- **Web**: `python run_web.py` then visit http://localhost:5000
- **Test**: `python -m pytest tests/` or `python tests/integration/run_functionality_tests.py`
- **Dependencies**: `pip install -r requirements.txt`

## Core Features
- Image ↔ Base64 conversion with advanced processing options
- Batch processing with real-time WebSocket progress tracking  
- Web UI + CLI interfaces with unified service layer
- Intelligent caching, security validation, memory optimization

## Architecture Overview

**Layered DI Architecture**: Presentation → Application → Domain → Infrastructure

**Key Patterns**: 
- **Dependency Injection**: All services injected via interfaces for testability
- **Result Pattern**: Explicit success/failure returns instead of exceptions  
- **Factory Pattern**: Configuration-based object creation
- **Adapter Pattern**: Legacy compatibility during migration

**Service Flow**: `CLI/Web → DIContainer → Services → Interfaces → Implementation`

## Project Structure

```
├── main.py                       # CLI entry point
├── run_web.py                    # Web server launcher  
├── config.json                   # Dev config
├── config.production.json        # Production config
├── requirements.txt              # Dependencies
├── src/
│   ├── cli.py                    # CLI interface
│   ├── core/
│   │   ├── container.py          # DI container (main orchestrator)
│   │   ├── services/             # Business logic services
│   │   ├── interfaces/           # Service contracts
│   │   ├── config/               # Configuration management
│   │   └── error_handler.py      # Centralized error handling
│   ├── web/web_app.py           # Flask application
│   ├── models/                   # Data models (ConversionResult, ProcessingOptions)
│   └── domain/exceptions/        # Domain-specific exceptions
├── tests/
│   ├── integration/              # End-to-end tests
│   └── unit/                     # Component tests
└── docs/                         # API docs, architecture guides
```

## Key Files to Know

- **`src/core/container.py`**: Central DI container - start here for service discovery
- **`src/core/services/image_conversion_service.py`**: Main business logic
- **`src/web/web_app.py`**: Flask app with REST + WebSocket endpoints
- **`src/cli.py`**: Command-line interface implementation
- **`config.json`**: All application settings (cache, security, performance)

## Development Tips

- Use `container = DIContainer.create_default()` to get all services - this is your main entry point
- Get services with `container.get('service_name')` - available services: `image_conversion_service`, `file_handler_service`, `cache_manager_service`, `logger`, `error_handler`
- For testing, use `DIContainer.create_for_testing()` to get a test-optimized container
- Check `config.json` for all settings - modify cache size, security options, performance tuning here
- All services return `Result` objects - check `result.success` before accessing `result.data`

## API Endpoints

**REST API**:
- `POST /api/convert/to-base64` - Basic conversion
- `POST /api/convert/to-base64-advanced` - With processing options  
- `POST /api/convert/batch-start` - Start batch processing
- `GET /api/convert/batch-progress/{queue_id}` - Check progress
- `GET /api/cache/stats` - Cache statistics
- `GET /api/health` - Health check

**WebSocket Events**:
- `batch_progress` - Real-time progress updates
- `file_processed` - Individual file completion
- `batch_completed` - Batch completion notification

## CLI Usage

```bash
python main.py image.png                    # Convert single image
python main.py image.png -o output.txt      # Save to file
python main.py /path/to/images/ -v          # Batch convert with verbose
python main.py image.png -o output.txt -f   # Force overwrite
```

## Adding New Features

1. **Define Interface**: Add to `src/core/interfaces/` 
2. **Implement Service**: Create in `src/core/services/`
3. **Register in DI**: Update `container.py` to wire up the service
4. **Add Tests**: Write unit tests in `tests/unit/` and integration tests in `tests/integration/`

## Code Patterns

**Result Pattern** (no exceptions):
```python
from src.core.base.result import Result

def convert_image(file_path: str) -> Result[str]:
    try:
        # do work
        return Result.success(base64_data)
    except Exception as e:
        return Result.failure(str(e))
```

**Service Access**:
```python
container = DIContainer.create_default()
service = container.get('image_conversion_service')
result = service.convert_image("image.jpg")
if result.success:
    print(result.data)
```

**Logging**:
```python
logger = container.get('logger')
logger.info("Converting image", extra={"file": file_path, "size": file_size})
```

**Configuration**:
```python
config = container.get('config')
max_size = config.security.max_file_size_mb
cache_enabled = config.cache.enabled
```

## Testing Instructions

- **Run All Tests**: `python -m pytest tests/`
- **Integration Only**: `python -m pytest tests/integration/`  
- **Functionality Tests**: `python tests/integration/run_functionality_tests.py`
- **Single Test**: `python -m pytest tests/unit/test_specific.py::test_function_name`

**Unit Test Pattern**:
```python
from unittest.mock import Mock

def test_service():
    mock_converter = Mock(spec=IImageConverter)
    service = ImageConversionService(mock_converter)
    result = service.convert_image("test.jpg")
    assert result.success
```

**Integration Test Pattern**:
```python
def test_end_to_end():
    container = DIContainer.create_for_testing()
    service = container.get('image_conversion_service')
    result = service.convert_image("test_image.jpg")
    assert result.success and result.base64_data
```

Always run tests before committing. Fix any failures in the test suite before merging.

## Performance & Configuration

**Memory Settings** (in `config.json`):
- `processing.max_memory_usage_mb`: Limit memory usage
- `processing.enable_memory_optimization`: Enable streaming for large files
- `processing.max_concurrent_files`: Concurrent processing limit

**Cache Settings**:
- `cache.max_size_mb`: Cache size limit  
- `cache.backend`: "disk", "memory", or "redis"
- Clear cache: `curl -X DELETE http://localhost:5000/api/cache/clear`

**Security Settings**:
- `security.max_file_size_mb`: File upload limit
- `security.enable_content_scan`: Malware scanning
- `security.rate_limit_requests_per_minute`: Rate limiting

## Deployment

**Development**:
```bash
pip install -r requirements.txt
python run_web.py                    # Web server
python main.py image.png             # CLI
```

**Production**:
```bash
CONFIG_FILE=config.production.json python run_web.py --production --workers 4
```

**Docker**:
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app  
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "run_web.py", "--production"]
```

## Troubleshooting

**Memory Issues**:
- Adjust `processing.max_memory_usage_mb` in `config.json`
- Enable `processing.enable_memory_optimization` for large files

**Cache Issues**:
- Clear cache: `curl -X DELETE http://localhost:5000/api/cache/clear`
- Check `cache.max_size_mb` setting

**Performance Issues**:
- Tune `processing.max_concurrent_files`
- Verify `processing.enable_parallel_processing` is enabled

**Debugging**:
```bash
DEBUG=1 python main.py image.png        # Debug mode
LOG_LEVEL=DEBUG python run_web.py       # Verbose logging
tail -f logs/app.log                    # Monitor logs
```

## Extension Examples

**Add New Image Format**:
```python
class WebPConverter(IImageConverter):
    def convert_to_base64(self, file_path: str) -> ConversionResult:
        # WebP-specific logic
        pass

# Register in ServiceFactory
ServiceFactory.register_converter("webp", WebPConverter)
```

**Add New Cache Backend**:
```python
class RedisCache(ICacheManager):
    def get(self, key: str) -> Optional[Any]:
        # Redis implementation
        pass

# Register in CacheFactory  
CacheFactory.register_cache_type("redis", RedisCache)
```

**Add Processing Option**:
```python
@dataclass
class ProcessingOptions:
    # existing options...
    watermark_text: Optional[str] = None  # new option
    
    def validate(self):
        # validation for new option
        pass
```

## Documentation References

- **API Details**: `docs/API_ENDPOINTS.md` - Complete REST + WebSocket API reference
- **Architecture**: `docs/ARCHITECTURE.md` - Detailed system design and patterns  
- **Migration**: `docs/MIGRATION_GUIDE.md` - v1.x to v2.0 upgrade guide