"""
CLI Integration Tests for the refactored image converter.

This test suite verifies that the CLI interface works correctly with
the refactored architecture and maintains all existing functionality.

Requirements: 1.1, 1.2
"""
import sys
import os
import tempfile
import subprocess
import json
from pathlib import Path
from PIL import Image

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestCLIIntegration:
    """Test CLI integration with the refactored system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_files = []
        self.test_dirs = []
        self.main_script = str(Path(__file__).parent.parent.parent / 'main.py')
    
    def teardown_method(self):
        """Clean up test files."""
        for file_path in self.test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        
        for dir_path in self.test_dirs:
            try:
                import shutil
                shutil.rmtree(dir_path)
            except:
                pass
    
    def create_test_image(self, format='PNG', size=(50, 50)) -> str:
        """Create a test image file."""
        image = Image.new('RGB', size, color='blue')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format.lower()}')
        image.save(temp_file.name, format)
        temp_file.close()
        self.test_files.append(temp_file.name)
        return temp_file.name
    
    def create_test_directory(self) -> str:
        """Create a directory with test images."""
        temp_dir = tempfile.mkdtemp()
        self.test_dirs.append(temp_dir)
        
        # Create multiple test images
        formats = ['PNG', 'JPEG', 'GIF']
        for i, fmt in enumerate(formats):
            colors = ['red', 'green', 'blue']
            image = Image.new('RGB', (30 + i*10, 30 + i*10), color=colors[i % len(colors)])
            file_path = os.path.join(temp_dir, f'image_{i}.{fmt.lower()}')
            
            if fmt == 'JPEG':
                image.save(file_path, fmt, quality=90)
            else:
                image.save(file_path, fmt)
        
        return temp_dir
    
    def run_cli_command(self, args: list) -> tuple:
        """Run CLI command and return result."""
        cmd = [sys.executable, self.main_script] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
    
    def test_cli_single_file_conversion(self):
        """Test CLI single file conversion."""
        print("🧪 Testing CLI Single File Conversion")
        print("=" * 50)
        
        # Create test image
        test_image = self.create_test_image()
        
        # Test conversion to stdout
        returncode, stdout, stderr = self.run_cli_command([test_image])
        
        print(f"   Return code: {returncode}")
        print(f"   Stdout length: {len(stdout)}")
        print(f"   Stderr: {stderr}")
        
        assert returncode == 0, f"CLI failed with stderr: {stderr}"
        assert 'data:image/' in stdout, "Output should contain data URI"
        assert 'base64,' in stdout, "Output should contain base64 data"
        
        print("   ✅ Single file conversion successful!")
    
    def test_cli_single_file_with_output(self):
        """Test CLI single file conversion with output file."""
        print("\n🧪 Testing CLI Single File with Output File")
        print("=" * 50)
        
        # Create test image and output file
        test_image = self.create_test_image()
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        output_file.close()
        self.test_files.append(output_file.name)
        
        # Test conversion with output file
        returncode, stdout, stderr = self.run_cli_command([
            test_image, '-o', output_file.name, '-f'
        ])
        
        print(f"   Return code: {returncode}")
        print(f"   Stderr: {stderr}")
        
        assert returncode == 0, f"CLI failed with stderr: {stderr}"
        assert os.path.exists(output_file.name), "Output file should be created"
        
        # Verify output file content
        with open(output_file.name, 'r') as f:
            content = f.read()
            assert 'data:image/' in content, "Output file should contain data URI"
            assert 'base64,' in content, "Output file should contain base64 data"
        
        print("   ✅ Single file with output successful!")
    
    def test_cli_verbose_mode(self):
        """Test CLI verbose mode."""
        print("\n🧪 Testing CLI Verbose Mode")
        print("=" * 50)
        
        # Create test image
        test_image = self.create_test_image()
        
        # Test with verbose flag
        returncode, stdout, stderr = self.run_cli_command([test_image, '-v'])
        
        print(f"   Return code: {returncode}")
        print(f"   Stdout contains processing info: {'Processing file:' in stdout}")
        print(f"   Stderr: {stderr}")
        
        assert returncode == 0, f"CLI failed with stderr: {stderr}"
        assert 'Processing file:' in stdout, "Verbose mode should show processing info"
        
        print("   ✅ Verbose mode successful!")
    
    def test_cli_directory_processing(self):
        """Test CLI directory processing."""
        print("\n🧪 Testing CLI Directory Processing")
        print("=" * 50)
        
        # Create test directory with images
        test_dir = self.create_test_directory()
        
        # Test directory processing
        returncode, stdout, stderr = self.run_cli_command([test_dir, '-v'])
        
        print(f"   Return code: {returncode}")
        print(f"   Stdout contains batch info: {'Batch processing completed:' in stdout}")
        print(f"   Stderr: {stderr}")
        
        assert returncode == 0, f"CLI failed with stderr: {stderr}"
        assert 'Batch processing completed:' in stdout, "Should show batch completion"
        assert 'Successful:' in stdout, "Should show success count"
        
        print("   ✅ Directory processing successful!")
    
    def test_cli_directory_with_output(self):
        """Test CLI directory processing with output file."""
        print("\n🧪 Testing CLI Directory with Output File")
        print("=" * 50)
        
        # Create test directory and output file
        test_dir = self.create_test_directory()
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        output_file.close()
        self.test_files.append(output_file.name)
        
        # Test directory processing with output
        returncode, stdout, stderr = self.run_cli_command([
            test_dir, '-o', output_file.name, '-f', '-v'
        ])
        
        print(f"   Return code: {returncode}")
        print(f"   Output file exists: {os.path.exists(output_file.name)}")
        print(f"   Stderr: {stderr}")
        
        assert returncode == 0, f"CLI failed with stderr: {stderr}"
        assert os.path.exists(output_file.name), "Output file should be created"
        
        # Verify output file contains multiple conversions
        with open(output_file.name, 'r') as f:
            content = f.read()
            file_count = content.count('File:')
            assert file_count >= 2, f"Should contain multiple files, found {file_count}"
        
        print("   ✅ Directory with output successful!")
    
    def test_cli_error_handling(self):
        """Test CLI error handling."""
        print("\n🧪 Testing CLI Error Handling")
        print("=" * 50)
        
        # Test with non-existent file
        returncode, stdout, stderr = self.run_cli_command(['/non/existent/file.jpg'])
        
        print(f"   Return code: {returncode}")
        print(f"   Error in stderr: {'Error:' in stderr}")
        print(f"   Stderr: {stderr[:100]}...")
        
        assert returncode != 0, "Should fail with non-existent file"
        assert 'Error:' in stderr, "Should show error message"
        
        print("   ✅ Error handling successful!")
    
    def test_cli_help_and_version(self):
        """Test CLI help and version options."""
        print("\n🧪 Testing CLI Help and Version")
        print("=" * 50)
        
        # Test help
        returncode, stdout, stderr = self.run_cli_command(['--help'])
        print(f"   Help return code: {returncode}")
        print(f"   Help shows usage: {'usage:' in stdout.lower()}")
        
        # Help should exit with 0 and show usage
        assert returncode == 0, "Help should exit successfully"
        assert 'usage:' in stdout.lower(), "Help should show usage"
        
        # Test version
        returncode, stdout, stderr = self.run_cli_command(['--version'])
        print(f"   Version return code: {returncode}")
        print(f"   Version shows number: {any(c.isdigit() for c in stdout)}")
        
        # Version should exit with 0 and show version number
        assert returncode == 0, "Version should exit successfully"
        assert any(c.isdigit() for c in stdout), "Version should show version number"
        
        print("   ✅ Help and version successful!")
    
    def test_cli_force_overwrite(self):
        """Test CLI force overwrite functionality."""
        print("\n🧪 Testing CLI Force Overwrite")
        print("=" * 50)
        
        # Create test image and output file
        test_image = self.create_test_image()
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        output_file.write(b'existing content')
        output_file.close()
        self.test_files.append(output_file.name)
        
        # Test without force flag (should handle existing file gracefully)
        returncode1, stdout1, stderr1 = self.run_cli_command([
            test_image, '-o', output_file.name
        ])
        
        # Test with force flag
        returncode2, stdout2, stderr2 = self.run_cli_command([
            test_image, '-o', output_file.name, '-f'
        ])
        
        print(f"   Without force return code: {returncode1}")
        print(f"   With force return code: {returncode2}")
        
        # With force flag should succeed
        assert returncode2 == 0, f"Force overwrite failed: {stderr2}"
        
        # Verify file was overwritten
        with open(output_file.name, 'r') as f:
            content = f.read()
            assert 'data:image/' in content, "File should be overwritten with base64 data"
        
        print("   ✅ Force overwrite successful!")


def run_cli_integration_tests():
    """Run all CLI integration tests."""
    print("🚀 Starting CLI Integration Tests")
    print("=" * 60)
    
    test_instance = TestCLIIntegration()
    test_methods = [
        test_instance.test_cli_single_file_conversion,
        test_instance.test_cli_single_file_with_output,
        test_instance.test_cli_verbose_mode,
        test_instance.test_cli_directory_processing,
        test_instance.test_cli_directory_with_output,
        test_instance.test_cli_error_handling,
        test_instance.test_cli_help_and_version,
        test_instance.test_cli_force_overwrite
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            test_instance.teardown_method()
            passed += 1
        except Exception as e:
            print(f"   ❌ Test failed: {str(e)}")
            test_instance.teardown_method()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 CLI Integration Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 All CLI integration tests passed!")
        print("✅ CLI interface works correctly with refactored architecture")
    else:
        print("⚠️  Some CLI integration tests failed")
        print("🔍 Please review the test output above for details")
    
    return failed == 0


if __name__ == '__main__':
    success = run_cli_integration_tests()
    sys.exit(0 if success else 1)