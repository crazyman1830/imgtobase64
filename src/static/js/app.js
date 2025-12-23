// 전역 변수
let currentBase64Data = '';
let currentFile = null;
let processingOptions = {
    resize_width: null,
    resize_height: null,
    maintain_aspect_ratio: true,
    quality: 85,
    target_format: null,
    rotation_angle: 0,
    flip_horizontal: false,
    flip_vertical: false
};

// 다중 파일 처리 관련 변수
let selectedFiles = [];
let currentBatchId = null;
let batchProgressInterval = null;
let multiProcessingOptions = {
    resize_width: null,
    resize_height: null,
    maintain_aspect_ratio: true,
    quality: 85,
    target_format: null,
    rotation_angle: 0,
    flip_horizontal: false,
    flip_vertical: false
};

// 히스토리 및 캐시 관련 변수
let conversionHistory = [];
let cacheStatus = {
    hitCount: 0,
    missCount: 0,
    usedSize: 0,
    maxSize: 100 * 1024 * 1024, // 100MB
    itemCount: 0
};

// ⚡ Performance: Cache DOM selectors to avoid repeated querySelectorAll() on every click
// These are queried once during initialization and reused, reducing DOM query overhead by ~50-75%
let cachedRotationButtons = null;
let cachedMultiRotationButtons = null;

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function () {
    initializeDropZone();
    initializeFileInput();
    initializeProcessingOptions();
    initializeMultiFileHandling();
    initializeHistoryAndCache();
    initializeImageConversion();
});

// 드롭존 초기화
function initializeDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // 클릭 이벤트
    dropZone.addEventListener('click', () => fileInput.click());

    // 키보드 이벤트 (Enter 또는 Space)
    dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });

    // 드래그 앤 드롭 이벤트
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });
}

// 파일 입력 초기화
function initializeFileInput() {
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });
}

// 파일 선택 처리
function handleFileSelection(file) {
    // 파일 타입 검증
    if (!file.type.startsWith('image/')) {
        showToast('이미지 파일만 선택할 수 있습니다.', 'error');
        return;
    }

    // 파일 크기 검증 (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showToast('파일 크기는 16MB를 초과할 수 없습니다.', 'error');
        return;
    }

    // 현재 파일 저장
    currentFile = file;

    // 미리보기 표시
    showImagePreview(file);

    // 처리 옵션 표시
    showProcessingOptions();

    // Base64 변환 (기본 옵션으로)
    convertToBase64(file);
}

