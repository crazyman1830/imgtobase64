// 전역 변수
let currentBase64Data = '';

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeDropZone();
    initializeFileInput();
});

// 드롭존 초기화
function initializeDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // 클릭 이벤트
    dropZone.addEventListener('click', () => fileInput.click());

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

    // 미리보기 표시
    showImagePreview(file);
    
    // Base64 변환
    convertToBase64(file);
}

// 이미지 미리보기 표시
function showImagePreview(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
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

// Base64 변환
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

// Base64 결과 표시
function displayBase64Result(data) {
    const base64Result = document.getElementById('base64Result');
    const base64Output = document.getElementById('base64Output');
    
    base64Output.textContent = data.base64;
    base64Result.style.display = 'block';
    
    // 파일 정보 업데이트
    const fileInfo = document.getElementById('fileInfo');
    fileInfo.innerHTML += `
        <div class="mt-2 pt-2 border-top">
            <div class="row">
                <div class="col-md-6">
                    <strong>변환된 형식:</strong> ${data.format}<br>
                    <strong>이미지 크기:</strong> ${data.size[0]} × ${data.size[1]}
                </div>
                <div class="col-md-6">
                    <strong>Base64 길이:</strong> ${data.base64.length.toLocaleString()} 문자
                </div>
            </div>
        </div>
    `;
}

// Base64 복사
function copyBase64() {
    if (!currentBase64Data) {
        showToast('복사할 Base64 데이터가 없습니다.', 'error');
        return;
    }
    
    navigator.clipboard.writeText(currentBase64Data)
        .then(() => showToast('Base64 데이터가 클립보드에 복사되었습니다!', 'success'))
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