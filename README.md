# Image Base64 Converter

A comprehensive Python tool for converting images to/from Base64 format with advanced processing capabilities. Provides both web UI and command-line interfaces for maximum flexibility.

## 🚀 Key Features

### Core Functionality
- **Multi-format Support**: PNG, JPG, JPEG, GIF, BMP, WEBP, TIFF, ICO
- **Bidirectional Conversion**: Image ↔ Base64 with full fidelity
- **Advanced Processing**: Resize, rotate, flip, compress, and format conversion
- **Batch Processing**: Handle multiple files simultaneously with progress tracking

### User Experience
- **Modern Web UI**: Drag & drop interface with real-time preview
- **Command Line Tool**: Perfect for automation and batch processing
- **Real-time Progress**: WebSocket-powered live updates during processing
- **One-click Copy**: Base64 data directly to clipboard

### Performance & Security
- **Intelligent Caching**: Avoid redundant processing with smart caching
- **Memory Optimization**: Handle large files efficiently with streaming
- **Security Validation**: Comprehensive file security scanning
- **Parallel Processing**: Multi-threaded processing for better performance

### Advanced Features
- **Image Editing**: Basic editing operations (rotate, flip, resize)
- **Quality Control**: Adjustable compression and quality settings
- **Format Conversion**: Convert between different image formats
- **Processing History**: Track and reuse previous conversions

## 📦 Installation & Setup

### Quick Start (Windows - Recommended)
1. **Install Dependencies**: Double-click `install_dependencies.bat`
2. **Launch Web UI**: Double-click `run_web.bat`
3. **Access Application**: Open http://localhost:5000 in your browser

### Manual Installation
```bash
# Clone the repository
git clone <repository-url>
cd image-base64-converter

# Install dependencies
pip install -r requirements.txt

# Launch web application
python run_web.py

# Or use CLI
python main.py image.png
```

### System Requirements
- **Python**: 3.7 or higher
- **Memory**: 2GB RAM minimum (4GB recommended for large files)
- **Storage**: 100MB for application + cache space
- **OS**: Windows, macOS, Linux

### Dependencies
- **PIL/Pillow**: Image processing
- **Flask**: Web framework
- **Flask-SocketIO**: Real-time communication
- **psutil**: System monitoring
- **Additional**: See `requirements.txt` for complete list

## 🎯 Usage Guide

### Web Interface (Recommended)

#### Basic Conversion
1. **Launch**: Run `run_web.bat` or `python run_web.py`
2. **Access**: Open http://localhost:5000 in your browser
3. **Convert**: Drag & drop images or click to select files
4. **Copy**: Click the copy button to get Base64 data

#### Advanced Processing
1. **Select Options**: Choose resize, quality, format, and rotation settings
2. **Preview**: See before/after comparison
3. **Batch Process**: Select multiple files for simultaneous processing
4. **Monitor Progress**: Watch real-time progress with WebSocket updates

#### Features Available in Web UI
- **Image Editing**: Resize, rotate, flip, and compress images
- **Format Conversion**: Convert between PNG, JPEG, WEBP, etc.
- **Quality Control**: Adjust compression levels and quality
- **Batch Operations**: Process multiple files with progress tracking
- **History**: View and reuse previous conversions
- **Cache Management**: Monitor and clear cache as needed

### Command Line Interface

#### Basic Usage
```bash
# Convert single image
python main.py image.png

# Save to file
python main.py image.png -o output.txt

# Batch process directory
python main.py /path/to/images/ -o /path/to/output/

# Windows batch file
run_cli.bat
```

#### Advanced CLI Options
```bash
# Resize image during conversion
python main.py image.png --width 800 --height 600

# Set quality and format
python main.py image.png --quality 90 --format JPEG

# Rotate and flip
python main.py image.png --rotate 90 --flip horizontal

# Enable caching
python main.py image.png --cache --cache-dir ./cache

# Security scan
python main.py image.png --security-scan

# Verbose output
python main.py image.png --verbose
```

### API Integration

#### REST API
```python
import requests

# Basic conversion
files = {'file': open('image.png', 'rb')}
response = requests.post('http://localhost:5000/api/convert/to-base64', files=files)
result = response.json()

# Advanced processing
options = {
    'resize_width': 800,
    'quality': 90,
    'target_format': 'JPEG'
}
data = {'options': json.dumps(options)}
response = requests.post('http://localhost:5000/api/convert/to-base64-advanced', 
                        files=files, data=data)
```

#### WebSocket Integration
```javascript
const socket = io();

// Join queue for updates
socket.emit('join_queue', {queue_id: 'your-queue-id'});

// Listen for progress
socket.on('batch_progress', (data) => {
    console.log(`Progress: ${data.progress_percentage}%`);
});
```