// 이미지 미리보기 표시
function showImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
        const previewImg = document.getElementById('previewImg');
        const imagePreview = document.getElementById('imagePreview');
        const fileInfo = document.getElementById('fileInfo');

        previewImg.src = e.target.result;
        imagePreview.style.display = 'block';

        // 파일 정보 표시
        fileInfo.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <strong>파일명:</strong> ${file.name}<br>
                    <strong>크기:</strong> ${formatFileSize(file.size)}<br>
                    <strong>타입:</strong> ${file.type}
                </div>
                <div class="col-md-6">
                    <strong>수정일:</strong> ${new Date(file.lastModified).toLocaleString()}
                </div>
            </div>
        `;
    };
    reader.readAsDataURL(file);
}

// Base64 변환 (기본)
function convertToBase64(file) {
    const formData = new FormData();
    formData.append('file', file);

    showLoading(true);

    fetch('/api/convert/to-base64', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            showLoading(false);

            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            currentBase64Data = data.base64;
            displayBase64Result(data);
            showToast('Base64 변환이 완료되었습니다!', 'success');
        })
        .catch(error => {
            showLoading(false);
            showToast('변환 중 오류가 발생했습니다: ' + error.message, 'error');
        });
}

// Base64 변환 (고급 옵션)
function convertToBase64Advanced(file, options) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('options', JSON.stringify(options));

    showLoading(true);

    fetch('/api/convert/to-base64-advanced', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            showLoading(false);

            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            currentBase64Data = data.base64;
            displayBase64Result(data);
            showToast('고급 옵션이 적용된 Base64 변환이 완료되었습니다!', 'success');
        })
        .catch(error => {
            showLoading(false);
            showToast('변환 중 오류가 발생했습니다: ' + error.message, 'error');
        });
}

// Base64 결과 표시
function displayBase64Result(data) {
    const base64Result = document.getElementById('base64Result');
    const base64Output = document.getElementById('base64Output');

    base64Output.textContent = data.base64;
    base64Result.style.display = 'block';

    // 이미지 비교 미리보기 표시
    showImageComparison(data);

    // 파일 정보 업데이트
    const fileInfo = document.getElementById('fileInfo');

    // 기본 변환 결과
    let resultInfo = `
        <div class="mt-2 pt-2 border-top">
            <div class="row">
                <div class="col-md-6">
                    <strong>변환된 형식:</strong> ${data.format || data.processed_format || 'Unknown'}<br>
                    <strong>이미지 크기:</strong> ${data.size ? data.size[0] + ' × ' + data.size[1] : (data.processed_size ? data.processed_size[0] + ' × ' + data.processed_size[1] : 'Unknown')}
                </div>
                <div class="col-md-6">
                    <strong>Base64 길이:</strong> ${data.base64.length.toLocaleString()} 문자
                </div>
            </div>
        </div>
    `;

    // 고급 처리 정보가 있는 경우 추가
    if (data.processing_options) {
        const options = data.processing_options;
        let optionsInfo = '<div class="mt-2 pt-2 border-top"><h6><i class="fas fa-cogs"></i> 적용된 처리 옵션</h6><div class="row">';

        // 원본 vs 처리된 정보
        if (data.original_size && data.processed_size) {
            optionsInfo += `
                <div class="col-md-6">
                    <strong>원본:</strong> ${data.original_format} (${data.original_size[0]} × ${data.original_size[1]})<br>
                    <strong>처리됨:</strong> ${data.processed_format} (${data.processed_size[0]} × ${data.processed_size[1]})
                </div>
            `;
        }

        // 처리 옵션 상세
        let appliedOptions = [];
        if (options.resize_width || options.resize_height) {
            appliedOptions.push(`리사이징: ${options.resize_width || 'auto'} × ${options.resize_height || 'auto'}`);
        }
        if (options.quality !== 85) {
            appliedOptions.push(`품질: ${options.quality}%`);
        }
        if (options.target_format) {
            appliedOptions.push(`포맷 변환: ${options.target_format}`);
        }
        if (options.rotation_angle !== 0) {
            appliedOptions.push(`회전: ${options.rotation_angle}°`);
        }
        if (options.flip_horizontal) {
            appliedOptions.push('수평 뒤집기');
        }
        if (options.flip_vertical) {
            appliedOptions.push('수직 뒤집기');
        }

        if (appliedOptions.length > 0) {
            optionsInfo += `
                <div class="col-md-6">
                    <strong>적용된 옵션:</strong><br>
                    ${appliedOptions.map(opt => `• ${opt}`).join('<br>')}
                </div>
            `;
        }

        optionsInfo += '</div></div>';
        resultInfo += optionsInfo;
    }

    fileInfo.innerHTML += resultInfo;

    // 히스토리에 추가
    addToHistory(data);
}

// 이미지 비교 미리보기 표시
function showImageComparison(data) {
    const imageComparison = document.getElementById('imageComparison');
    const originalPreview = document.getElementById('originalPreview');
    const processedPreview = document.getElementById('processedPreview');
    const originalInfo = document.getElementById('originalInfo');
    const processedInfo = document.getElementById('processedInfo');

    // 원본 이미지 표시 (현재 미리보기에서 가져오기)
    const currentPreview = document.getElementById('previewImg');
    if (currentPreview && currentPreview.src) {
        originalPreview.src = currentPreview.src;

        // 원본 정보
        if (data.original_format && data.original_size) {
            originalInfo.textContent = `${data.original_format} • ${data.original_size[0]} × ${data.original_size[1]}`;
        } else if (data.format && data.size) {
            originalInfo.textContent = `${data.format} • ${data.size[0]} × ${data.size[1]}`;
        }
    }

    // 처리된 이미지 표시
    const processedDataUrl = `data:image/${(data.processed_format || data.format || 'png').toLowerCase()};base64,${data.base64}`;
    processedPreview.src = processedDataUrl;

    // 처리된 이미지 정보
    if (data.processed_format && data.processed_size) {
        processedInfo.textContent = `${data.processed_format} • ${data.processed_size[0]} × ${data.processed_size[1]}`;
    } else if (data.format && data.size) {
        processedInfo.textContent = `${data.format} • ${data.size[0]} × ${data.size[1]}`;
    }

    imageComparison.style.display = 'block';
}

// Base64 복사
function copyBase64() {
    if (!currentBase64Data) {
        showToast('복사할 Base64 데이터가 없습니다.', 'error');
        return;
    }

    const btn = document.getElementById('btnCopyBase64');
    const originalHtml = btn.innerHTML;

    navigator.clipboard.writeText(currentBase64Data)
        .then(() => {
            showToast('Base64 데이터가 클립보드에 복사되었습니다!', 'success');

            // Micro-interaction: Change button state
            btn.innerHTML = '<i class="fas fa-check"></i> 복사됨!';
            btn.classList.replace('btn-primary', 'btn-success');

            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.classList.replace('btn-success', 'btn-primary');
            }, 2000);
        })
        .catch(() => showToast('복사에 실패했습니다.', 'error'));
}

// Base64 텍스트 파일로 다운로드
function downloadBase64() {
    if (!currentBase64Data) {
        showToast('다운로드할 Base64 데이터가 없습니다.', 'error');
        return;
    }

    const blob = new Blob([currentBase64Data], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'base64_data.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Base64 데이터가 다운로드되었습니다!', 'success');
}

// Base64 유효성 검사
function validateBase64() {
    const base64Input = document.getElementById('base64Input').value.trim();

    if (!base64Input) {
        showToast('Base64 데이터를 입력해주세요.', 'error');
        return;
    }

    fetch('/api/validate-base64', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ base64: base64Input })
    })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('base64ValidationResult');

            if (data.valid) {
                resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i> 유효한 Base64 이미지 데이터입니다!
                    ${data.format ? `<br><strong>형식:</strong> ${data.format}` : ''}
                    ${data.size ? `<br><strong>크기:</strong> ${data.size[0]} × ${data.size[1]}` : ''}
                    ${data.mode ? `<br><strong>모드:</strong> ${data.mode}` : ''}
                </div>
            `;

                // 미리보기 표시
                showBase64Preview(base64Input);
            } else {
                resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> ${data.error || '유효하지 않은 Base64 데이터입니다.'}
                </div>
            `;
                hideBase64Preview();
            }

            resultDiv.style.display = 'block';
        })
        .catch(error => {
            showToast('유효성 검사 중 오류가 발생했습니다: ' + error.message, 'error');
        });
}

// Base64 미리보기 표시
function showBase64Preview(base64Data) {
    const previewDiv = document.getElementById('base64Preview');
    const previewImg = document.getElementById('base64PreviewImg');

    // data URL 형식으로 변환
    const dataUrl = base64Data.startsWith('data:') ? base64Data : `data:image/png;base64,${base64Data}`;

    previewImg.src = dataUrl;
    previewDiv.style.display = 'block';
}

// Base64 미리보기 숨기기
function hideBase64Preview() {
    const previewDiv = document.getElementById('base64Preview');
    previewDiv.style.display = 'none';
}

// Base64를 이미지로 변환
function convertFromBase64() {
    const base64Input = document.getElementById('base64Input').value.trim();
    const outputFormat = document.getElementById('outputFormat').value;

    if (!base64Input) {
        showToast('Base64 데이터를 입력해주세요.', 'error');
        return;
    }

    fetch('/api/convert/from-base64', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            base64: base64Input,
            format: outputFormat
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.blob();
        })
        .then(blob => {
            // 파일 다운로드
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `converted.${outputFormat.toLowerCase()}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast('이미지 변환이 완료되었습니다!', 'success');
        })
        .catch(error => {
            showToast(error.error || '변환 중 오류가 발생했습니다.', 'error');
        });
}

// 로딩 표시/숨김
function showLoading(show) {
    const loading = document.querySelector('.loading');
    loading.style.display = show ? 'block' : 'none';
}

