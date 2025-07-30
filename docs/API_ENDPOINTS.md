# API 엔드포인트 문서

이 문서는 이미지 Base64 변환기 애플리케이션의 모든 API 엔드포인트에 대한 포괄적인 문서를 제공합니다. 애플리케이션은 실시간 통신을 위한 REST API 엔드포인트와 WebSocket 연결을 모두 지원합니다.

## 개요

이미지 Base64 변환기는 다음과 같은 주요 기능을 제공합니다:
- **기본 변환**: 이미지를 Base64 포맷으로/에서 변환
- **고급 처리**: 이미지 변환 적용 (크기 조정, 회전, 압축, 포맷 변환)
- **배치 처리**: 진행률 추적과 함께 여러 파일 동시 처리
- **실시간 업데이트**: 실시간 진행률 업데이트를 위한 WebSocket 지원
- **보안 검증**: 파일 보안 스캔 및 검증
- **캐싱**: 성능 향상을 위한 지능형 캐싱

## v2.0 아키텍처 개선사항

- **의존성 주입**: 모든 API 핸들러가 서비스 레이어를 통해 작동
- **통합 에러 처리**: 일관된 에러 응답 형식
- **Result 패턴**: 성공/실패 상태를 명확히 구분하는 응답
- **구조화된 로깅**: 모든 API 호출에 대한 상세한 로그
- **성능 최적화**: 메모리 효율적인 스트리밍 처리

## WebSocket 지원

애플리케이션은 배치 처리 작업 중 실시간 업데이트를 위한 WebSocket 연결을 지원합니다.

**WebSocket URL:** `ws://localhost:5000/socket.io/`

### 연결 요구사항
- **프로토콜**: Socket.IO (Socket.IO 클라이언트 라이브러리와 호환)
- **CORS**: 모든 오리진에 대해 활성화 (프로덕션에서는 설정 필요)
- **인증**: 없음 (프로덕션에서 필요에 따라 구현)

### WebSocket 이벤트

#### 클라이언트에서 서버로 이벤트

**connect**: WebSocket 연결 설정
```javascript
socket.on('connect', () => {
  console.log('서버에 연결됨');
});
```

**join_queue**: 업데이트를 위한 특정 큐 룸 참여
```javascript
socket.emit('join_queue', { queue_id: 'your-queue-id' });
```

**leave_queue**: 큐 룸 떠나기
```javascript
socket.emit('leave_queue', { queue_id: 'your-queue-id' });
```

**request_progress**: Request current progress for a queue
```javascript
socket.emit('request_progress', { queue_id: 'your-queue-id' });
```

**cancel_batch**: Cancel batch processing via WebSocket
```javascript
socket.emit('cancel_batch', { queue_id: 'your-queue-id' });
```

**get_queue_status**: Get detailed queue status
```javascript
socket.emit('get_queue_status', { queue_id: 'your-queue-id' });
```

**get_active_queues**: Get list of all active queues
```javascript
socket.emit('get_active_queues');
```

#### 서버에서 클라이언트로 이벤트

**connected**: 연결 확인
```javascript
socket.on('connected', (data) => {
  console.log(data.message);
});
```

**batch_progress**: 실시간 진행률 업데이트
```javascript
socket.on('batch_progress', (data) => {
  console.log(`진행률: ${data.progress_percentage}%`);
  console.log(`현재 파일: ${data.current_file}`);
  console.log(`예상 남은 시간: ${data.estimated_time_remaining}초`);
});
```

**file_processed**: 개별 파일 완료 알림
```javascript
socket.on('file_processed', (data) => {
  console.log(`파일 처리됨: ${data.file_path}`);
  console.log(`성공: ${data.success}`);
  if (!data.success) {
    console.log(`오류: ${data.error_message}`);
  }
});
```

**batch_completed**: Batch processing completion
```javascript
socket.on('batch_completed', (data) => {
  console.log(`Batch completed: ${data.successful_files}/${data.total_files} files`);
  console.log('Processing summary:', data.processing_summary);
});
```

**batch_cancelled**: Batch processing cancellation
```javascript
socket.on('batch_cancelled', (data) => {
  console.log(`Batch cancelled: ${data.message}`);
});
```

**batch_error**: Batch processing error
```javascript
socket.on('batch_error', (data) => {
  console.log(`Batch error: ${data.error}`);
});
```

**queue_status**: Queue status information
```javascript
socket.on('queue_status', (data) => {
  console.log('Queue info:', data.queue_info);
  console.log('Task status:', data.task_status);
});
```

**active_queues**: List of active queues
```javascript
socket.on('active_queues', (data) => {
  console.log('Active tasks:', data.active_tasks);
  console.log('All queues:', data.all_queues);
});
```