## 📋 Output Formats & Examples

### Data URI Format
The converted result is output in Data URI format, ready for immediate use:
```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

### Usage Examples

#### HTML Integration
```html
<img src="data:image/png;base64,..." alt="Converted Image">
<div style="background-image: url('data:image/jpeg;base64,...')"></div>
```

#### CSS Integration
```css
.background {
    background-image: url('data:image/webp;base64,...');
}
```

#### JavaScript Integration
```javascript
const img = new Image();
img.src = 'data:image/png;base64,...';
document.body.appendChild(img);
```

## 🎨 Supported Formats

### Input Formats
- **PNG**: Lossless compression, transparency support
- **JPEG/JPG**: Lossy compression, smaller file sizes
- **WEBP**: Modern format, excellent compression
- **GIF**: Animation support, limited colors
- **BMP**: Uncompressed, large file sizes
- **TIFF**: High quality, multiple pages
- **ICO**: Icon format, multiple sizes

### Output Formats
All input formats plus optimized variants:
- **PNG**: Optimized compression levels
- **JPEG**: Quality control (1-100)
- **WEBP**: Advanced compression options
- **Format Conversion**: Convert between any supported formats

### Processing Capabilities
- **Resize**: Maintain aspect ratio or custom dimensions
- **Rotate**: 90°, 180°, 270° rotations
- **Flip**: Horizontal and vertical flipping
- **Compress**: Quality adjustment and optimization
- **Convert**: Change format while processing

## 📁 Project Structure

```
image-base64-converter/
├── src/                           # Source code
│   ├── core/                      # Core processing modules
│   │   ├── converter.py           # Main conversion logic
│   │   ├── image_processor.py     # Advanced image processing
│   │   ├── multi_file_handler.py  # Batch processing
│   │   ├── cache_manager.py       # Caching system
│   │   ├── security_validator.py  # Security validation
│   │   ├── memory_optimizer.py    # Memory optimization
│   │   ├── parallel_processor.py  # Parallel processing
│   │   └── rate_limiter.py        # Rate limiting
│   ├── web/                       # Web application
│   │   ├── web_app.py            # Flask application
│   │   └── async_handler.py      # Async processing
│   ├── models/                    # Data models
│   │   ├── models.py             # Core models
│   │   └── processing_options.py # Processing options
│   ├── utils/                     # Utilities
│   │   └── utils.py              # Helper functions
│   ├── templates/                 # HTML templates
│   │   └── index.html            # Main web interface
│   └── static/                    # Static assets
│       ├── js/                   # JavaScript files
│       └── css/                  # Stylesheets
├── tests/                         # Test suite
│   ├── test_image_processor.py   # Image processing tests
│   ├── test_multi_file_handler.py # Batch processing tests
│   ├── test_cache_manager.py     # Cache tests
│   ├── test_security_validator.py # Security tests
│   └── test_integration.py       # Integration tests
├── logs/                          # Application logs
├── cache/                         # Cache directory
├── main.py                        # CLI entry point
├── run_web.py                     # Web server launcher
├── requirements.txt               # Python dependencies
├── install_dependencies.bat       # Windows installer
├── run_web.bat                   # Windows web launcher
├── run_cli.bat                   # Windows CLI launcher
├── API_ENDPOINTS.md              # API documentation
└── README.md                     # This file
```

## 🔧 Configuration

### Environment Variables
```bash
# Cache settings
CACHE_DIR=./cache
CACHE_MAX_SIZE_MB=100
CACHE_MAX_AGE_HOURS=24

# Security settings
MAX_FILE_SIZE_MB=10
ENABLE_SECURITY_SCAN=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Performance settings
MAX_CONCURRENT_PROCESSING=3
ENABLE_MEMORY_OPTIMIZATION=true
PARALLEL_PROCESSING_WORKERS=4
```

### Configuration Files
- **Cache**: Automatic cache management with configurable limits
- **Security**: Customizable security policies and validation rules
- **Performance**: Adjustable concurrency and memory settings
- **Logging**: Structured logging with multiple levels

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test category
python -m pytest tests/test_image_processor.py

# Run with coverage
python -m pytest tests/ --cov=src/

# Performance benchmarks
python performance_demo.py
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability and validation testing

## 🚀 Deployment

### Production Considerations
- **Security**: Implement authentication and authorization
- **Scaling**: Use load balancers and multiple instances
- **Monitoring**: Set up logging and performance monitoring
- **Caching**: Configure Redis or similar for distributed caching

### Docker Deployment
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "run_web.py"]
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests before committing
python -m pytest tests/

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Pillow**: Python Imaging Library for image processing
- **Flask**: Lightweight web framework
- **Socket.IO**: Real-time communication
- **Contributors**: Thanks to all contributors who helped improve this project