import unittest
import os
from unittest.mock import patch
from src.core.converter import ImageConverter
from src.models.models import PermissionError

class TestImageConverter(unittest.TestCase):
    def setUp(self):
        self.converter = ImageConverter()
        self.test_dir = 'test_images'
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        for file in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, file))
        os.rmdir(self.test_dir)

    def test_permission_error(self):
        file_path = os.path.join(self.test_dir, 'test.jpg')
        with open(file_path, 'w') as f:
            f.write('test')
        os.chmod(file_path, 0o000)

        result = self.converter.convert_to_base64(file_path)
        self.assertFalse(result.success)
        self.assertIn("파일에 접근할 권한이 없습니다", result.error_message)

if __name__ == '__main__':
    unittest.main()