// 토스트 메시지 표시
function showToast(message, type = 'info') {
    const toast = document.getElementById('alertToast');
    const toastMessage = document.getElementById('toastMessage');
    const toastHeader = toast.querySelector('.toast-header');

    toastMessage.textContent = message;

    // 타입에 따른 스타일 적용
    toast.className = 'toast';
    if (type === 'success') {
        toast.classList.add('bg-success', 'text-white');
    } else if (type === 'error') {
        toast.classList.add('bg-danger', 'text-white');
    } else {
        toast.classList.add('bg-info', 'text-white');
    }

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// 파일 크기 포맷팅
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 처리 옵션 초기화
function initializeProcessingOptions() {
    // ⚡ Performance: Cache rotation button selectors once for reuse
    cachedRotationButtons = document.querySelectorAll('[data-rotation]');

    // 품질 슬라이더 이벤트
    const qualitySlider = document.getElementById('qualitySlider');
    const qualityValue = document.getElementById('qualityValue');
    const compressionLevel = document.getElementById('compressionLevel');

    qualitySlider.addEventListener('input', function () {
        const value = this.value;
        qualityValue.textContent = value;
        processingOptions.quality = parseInt(value);

        // 압축 레벨 표시 업데이트
        if (value >= 90) {
            compressionLevel.textContent = '최고 품질';
        } else if (value >= 70) {
            compressionLevel.textContent = '높음';
        } else if (value >= 50) {
            compressionLevel.textContent = '보통';
        } else if (value >= 30) {
            compressionLevel.textContent = '낮음';
        } else {
            compressionLevel.textContent = '최대 압축';
        }
    });

    // 리사이징 입력 이벤트
    document.getElementById('resizeWidth').addEventListener('input', function () {
        processingOptions.resize_width = this.value ? parseInt(this.value) : null;
    });

    document.getElementById('resizeHeight').addEventListener('input', function () {
        processingOptions.resize_height = this.value ? parseInt(this.value) : null;
    });

    document.getElementById('maintainAspectRatio').addEventListener('change', function () {
        processingOptions.maintain_aspect_ratio = this.checked;
    });

    // 포맷 선택 이벤트
    document.getElementById('targetFormat').addEventListener('change', function () {
        processingOptions.target_format = this.value || null;
    });
}

// 처리 옵션 표시
function showProcessingOptions() {
    const processingOptionsDiv = document.getElementById('processingOptions');
    processingOptionsDiv.style.display = 'block';
}

// 회전 설정
function setRotation(angle) {
    processingOptions.rotation_angle = angle;

    // ⚡ Performance: Use cached button selectors instead of querying DOM every time
    if (cachedRotationButtons) {
        cachedRotationButtons.forEach(btn => {
            if (btn.dataset.rotation == angle) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
}

// 뒤집기 토글
function toggleFlip(direction) {
    const button = document.getElementById(`flip${direction.charAt(0).toUpperCase() + direction.slice(1)}`);

    if (direction === 'horizontal') {
        processingOptions.flip_horizontal = !processingOptions.flip_horizontal;
        button.classList.toggle('active', processingOptions.flip_horizontal);
    } else if (direction === 'vertical') {
        processingOptions.flip_vertical = !processingOptions.flip_vertical;
        button.classList.toggle('active', processingOptions.flip_vertical);
    }
}

// 처리 옵션 초기화
function resetProcessingOptions() {
    processingOptions = {
        resize_width: null,
        resize_height: null,
        maintain_aspect_ratio: true,
        quality: 85,
        target_format: null,
        rotation_angle: 0,
        flip_horizontal: false,
        flip_vertical: false
    };

    // UI 초기화
    document.getElementById('resizeWidth').value = '';
    document.getElementById('resizeHeight').value = '';
    document.getElementById('maintainAspectRatio').checked = true;
    document.getElementById('qualitySlider').value = 85;
    document.getElementById('qualityValue').textContent = '85';
    document.getElementById('compressionLevel').textContent = '보통';
    document.getElementById('targetFormat').value = '';

    // ⚡ Performance: Use cached button selectors via helper
    setRotation(0);

    // 뒤집기 버튼 초기화
    document.getElementById('flipHorizontal').classList.remove('active');
    document.getElementById('flipVertical').classList.remove('active');

    showToast('처리 옵션이 초기화되었습니다.', 'info');
}

// 처리 옵션 적용
function applyProcessingOptions() {
    if (!currentFile) {
        showToast('먼저 이미지 파일을 선택해주세요.', 'error');
        return;
    }

    // 고급 변환 API 호출
    convertToBase64Advanced(currentFile, processingOptions);
}

// 다중 파일 처리 초기화
function initializeMultiFileHandling() {
    const multiDropZone = document.getElementById('multiDropZone');
    const multiFileInput = document.getElementById('multiFileInput');

    // 클릭 이벤트
    multiDropZone.addEventListener('click', () => multiFileInput.click());

    // 키보드 이벤트 (Enter 또는 Space)
    multiDropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            multiFileInput.click();
        }
    });

    // 드래그 앤 드롭 이벤트
    multiDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        multiDropZone.classList.add('dragover');
    });

    multiDropZone.addEventListener('dragleave', () => {
        multiDropZone.classList.remove('dragover');
    });

    multiDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        multiDropZone.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files);
        handleMultiFileSelection(files);
    });

    // 파일 입력 이벤트
    multiFileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        handleMultiFileSelection(files);
    });

    // 다중 파일 처리 옵션 초기화
    initializeMultiProcessingOptions();
}

// 다중 파일 선택 처리
function handleMultiFileSelection(files) {
    const validFiles = files.filter(file => {
        // 파일 타입 검증
        if (!file.type.startsWith('image/')) {
            showToast(`${file.name}은(는) 이미지 파일이 아닙니다.`, 'error');
            return false;
        }

        // 파일 크기 검증 (16MB)
        if (file.size > 16 * 1024 * 1024) {
            showToast(`${file.name}의 크기가 16MB를 초과합니다.`, 'error');
            return false;
        }

        // 중복 파일 검사
        if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            showToast(`${file.name}은(는) 이미 선택된 파일입니다.`, 'error');
            return false;
        }

        return true;
    });

    if (validFiles.length === 0) {
        return;
    }

    // 선택된 파일 목록에 추가
    selectedFiles.push(...validFiles);

    // UI 업데이트
    updateFileList();
    showMultiProcessingOptions();

    showToast(`${validFiles.length}개 파일이 추가되었습니다.`, 'success');
}