### WebSocket Usage Example

```javascript
// Connect to WebSocket
const socket = io();

// Join a queue room for real-time updates
socket.emit('join_queue', { queue_id: queueId });

// Listen for progress updates
socket.on('batch_progress', (data) => {
  updateProgressBar(data.progress_percentage);
  updateCurrentFile(data.current_file);
  updateETA(data.estimated_time_remaining);
});

// Listen for file completion
socket.on('file_processed', (data) => {
  addFileToCompletedList(data);
});

// Listen for batch completion
socket.on('batch_completed', (data) => {
  showCompletionSummary(data);
  socket.emit('leave_queue', { queue_id: queueId });
});

// Handle errors
socket.on('batch_error', (data) => {
  showError(data.error);
});
```

## REST API Endpoints

All REST API endpoints return JSON responses and follow standard HTTP status codes. The base URL for all endpoints is `http://localhost:5000` (adjust for your deployment).

### Basic Conversion Endpoints

#### 1. Convert Image to Base64

**Endpoint:** `POST /api/convert/to-base64`

**Description:** Convert a single image file to Base64 format with basic processing.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file`: Image file to convert (required)

**Response:**
```json
{
  "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "format": "PNG",
  "size": [1920, 1080],
  "file_size": 45678
}
```

#### 2. Convert Base64 to Image

**Endpoint:** `POST /api/convert/from-base64`

**Description:** Convert Base64 data back to an image file.

**Request:**
```json
{
  "base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "format": "PNG"
}
```

**Response:** Binary image file download

#### 3. Validate Base64 Data

**Endpoint:** `POST /api/validate-base64`

**Description:** Validate if Base64 data represents a valid image.

**Request:**
```json
{
  "base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Response:**
```json
{
  "valid": true,
  "format": "PNG",
  "size": [1920, 1080],
  "mode": "RGBA"
}
```

### Advanced Processing Endpoints

#### 1. Advanced Image Conversion

**Endpoint:** `POST /api/convert/to-base64-advanced`

**Description:** Convert an image to Base64 with advanced processing options.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file`: Image file to convert
  - `options`: JSON string with processing options

**Processing Options:**
```json
{
  "resize_width": 800,           // Target width (optional)
  "resize_height": 600,          // Target height (optional)
  "maintain_aspect_ratio": true, // Maintain aspect ratio during resize
  "quality": 85,                 // Image quality (1-100)
  "target_format": "JPEG",       // Target format (PNG, JPEG, WEBP)
  "rotation_angle": 90,          // Rotation angle (0, 90, 180, 270)
  "flip_horizontal": false,      // Flip horizontally
  "flip_vertical": false         // Flip vertically
}
```

**Response:**
```json
{
  "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "original_format": "PNG",
  "original_size": [1920, 1080],
  "processed_format": "JPEG",
  "processed_size": [800, 450],
  "file_size": 45678,
  "processing_options": {
    "resize_width": 800,
    "resize_height": null,
    "maintain_aspect_ratio": true,
    "quality": 85,
    "target_format": "JPEG",
    "rotation_angle": 0,
    "flip_horizontal": false,
    "flip_vertical": false
  }
}
```

#### 2. Batch Processing Start

**Endpoint:** `POST /api/convert/batch-start`

**Description:** Start batch processing of multiple images.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `files`: Multiple image files to process
  - `options`: JSON string with processing options (same as advanced endpoint)

**Response:**
```json
{
  "queue_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_files": 5,
  "status": "started",
  "message": "5개 파일의 배치 처리가 시작되었습니다."
}
```

#### 3. Batch Processing Progress

**Endpoint:** `GET /api/convert/batch-progress/{queue_id}`

**Description:** Check the progress of batch processing.

**Response (Processing):**
```json
{
  "queue_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_files": 5,
  "completed_files": 2,
  "current_file": "image3.jpg",
  "estimated_time_remaining": 15.5,
  "status": "processing",
  "error_count": 0,
  "start_time": 1640995200.0,
  "current_file_progress": 0.5,
  "progress_percentage": 50.0,
  "success_rate": 100.0
}
```

**Response (Completed):**
```json
{
  "queue_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_files": 5,
  "completed_files": 5,
  "current_file": "",
  "estimated_time_remaining": 0.0,
  "status": "completed",
  "error_count": 0,
  "start_time": 1640995200.0,
  "current_file_progress": 1.0,
  "progress_percentage": 100.0,
  "success_rate": 100.0,
  "successful_files": 5,
  "failed_files": 0,
  "average_processing_time": 2.3,
  "total_processing_time": 11.5,
  "successful_results": [
    {
      "file_path": "/tmp/image1.jpg",
      "format": "JPEG",
      "size": [800, 600],
      "file_size": 45678,
      "processing_time": 2.1
    }
  ],
  "failed_file_details": []
}
```

## Status Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid request parameters or file
- **404 Not Found**: Queue not found (for progress endpoint)
- **500 Internal Server Error**: Server error during processing

## Error Response Format

```json
{
  "error": "Error message description"
}
```

## Usage Examples

### cURL Examples

**Advanced Conversion:**
```bash
curl -X POST http://localhost:5000/api/convert/to-base64-advanced \
  -F "file=@image.jpg" \
  -F 'options={"resize_width":800,"quality":90,"target_format":"JPEG"}'
```

**Batch Processing:**
```bash
# Start batch
curl -X POST http://localhost:5000/api/convert/batch-start \
  -F "files=@image1.jpg" \
  -F "files=@image2.png" \
  -F 'options={"quality":85,"target_format":"JPEG"}'

# Check progress
curl http://localhost:5000/api/convert/batch-progress/QUEUE_ID
```

### JavaScript Examples

**Advanced Conversion:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('options', JSON.stringify({
  resize_width: 800,
  quality: 90,
  target_format: 'JPEG'
}));

fetch('/api/convert/to-base64-advanced', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

**Batch Processing:**
```javascript
const formData = new FormData();
for (let file of fileInput.files) {
  formData.append('files', file);
}
formData.append('options', JSON.stringify({
  quality: 85,
  target_format: 'JPEG'
}));

fetch('/api/convert/batch-start', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  const queueId = data.queue_id;
  // Poll for progress
  const checkProgress = () => {
    fetch(`/api/convert/batch-progress/${queueId}`)
      .then(response => response.json())
      .then(progress => {
        console.log(`Progress: ${progress.progress_percentage}%`);
        if (progress.status !== 'completed') {
          setTimeout(checkProgress, 1000);
        }
      });
  };
  checkProgress();
});
```

#### 4. Batch Processing Cancellation

**Endpoint:** `DELETE /api/convert/batch-cancel/{queue_id}`

**Description:** Cancel an ongoing batch processing operation.

**Response:**
```json
{
  "queue_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "배치 처리가 취소되었습니다."
}
```

#### 5. Batch Status Overview

**Endpoint:** `GET /api/convert/batch-status`

**Description:** Get overview of all batch processing operations.

**Response:**
```json
{
  "active_tasks": ["queue-id-1", "queue-id-2"],
  "all_queues": {
    "queue-id-1": {
      "queue_id": "queue-id-1",
      "status": "processing",
      "total_files": 5,
      "completed_files": 2,
      "created_time": 1640995200.0
    }
  },
  "statistics": {
    "total_queues": 3,
    "active_queues": 1,
    "completed_queues": 2,
    "total_files": 15,
    "completed_files": 12
  },
  "timestamp": 1640995800.0
}
```

#### 6. Batch Cleanup

**Endpoint:** `POST /api/convert/batch-cleanup`

**Description:** Clean up completed batch operations and free memory.

**Request (Optional):**
```json
{
  "max_age_hours": 24.0
}
```

**Response:**
```json
{
  "cleaned_tasks": 2,
  "cleaned_queues": 3,
  "cleaned_tracking": 1,
  "message": "2개 작업, 3개 큐, 1개 추적이 정리되었습니다."
}
```

### Cache Management Endpoints

#### 7. Cache Status

**Endpoint:** `GET /api/cache/status`

**Description:** Get current cache statistics and status information.

**Response:**
```json
{
  "hits": 150,
  "misses": 25,
  "total_requests": 175,
  "hit_rate_percent": 85.71,
  "memory_entries": 45,
  "disk_entries": 120,
  "cache_size_mb": 25.6,
  "max_size_mb": 100.0,
  "size_utilization_percent": 25.6,
  "cleanup_runs": 3,
  "errors": 0
}
```

#### 8. Clear Cache

**Endpoint:** `DELETE /api/cache/clear`

**Description:** Clear all cached data to free up space.

**Response:**
```json
{
  "message": "Cache cleared successfully",
  "entries_removed": 120,
  "space_freed_mb": 25.6
}
```

### Security Endpoints

#### 9. Security Scan

**Endpoint:** `POST /api/security/scan`

**Description:** Perform security validation on an uploaded file.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file`: File to scan (required)

**Response:**
```json
{
  "is_safe": true,
  "threat_level": "low",
  "warnings": [],
  "scan_time": 0.15,
  "file_size_check": true,
  "mime_type_check": true,
  "header_check": true,
  "content_check": true,
  "scan_details": {
    "file_size": 45678,
    "detected_mime_type": "image/jpeg",
    "detected_format": "image/jpeg"
  }
}
```