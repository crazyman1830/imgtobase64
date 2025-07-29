#!/usr/bin/env python3
"""
Simple test script to verify the new API endpoints are working.
"""
import requests
import json
import os
from PIL import Image
import io
import base64

def create_test_image():
    """Create a simple test image for testing."""
    # Create a simple 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

def test_advanced_endpoint():
    """Test the /api/convert/to-base64-advanced endpoint."""
    print("Testing /api/convert/to-base64-advanced endpoint...")
    
    # Create test image
    test_image = create_test_image()
    
    # Prepare request data
    files = {'file': ('test.png', test_image, 'image/png')}
    options = {
        'resize_width': 50,
        'resize_height': 50,
        'maintain_aspect_ratio': True,
        'quality': 90,
        'target_format': 'JPEG',
        'rotation_angle': 90,
        'flip_horizontal': False,
        'flip_vertical': False
    }
    data = {'options': json.dumps(options)}
    
    try:
        response = requests.post('http://localhost:5000/api/convert/to-base64-advanced', 
                               files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Advanced endpoint test passed")
            print(f"  - Original size: {result.get('original_size')}")
            print(f"  - Processed size: {result.get('processed_size')}")
            print(f"  - Format: {result.get('processed_format')}")
            return True
        else:
            print(f"✗ Advanced endpoint test failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Advanced endpoint test error: {e}")
        return False

def test_batch_endpoints():
    """Test the batch processing endpoints."""
    print("\nTesting batch processing endpoints...")
    
    # Create multiple test images
    test_images = []
    for i in range(3):
        img = Image.new('RGB', (100, 100), color=['red', 'green', 'blue'][i])
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        test_images.append(('files', (f'test{i}.png', img_bytes, 'image/png')))
    
    # Test batch start
    options = {
        'resize_width': 50,
        'quality': 85,
        'target_format': 'JPEG'
    }
    data = {'options': json.dumps(options)}
    
    try:
        response = requests.post('http://localhost:5000/api/convert/batch-start',
                               files=test_images, data=data)
        
        if response.status_code == 200:
            result = response.json()
            queue_id = result.get('queue_id')
            print("✓ Batch start test passed")
            print(f"  - Queue ID: {queue_id}")
            print(f"  - Total files: {result.get('total_files')}")
            
            # Test progress endpoint
            import time
            time.sleep(1)  # Give it a moment to process
            
            progress_response = requests.get(f'http://localhost:5000/api/convert/batch-progress/{queue_id}')
            
            if progress_response.status_code == 200:
                progress_result = progress_response.json()
                print("✓ Batch progress test passed")
                print(f"  - Status: {progress_result.get('status')}")
                print(f"  - Progress: {progress_result.get('progress_percentage'):.1f}%")
                print(f"  - Completed: {progress_result.get('completed_files')}/{progress_result.get('total_files')}")
                return True
            else:
                print(f"✗ Batch progress test failed: {progress_response.status_code}")
                return False
        else:
            print(f"✗ Batch start test failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Batch endpoints test error: {e}")
        return False

if __name__ == '__main__':
    print("API Endpoint Tests")
    print("=" * 50)
    print("Make sure the Flask app is running on localhost:5000")
    print("You can start it with: python -m src.web.web_app")
    print()
    
    # Test endpoints
    advanced_ok = test_advanced_endpoint()
    batch_ok = test_batch_endpoints()
    
    print("\n" + "=" * 50)
    if advanced_ok and batch_ok:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")