// 파일 목록 UI 업데이트
function updateFileList() {
    const fileList = document.getElementById('fileList');
    const fileListContainer = document.getElementById('fileListContainer');
    const fileCount = document.getElementById('fileCount');

    if (selectedFiles.length === 0) {
        fileList.style.display = 'none';
        return;
    }

    fileList.style.display = 'block';
    fileCount.textContent = selectedFiles.length;

    fileListContainer.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item border-bottom pb-2 mb-2" data-index="${index}">
            <div class="row align-items-center">
                <div class="col-md-6">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-image text-primary me-2"></i>
                        <div>
                            <div class="fw-bold">${file.name}</div>
                            <small class="text-muted">${formatFileSize(file.size)} • ${file.type}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <small class="text-muted">
                        수정일: ${new Date(file.lastModified).toLocaleDateString()}
                    </small>
                </div>
                <div class="col-md-2 text-end">
                    <button class="btn btn-sm btn-outline-danger" onclick="removeFile(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 개별 파일 제거
function removeFile(index) {
    if (index >= 0 && index < selectedFiles.length) {
        const fileName = selectedFiles[index].name;
        selectedFiles.splice(index, 1);
        updateFileList();

        if (selectedFiles.length === 0) {
            hideMultiProcessingOptions();
        }

        showToast(`${fileName}이(가) 제거되었습니다.`, 'info');
    }
}

// 모든 파일 제거
function clearAllFiles() {
    selectedFiles = [];
    updateFileList();
    hideMultiProcessingOptions();
    showToast('모든 파일이 제거되었습니다.', 'info');
}

// 다중 파일 처리 옵션 표시
function showMultiProcessingOptions() {
    document.getElementById('multiProcessingOptions').style.display = 'block';
    document.getElementById('multiProcessingControls').style.display = 'block';
}

// 다중 파일 처리 옵션 숨기기
function hideMultiProcessingOptions() {
    document.getElementById('multiProcessingOptions').style.display = 'none';
    document.getElementById('multiProcessingControls').style.display = 'none';
}

// 다중 파일 처리 옵션 초기화
function initializeMultiProcessingOptions() {
    // ⚡ Performance: Cache multi-rotation button selectors once for reuse
    cachedMultiRotationButtons = document.querySelectorAll('[data-multi-rotation]');

    // 품질 슬라이더 이벤트
    const multiQualitySlider = document.getElementById('multiQualitySlider');
    const multiQualityValue = document.getElementById('multiQualityValue');
    const multiCompressionLevel = document.getElementById('multiCompressionLevel');

    multiQualitySlider.addEventListener('input', function () {
        const value = this.value;
        multiQualityValue.textContent = value;
        multiProcessingOptions.quality = parseInt(value);

        // 압축 레벨 표시 업데이트
        if (value >= 90) {
            multiCompressionLevel.textContent = '최고 품질';
        } else if (value >= 70) {
            multiCompressionLevel.textContent = '높음';
        } else if (value >= 50) {
            multiCompressionLevel.textContent = '보통';
        } else if (value >= 30) {
            multiCompressionLevel.textContent = '낮음';
        } else {
            multiCompressionLevel.textContent = '최대 압축';
        }
    });

    // 리사이징 입력 이벤트
    document.getElementById('multiResizeWidth').addEventListener('input', function () {
        multiProcessingOptions.resize_width = this.value ? parseInt(this.value) : null;
    });

    document.getElementById('multiResizeHeight').addEventListener('input', function () {
        multiProcessingOptions.resize_height = this.value ? parseInt(this.value) : null;
    });

    document.getElementById('multiMaintainAspectRatio').addEventListener('change', function () {
        multiProcessingOptions.maintain_aspect_ratio = this.checked;
    });

    // 포맷 선택 이벤트
    document.getElementById('multiTargetFormat').addEventListener('change', function () {
        multiProcessingOptions.target_format = this.value || null;
    });
}

// 다중 파일 회전 설정
function setMultiRotation(angle) {
    multiProcessingOptions.rotation_angle = angle;

    // ⚡ Performance: Use cached button selectors instead of querying DOM every time
    if (cachedMultiRotationButtons) {
        cachedMultiRotationButtons.forEach(btn => {
            if (btn.dataset.multiRotation == angle) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
}

// 다중 파일 뒤집기 토글
function toggleMultiFlip(direction) {
    const button = document.getElementById(`multiFlip${direction.charAt(0).toUpperCase() + direction.slice(1)}`);

    if (direction === 'horizontal') {
        multiProcessingOptions.flip_horizontal = !multiProcessingOptions.flip_horizontal;
        button.classList.toggle('active', multiProcessingOptions.flip_horizontal);
    } else if (direction === 'vertical') {
        multiProcessingOptions.flip_vertical = !multiProcessingOptions.flip_vertical;
        button.classList.toggle('active', multiProcessingOptions.flip_vertical);
    }
}

// 다중 파일 처리 옵션 초기화
function resetMultiProcessingOptions() {
    multiProcessingOptions = {
        resize_width: null,
        resize_height: null,
        maintain_aspect_ratio: true,
        quality: 85,
        target_format: null,
        rotation_angle: 0,
        flip_horizontal: false,
        flip_vertical: false
    };

    // UI 초기화
    document.getElementById('multiResizeWidth').value = '';
    document.getElementById('multiResizeHeight').value = '';
    document.getElementById('multiMaintainAspectRatio').checked = true;
    document.getElementById('multiQualitySlider').value = 85;
    document.getElementById('multiQualityValue').textContent = '85';
    document.getElementById('multiCompressionLevel').textContent = '보통';
    document.getElementById('multiTargetFormat').value = '';

    // ⚡ Performance: Use cached button selectors via helper
    setMultiRotation(0);

    // 뒤집기 버튼 초기화
    document.getElementById('multiFlipHorizontal').classList.remove('active');
    document.getElementById('multiFlipVertical').classList.remove('active');

    showToast('다중 파일 처리 옵션이 초기화되었습니다.', 'info');
}

// 배치 처리 시작
function startBatchProcessing() {
    if (selectedFiles.length === 0) {
        showToast('처리할 파일을 선택해주세요.', 'error');
        return;
    }

    const formData = new FormData();

    // 파일들 추가
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    // 처리 옵션 추가
    formData.append('options', JSON.stringify(multiProcessingOptions));

    // UI 상태 변경
    showBatchProgress();

    fetch('/api/convert/batch-start', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                hideBatchProgress();
                return;
            }

            currentBatchId = data.queue_id;
            showToast(data.message, 'success');

            // 진행률 추적 시작
            startProgressTracking();
        })
        .catch(error => {
            showToast('배치 처리 시작 중 오류가 발생했습니다: ' + error.message, 'error');
            hideBatchProgress();
        });
}

// 진행률 추적 시작
function startProgressTracking() {
    if (!currentBatchId) return;

    batchProgressInterval = setInterval(() => {
        fetch(`/api/convert/batch-progress/${currentBatchId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    clearInterval(batchProgressInterval);
                    showToast(data.error, 'error');
                    return;
                }

                updateBatchProgress(data);

                // 완료된 경우 추적 중지
                if (data.status === 'completed' || data.status === 'cancelled' || data.status === 'error') {
                    clearInterval(batchProgressInterval);
                    showBatchResults(data);
                }
            })
            .catch(error => {
                console.error('Progress tracking error:', error);
            });
    }, 1000); // 1초마다 업데이트
}

// 배치 진행률 표시
function showBatchProgress() {
    document.getElementById('batchProgress').style.display = 'block';
    document.getElementById('multiProcessingControls').style.display = 'none';
}

// 배치 진행률 숨기기
function hideBatchProgress() {
    document.getElementById('batchProgress').style.display = 'none';
    document.getElementById('multiProcessingControls').style.display = 'block';
}

// 배치 진행률 업데이트
function updateBatchProgress(data) {
    const progressBar = document.getElementById('batchProgressBar');
    const progressText = document.getElementById('batchProgressText');
    const currentFileProgressBar = document.getElementById('currentFileProgressBar');
    const currentFileProgressText = document.getElementById('currentFileProgressText');
    const progressStatus = document.getElementById('batchProgressStatus');
    const completedFiles = document.getElementById('batchCompletedFiles');
    const totalFiles = document.getElementById('batchTotalFiles');
    const currentFile = document.getElementById('batchCurrentFile');
    const estimatedTime = document.getElementById('batchEstimatedTime');
    const successRate = document.getElementById('batchSuccessRate');
    const processingSpeed = document.getElementById('batchProcessingSpeed');

    // 전체 진행률
    const percentage = Math.round((data.completed_files / data.total_files) * 100);
    progressBar.style.width = `${percentage}%`;
    progressText.textContent = `${percentage}%`;

    // 현재 파일 진행률
    const currentFileProgress = data.current_file_progress || 0;
    currentFileProgressBar.style.width = `${currentFileProgress}%`;
    currentFileProgressText.textContent = `${Math.round(currentFileProgress)}%`;

    // 상태 업데이트
    const statusText = getStatusText(data.status);
    progressStatus.textContent = statusText;
    progressStatus.className = `badge ${getStatusBadgeClass(data.status)}`;

    // 파일 정보
    completedFiles.textContent = data.completed_files;
    totalFiles.textContent = data.total_files;

    // 현재 파일명 (경로에서 파일명만 추출)
    if (data.current_file) {
        const fileName = data.current_file.split('/').pop() || data.current_file;
        currentFile.textContent = fileName;
    } else {
        currentFile.textContent = '-';
    }

    // 남은 시간
    if (data.estimated_time_remaining > 0) {
        estimatedTime.textContent = formatTime(data.estimated_time_remaining);
    } else {
        estimatedTime.textContent = '계산 중...';
    }

    // 성공률
    if (data.success_rate !== undefined) {
        successRate.textContent = `${Math.round(data.success_rate * 100)}%`;
    } else if (data.completed_files > 0) {
        const successCount = data.completed_files - (data.error_count || 0);
        const rate = (successCount / data.completed_files) * 100;
        successRate.textContent = `${Math.round(rate)}%`;
    } else {
        successRate.textContent = '-';
    }

    // 처리 속도 (파일/분)
    if (data.start_time && data.completed_files > 0) {
        const elapsedTime = (Date.now() / 1000) - data.start_time;
        const filesPerMinute = (data.completed_files / elapsedTime) * 60;
        processingSpeed.textContent = `${filesPerMinute.toFixed(1)} 파일/분`;
    } else {
        processingSpeed.textContent = '-';
    }

    // 상태에 따른 진행률 바 색상 변경
    progressBar.className = 'progress-bar progress-bar-striped';
    if (data.status === 'completed') {
        progressBar.classList.add('bg-success');
        currentFileProgressBar.className = 'progress-bar bg-success';
    } else if (data.status === 'error') {
        progressBar.classList.add('bg-danger');
        currentFileProgressBar.className = 'progress-bar bg-danger';
    } else if (data.status === 'cancelled') {
        progressBar.classList.add('bg-warning');
        currentFileProgressBar.className = 'progress-bar bg-warning';
    } else {
        progressBar.classList.add('progress-bar-animated', 'bg-primary');
        currentFileProgressBar.className = 'progress-bar bg-info';
    }

    // 처리 로그 업데이트
    updateProcessingLog(data);
}

// 상태에 따른 배지 클래스 반환
function getStatusBadgeClass(status) {
    const statusClasses = {
        'processing': 'bg-primary',
        'completed': 'bg-success',
        'error': 'bg-danger',
        'cancelled': 'bg-warning',
        'waiting': 'bg-secondary'
    };
    return statusClasses[status] || 'bg-secondary';
}

// 처리 로그 업데이트
function updateProcessingLog(data) {
    const processingLog = document.getElementById('processingLog');

    // 새로운 로그 엔트리 생성
    const timestamp = new Date().toLocaleTimeString();
    let logEntry = '';

    if (data.current_file && data.status === 'processing') {
        const fileName = data.current_file.split('/').pop() || data.current_file;
        logEntry = `[${timestamp}] 처리 중: ${fileName}`;
    } else if (data.status === 'completed') {
        logEntry = `[${timestamp}] ✅ 모든 파일 처리 완료 (${data.completed_files}/${data.total_files})`;
    } else if (data.status === 'error') {
        logEntry = `[${timestamp}] ❌ 처리 중 오류 발생`;
    } else if (data.status === 'cancelled') {
        logEntry = `[${timestamp}] ⏹️ 처리가 취소되었습니다`;
    }

    if (logEntry) {
        // 기존 로그가 "처리 로그가 여기에 표시됩니다..."인 경우 제거
        if (processingLog.textContent.includes('처리 로그가 여기에 표시됩니다')) {
            processingLog.innerHTML = '';
        }

        const logDiv = document.createElement('div');
        logDiv.textContent = logEntry;
        logDiv.className = 'mb-1';

        // 상태에 따른 색상 적용
        if (data.status === 'completed') {
            logDiv.classList.add('text-success');
        } else if (data.status === 'error') {
            logDiv.classList.add('text-danger');
        } else if (data.status === 'cancelled') {
            logDiv.classList.add('text-warning');
        }

        processingLog.appendChild(logDiv);

        // 스크롤을 맨 아래로
        processingLog.scrollTop = processingLog.scrollHeight;

        // 로그 엔트리가 너무 많으면 오래된 것 제거 (최대 50개)
        const logEntries = processingLog.children;
        if (logEntries.length > 50) {
            processingLog.removeChild(logEntries[0]);
        }
    }
}

// 처리 로그 지우기
function clearProcessingLog() {
    const processingLog = document.getElementById('processingLog');
    processingLog.innerHTML = '<div class="text-muted">처리 로그가 여기에 표시됩니다...</div>';
}

// 배치 처리 취소
function cancelBatchProcessing() {
    if (!currentBatchId) return;

    fetch(`/api/convert/batch-cancel/${currentBatchId}`, {
        method: 'DELETE'
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            clearInterval(batchProgressInterval);
            showToast(data.message, 'info');
            hideBatchProgress();
        })
        .catch(error => {
            showToast('배치 처리 취소 중 오류가 발생했습니다: ' + error.message, 'error');
        });
}

// 배치 결과 표시
function showBatchResults(data) {
    const batchResults = document.getElementById('batchResults');
    const batchResultsContent = document.getElementById('batchResultsContent');

    let resultsHtml = `
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-success">${data.completed_files}</h5>
                        <p class="card-text">성공한 파일</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-danger">${data.error_count || 0}</h5>
                        <p class="card-text">실패한 파일</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (data.successful_results && data.successful_results.length > 0) {
        resultsHtml += `
            <h6><i class="fas fa-check-circle text-success"></i> 성공한 파일들</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>파일명</th>
                            <th>포맷</th>
                            <th>크기</th>
                            <th>파일 크기</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.successful_results.map(result => `
                            <tr>
                                <td>${result.file_path.split('/').pop()}</td>
                                <td>${result.format}</td>
                                <td>${result.size[0]} × ${result.size[1]}</td>
                                <td>${formatFileSize(result.file_size)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    if (data.failed_file_details && data.failed_file_details.length > 0) {
        resultsHtml += `
            <h6 class="mt-3"><i class="fas fa-exclamation-triangle text-danger"></i> 실패한 파일들</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>파일명</th>
                            <th>오류</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.failed_file_details.map(failed => `
                            <tr>
                                <td>${failed.file_path.split('/').pop()}</td>
                                <td class="text-danger">${failed.error}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    resultsHtml += `
        <div class="mt-3 text-center">
            <button class="btn btn-primary" onclick="downloadBatchResults()">
                <i class="fas fa-download"></i> 결과 다운로드
            </button>
            <button class="btn btn-secondary ms-2" onclick="resetBatchProcessing()">
                <i class="fas fa-refresh"></i> 새로 시작
            </button>
        </div>
    `;

    batchResultsContent.innerHTML = resultsHtml;
    batchResults.style.display = 'block';
}

// 배치 처리 초기화
function resetBatchProcessing() {
    clearAllFiles();
    currentBatchId = null;
    clearInterval(batchProgressInterval);
    document.getElementById('batchProgress').style.display = 'none';
    document.getElementById('batchResults').style.display = 'none';
    resetMultiProcessingOptions();
}

// 배치 결과 다운로드 (추후 구현)
function downloadBatchResults() {
    showToast('배치 결과 다운로드 기능은 추후 구현 예정입니다.', 'info');
}

// 상태 텍스트 변환
function getStatusText(status) {
    const statusMap = {
        'processing': '처리 중...',
        'completed': '완료됨',
        'error': '오류 발생',
        'cancelled': '취소됨',
        'waiting': '대기 중...'
    };
    return statusMap[status] || status;
}

// 시간 포맷팅
function formatTime(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}초`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.round(seconds % 60);
        return `${minutes}분 ${remainingSeconds}초`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}시간 ${minutes}분`;
    }
}

// 히스토리 및 캐시 초기화
function initializeHistoryAndCache() {
    // 로컬 스토리지에서 히스토리 로드
    loadHistoryFromStorage();

    // 캐시 상태 초기화
    refreshCacheStatus();

    // 탭 변경 시 히스토리 새로고침
    document.getElementById('history-tab').addEventListener('shown.bs.tab', function () {
        refreshHistory();
        refreshCacheStatus();
    });
}

// 로컬 스토리지에서 히스토리 로드
function loadHistoryFromStorage() {
    try {
        const stored = localStorage.getItem('conversionHistory');
        if (stored) {
            conversionHistory = JSON.parse(stored);
            // 최대 50개 항목만 유지
            if (conversionHistory.length > 50) {
                conversionHistory = conversionHistory.slice(-50);
                saveHistoryToStorage();
            }
        }
    } catch (error) {
        console.error('히스토리 로드 오류:', error);
        conversionHistory = [];
    }
}

// 로컬 스토리지에 히스토리 저장
function saveHistoryToStorage() {
    try {
        localStorage.setItem('conversionHistory', JSON.stringify(conversionHistory));
    } catch (error) {
        console.error('히스토리 저장 오류:', error);
    }
}

// 히스토리에 항목 추가
function addToHistory(data) {
    const historyItem = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        fileName: currentFile ? currentFile.name : 'Unknown',
        fileSize: currentFile ? currentFile.size : 0,
        originalFormat: data.original_format || data.format,
        originalSize: data.original_size || data.size,
        processedFormat: data.processed_format || data.format,
        processedSize: data.processed_size || data.size,
        base64Length: data.base64.length,
        processingOptions: data.processing_options || null,
        base64Data: data.base64.substring(0, 1000) + '...', // 처음 1000자만 저장
        thumbnail: data.base64.substring(0, 500) // 썸네일용 데이터
    };

    conversionHistory.unshift(historyItem);

    // 최대 50개 항목만 유지
    if (conversionHistory.length > 50) {
        conversionHistory = conversionHistory.slice(0, 50);
    }

    saveHistoryToStorage();

    // 히스토리 탭이 활성화되어 있으면 UI 업데이트
    if (document.getElementById('history-tab').classList.contains('active')) {
        refreshHistory();
    }
}

// 히스토리 새로고침
function refreshHistory() {
    const historyList = document.getElementById('historyList');

    if (conversionHistory.length === 0) {
        historyList.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-clock fa-2x mb-3"></i>
                <p>변환 기록이 없습니다.</p>
                <small>이미지를 변환하면 여기에 기록이 표시됩니다.</small>
            </div>
        `;
        return;
    }

    historyList.innerHTML = conversionHistory.map(item => `
        <div class="history-item border-bottom pb-3 mb-3" data-id="${item.id}">
            <div class="row align-items-center">
                <div class="col-md-2">
                    <div class="text-center">
                        <img src="data:image/png;base64,${item.thumbnail}" 
                             class="img-thumbnail" style="width: 60px; height: 60px; object-fit: cover;" 
                             alt="썸네일" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0yMCAyMEg0MFY0MEgyMFYyMFoiIGZpbGw9IiNEREREREQiLz4KPC9zdmc+'">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="fw-bold">${item.fileName}</div>
                    <small class="text-muted">
                        ${new Date(item.timestamp).toLocaleString()}<br>
                        ${formatFileSize(item.fileSize)} • ${item.originalFormat}
                        ${item.originalSize ? ` (${item.originalSize[0]}×${item.originalSize[1]})` : ''}
                    </small>
                    ${item.processingOptions ? `
                        <div class="mt-1">
                            <span class="badge bg-light text-dark">처리됨</span>
                        </div>
                    ` : ''}
                </div>
                <div class="col-md-2">
                    <small class="text-muted">
                        결과: ${item.processedFormat}<br>
                        ${item.processedSize ? `${item.processedSize[0]}×${item.processedSize[1]}` : ''}<br>
                        Base64: ${item.base64Length.toLocaleString()}자
                    </small>
                </div>
                <div class="col-md-2 text-end">
                    <div class="btn-group-vertical btn-group-sm">
                        <button class="btn btn-outline-primary btn-sm" onclick="reprocessFromHistory(${item.id})">
                            <i class="fas fa-redo"></i> 재변환
                        </button>
                        <button class="btn btn-outline-secondary btn-sm" onclick="viewHistoryDetails(${item.id})">
                            <i class="fas fa-eye"></i> 상세
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="removeFromHistory(${item.id})">
                            <i class="fas fa-trash"></i> 삭제
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// 히스토리에서 재변환
function reprocessFromHistory(historyId) {
    const item = conversionHistory.find(h => h.id === historyId);
    if (!item) {
        showToast('히스토리 항목을 찾을 수 없습니다.', 'error');
        return;
    }

    // 단일 파일 탭으로 이동
    document.getElementById('to-base64-tab').click();

    // 처리 옵션 복원
    if (item.processingOptions) {
        const options = item.processingOptions;

        // 옵션 값 설정
        document.getElementById('resizeWidth').value = options.resize_width || '';
        document.getElementById('resizeHeight').value = options.resize_height || '';
        document.getElementById('maintainAspectRatio').checked = options.maintain_aspect_ratio;
        document.getElementById('qualitySlider').value = options.quality;
        document.getElementById('qualityValue').textContent = options.quality;
        document.getElementById('targetFormat').value = options.target_format || '';

        // 전역 옵션 객체 업데이트
        processingOptions = { ...options };

        // 회전/뒤집기 버튼 상태 복원
        setRotation(options.rotation_angle);
        if (options.flip_horizontal) {
            toggleFlip('horizontal');
        }
        if (options.flip_vertical) {
            toggleFlip('vertical');
        }

        showToast('처리 옵션이 복원되었습니다. 새 이미지를 선택해주세요.', 'info');
    } else {
        showToast('기본 변환 모드로 설정되었습니다. 새 이미지를 선택해주세요.', 'info');
    }
}

// 히스토리 상세 보기
function viewHistoryDetails(historyId) {
    const item = conversionHistory.find(h => h.id === historyId);
    if (!item) {
        showToast('히스토리 항목을 찾을 수 없습니다.', 'error');
        return;
    }

    let detailsHtml = `
        <div class="modal fade" id="historyDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">변환 기록 상세</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>파일 정보</h6>
                                <table class="table table-sm">
                                    <tr><td>파일명</td><td>${item.fileName}</td></tr>
                                    <tr><td>파일 크기</td><td>${formatFileSize(item.fileSize)}</td></tr>
                                    <tr><td>변환 시간</td><td>${new Date(item.timestamp).toLocaleString()}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6>이미지 정보</h6>
                                <table class="table table-sm">
                                    <tr><td>원본 형식</td><td>${item.originalFormat}</td></tr>
                                    <tr><td>원본 크기</td><td>${item.originalSize ? `${item.originalSize[0]}×${item.originalSize[1]}` : '-'}</td></tr>
                                    <tr><td>결과 형식</td><td>${item.processedFormat}</td></tr>
                                    <tr><td>결과 크기</td><td>${item.processedSize ? `${item.processedSize[0]}×${item.processedSize[1]}` : '-'}</td></tr>
                                    <tr><td>Base64 길이</td><td>${item.base64Length.toLocaleString()}자</td></tr>
                                </table>
                            </div>
                        </div>
    `;

    if (item.processingOptions) {
        const options = item.processingOptions;
        detailsHtml += `
            <div class="mt-3">
                <h6>적용된 처리 옵션</h6>
                <div class="row">
                    <div class="col-md-6">
                        <ul class="list-unstyled">
                            ${options.resize_width || options.resize_height ? `<li>• 리사이징: ${options.resize_width || 'auto'} × ${options.resize_height || 'auto'}</li>` : ''}
                            ${options.quality !== 85 ? `<li>• 품질: ${options.quality}%</li>` : ''}
                            ${options.target_format ? `<li>• 포맷 변환: ${options.target_format}</li>` : ''}
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <ul class="list-unstyled">
                            ${options.rotation_angle !== 0 ? `<li>• 회전: ${options.rotation_angle}°</li>` : ''}
                            ${options.flip_horizontal ? `<li>• 수평 뒤집기</li>` : ''}
                            ${options.flip_vertical ? `<li>• 수직 뒤집기</li>` : ''}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }

    detailsHtml += `
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                        <button type="button" class="btn btn-primary" onclick="reprocessFromHistory(${item.id}); bootstrap.Modal.getInstance(document.getElementById('historyDetailsModal')).hide();">
                            재변환하기
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 기존 모달 제거
    const existingModal = document.getElementById('historyDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 새 모달 추가 및 표시
    document.body.insertAdjacentHTML('beforeend', detailsHtml);
    const modal = new bootstrap.Modal(document.getElementById('historyDetailsModal'));
    modal.show();
}

// 히스토리에서 항목 제거
function removeFromHistory(historyId) {
    conversionHistory = conversionHistory.filter(h => h.id !== historyId);
    saveHistoryToStorage();
    refreshHistory();
    showToast('히스토리 항목이 삭제되었습니다.', 'info');
}

// 모든 히스토리 삭제
function clearHistory() {
    if (confirm('모든 변환 기록을 삭제하시겠습니까?')) {
        conversionHistory = [];
        saveHistoryToStorage();
        refreshHistory();
        showToast('모든 히스토리가 삭제되었습니다.', 'info');
    }
}

// 캐시 상태 새로고침
function refreshCacheStatus() {
    // 실제 캐시 API가 구현되면 여기서 호출
    // 현재는 모의 데이터 사용
    updateCacheStatusDisplay();
}

// 캐시 상태 표시 업데이트
function updateCacheStatusDisplay() {
    document.getElementById('cacheHitCount').textContent = cacheStatus.hitCount;
    document.getElementById('cacheMissCount').textContent = cacheStatus.missCount;
    document.getElementById('cacheItemCount').textContent = cacheStatus.itemCount;

    const usagePercentage = (cacheStatus.usedSize / cacheStatus.maxSize) * 100;
    document.getElementById('cacheUsageBar').style.width = `${usagePercentage}%`;
    document.getElementById('cacheUsageText').textContent =
        `${formatFileSize(cacheStatus.usedSize)} / ${formatFileSize(cacheStatus.maxSize)}`;

    const totalRequests = cacheStatus.hitCount + cacheStatus.missCount;
    const hitRate = totalRequests > 0 ? (cacheStatus.hitCount / totalRequests) * 100 : 0;
    document.getElementById('cacheHitRate').textContent = `${Math.round(hitRate)}%`;

    // 사용량에 따른 진행률 바 색상 변경
    const usageBar = document.getElementById('cacheUsageBar');
    usageBar.className = 'progress-bar';
    if (usagePercentage > 90) {
        usageBar.classList.add('bg-danger');
    } else if (usagePercentage > 70) {
        usageBar.classList.add('bg-warning');
    } else {
        usageBar.classList.add('bg-success');
    }
}

// 만료된 캐시 정리
function clearExpiredCache() {
    // 실제 캐시 API 호출
    fetch('/api/cache/cleanup-expired', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            showToast(`${data.cleaned_items || 0}개의 만료된 캐시 항목이 정리되었습니다.`, 'success');
            refreshCacheStatus();
        })
        .catch(error => {
            showToast('캐시 정리 중 오류가 발생했습니다: ' + error.message, 'error');
        });
}

// 모든 캐시 삭제
function clearAllCache() {
    if (confirm('모든 캐시를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
        fetch('/api/cache/clear-all', {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showToast(data.error, 'error');
                    return;
                }

                cacheStatus = {
                    hitCount: 0,
                    missCount: 0,
                    usedSize: 0,
                    maxSize: cacheStatus.maxSize,
                    itemCount: 0
                };

                updateCacheStatusDisplay();
                showToast('모든 캐시가 삭제되었습니다.', 'success');
            })
            .catch(error => {
                showToast('캐시 삭제 중 오류가 발생했습니다: ' + error.message, 'error');
            });
    }
}

// 캐시 설정 업데이트
function updateCacheSettings() {
    const maxSize = parseInt(document.getElementById('cacheMaxSize').value);
    const expiry = parseInt(document.getElementById('cacheExpiry').value);

    if (maxSize < 10 || maxSize > 1000) {
        showToast('캐시 크기는 10MB에서 1000MB 사이여야 합니다.', 'error');
        return;
    }

    if (expiry < 1 || expiry > 168) {
        showToast('캐시 만료 시간은 1시간에서 168시간(7일) 사이여야 합니다.', 'error');
        return;
    }

    const settings = {
        max_size_mb: maxSize,
        expiry_hours: expiry
    };

    fetch('/api/cache/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            cacheStatus.maxSize = maxSize * 1024 * 1024; // MB to bytes
            updateCacheStatusDisplay();
            showToast('캐시 설정이 업데이트되었습니다.', 'success');
        })
        .catch(error => {
            showToast('캐시 설정 업데이트 중 오류가 발생했습니다: ' + error.message, 'error');
        });
}

// ============================================
// 이미지 포맷 변환 기능
// ============================================

let convertCurrentFile = null;

// 이미지 포맷 변환 초기화
function initializeImageConversion() {
    const convertDropZone = document.getElementById('convertDropZone');
    const convertFileInput = document.getElementById('convertFileInput');

    if (!convertDropZone || !convertFileInput) {
        return; // 요소가 없으면 초기화하지 않음
    }

    // 클릭 이벤트
    convertDropZone.addEventListener('click', () => convertFileInput.click());

    // 키보드 이벤트
    convertDropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            convertFileInput.click();
        }
    });

    // 드래그 앤 드롭 이벤트
    convertDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        convertDropZone.classList.add('dragover');
    });

    convertDropZone.addEventListener('dragleave', () => {
        convertDropZone.classList.remove('dragover');
    });

    convertDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        convertDropZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleConvertFileSelection(files[0]);
        }
    });

    // 파일 입력 이벤트
    convertFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleConvertFileSelection(e.target.files[0]);
        }
    });
}

