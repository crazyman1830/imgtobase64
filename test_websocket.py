#!/usr/bin/env python3
"""
WebSocket functionality test for the image converter

This script tests the WebSocket implementation for real-time
batch processing updates.
"""
import socketio
import time
import threading
import requests
import tempfile
import os
from PIL import Image
import io

# Create a test client
sio = socketio.Client()

# Event handlers
@sio.event
def connect():
    print("✅ Connected to WebSocket server")

@sio.event
def disconnect():
    print("❌ Disconnected from WebSocket server")

@sio.event
def connected(data):
    print(f"📡 Server says: {data['message']}")

@sio.event
def batch_progress(data):
    print(f"📊 Progress: {data['progress_percentage']:.1f}% - {data['current_file']} (ETA: {data['estimated_time_remaining']:.1f}s)")

@sio.event
def file_processed(data):
    status = "✅" if data['success'] else "❌"
    print(f"{status} File processed: {os.path.basename(data['file_path'])}")
    if not data['success']:
        print(f"   Error: {data['error_message']}")

@sio.event
def batch_completed(data):
    print(f"🎉 Batch completed! {data['successful_files']}/{data['total_files']} files successful")

@sio.event
def batch_cancelled(data):
    print(f"🚫 Batch cancelled: {data['message']}")

@sio.event
def batch_error(data):
    print(f"💥 Batch error: {data['error']}")

def create_test_image(filename, size=(100, 100), color='red'):
    """Create a test image file"""
    image = Image.new('RGB', size, color)
    image.save(filename, 'JPEG')
    return filename

def test_websocket_batch_processing():
    """Test WebSocket batch processing functionality"""
    print("🧪 Testing WebSocket batch processing...")
    
    try:
        # Connect to WebSocket
        print("🔌 Connecting to WebSocket server...")
        sio.connect('http://localhost:5000')
        
        # Create test images
        test_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            create_test_image(temp_file.name, size=(200 + i*50, 200 + i*50), 
                            color=['red', 'green', 'blue'][i])
            test_files.append(temp_file.name)
        
        print(f"📁 Created {len(test_files)} test images")
        
        # Start batch processing via REST API
        print("🚀 Starting batch processing...")
        files_data = []
        for file_path in test_files:
            with open(file_path, 'rb') as f:
                files_data.append(('files', (os.path.basename(file_path), f.read(), 'image/jpeg')))
        
        # Processing options
        options = {
            'resize_width': 150,
            'quality': 80,
            'target_format': 'JPEG'
        }
        
        response = requests.post(
            'http://localhost:5000/api/convert/batch-start',
            files=files_data,
            data={'options': str(options).replace("'", '"')}
        )
        
        if response.status_code == 200:
            result = response.json()
            queue_id = result['queue_id']
            print(f"📋 Batch started with queue ID: {queue_id}")
            
            # Join the queue room for real-time updates
            sio.emit('join_queue', {'queue_id': queue_id})
            
            # Wait for completion
            print("⏳ Waiting for batch completion...")
            time.sleep(10)  # Wait for processing to complete
            
            # Check final status
            status_response = requests.get(f'http://localhost:5000/api/convert/batch-progress/{queue_id}')
            if status_response.status_code == 200:
                final_status = status_response.json()
                print(f"📈 Final status: {final_status['status']}")
                print(f"📊 Completed: {final_status['completed_files']}/{final_status['total_files']}")
            
            # Leave the queue room
            sio.emit('leave_queue', {'queue_id': queue_id})
            
        else:
            print(f"❌ Failed to start batch processing: {response.text}")
        
        # Clean up test files
        for file_path in test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"💥 Test failed: {e}")
    finally:
        # Disconnect
        sio.disconnect()

def test_websocket_events():
    """Test individual WebSocket events"""
    print("🧪 Testing WebSocket events...")
    
    try:
        # Connect to WebSocket
        sio.connect('http://localhost:5000')
        
        # Test get active queues
        print("📋 Requesting active queues...")
        sio.emit('get_active_queues')
        
        time.sleep(2)
        
        print("✅ WebSocket events test completed!")
        
    except Exception as e:
        print(f"💥 WebSocket events test failed: {e}")
    finally:
        sio.disconnect()

if __name__ == '__main__':
    print("🚀 Starting WebSocket tests...")
    print("Make sure the Flask-SocketIO server is running on localhost:5000")
    
    try:
        # Test basic WebSocket events
        test_websocket_events()
        
        time.sleep(2)
        
        # Test batch processing with WebSocket
        test_websocket_batch_processing()
        
        print("🎉 All tests completed!")
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"💥 Test suite failed: {e}")