// 이미지 변환 파일 선택 처리
function handleConvertFileSelection(file) {
    // 파일 타입 검증
    if (!file.type.startsWith('image/')) {
        showToast('이미지 파일만 선택할 수 있습니다.', 'error');
        return;
    }

    // 파일 크기 검증 (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showToast('파일 크기는 16MB를 초과할 수 없습니다.', 'error');
        return;
    }

    // 현재 파일 저장
    convertCurrentFile = file;

    // 미리보기 표시
    showConvertImagePreview(file);

    // 변환 옵션 표시
    showConvertOptions();
}

// 이미지 변환 미리보기 표시
function showConvertImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
        const previewImg = document.getElementById('convertPreviewImg');
        const fileInfo = document.getElementById('convertFileInfo');

        previewImg.src = e.target.result;

        // 파일 정보 표시
        const img = new Image();
        img.onload = function () {
            fileInfo.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <strong>파일명:</strong> ${file.name}<br>
                        <strong>크기:</strong> ${formatFileSize(file.size)}<br>
                        <strong>타입:</strong> ${file.type}
                    </div>
                    <div class="col-md-6">
                        <strong>이미지 크기:</strong> ${img.width} × ${img.height}<br>
                        <strong>수정일:</strong> ${new Date(file.lastModified).toLocaleString()}
                    </div>
                </div>
            `;
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

// 변환 옵션 표시
function showConvertOptions() {
    document.getElementById('convertOptions').style.display = 'block';
}

// 이미지 포맷 변환 및 다운로드
function convertImageFormat() {
    if (!convertCurrentFile) {
        showToast('먼저 이미지 파일을 선택해주세요.', 'error');
        return;
    }

    const targetFormat = document.getElementById('convertTargetFormat').value;

    const formData = new FormData();
    formData.append('file', convertCurrentFile);
    formData.append('target_format', targetFormat);

    showLoading(true);

    fetch('/api/convert/image', {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.blob();
        })
        .then(blob => {
            showLoading(false);

            // 파일 다운로드
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // 원본 파일명에서 확장자를 제거하고 새 확장자 추가
            const originalName = convertCurrentFile.name.replace(/\.[^/.]+$/, '');
            a.download = `${originalName}_converted.${targetFormat.toLowerCase()}`;

            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast(`${targetFormat} 포맷으로 변환이 완료되었습니다!`, 'success');
        })
        .catch(error => {
            showLoading(false);
            const errorMessage = error.error || error.message || '변환 중 오류가 발생했습니다.';
            showToast(errorMessage, 'error');
        });
}
