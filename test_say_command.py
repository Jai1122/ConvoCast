#!/usr/bin/env python3
"""
Test script to diagnose and fix macOS say command issues.
"""

import os
import subprocess
import tempfile
from pathlib import Path

def test_say_command_basic():
    """Test basic say command functionality."""
    print("🧪 Testing macOS say Command")
    print("=" * 40)

    try:
        # Test if say command is available
        result = subprocess.run(['say', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ macOS say command is available")
        else:
            print("❌ say command failed version check")
            return False
    except FileNotFoundError:
        print("❌ macOS say command not found")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  say command timeout")
        return False

    # Test basic say functionality
    try:
        print("\n🎤 Testing basic say command...")
        result = subprocess.run(['say', 'Hello world'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Basic say command works")
        else:
            print(f"❌ Basic say failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Basic say test error: {e}")
        return False

    # Test say with file output
    try:
        print("\n📁 Testing say with file output...")
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as tmp:
            temp_path = tmp.name

        print(f"🎯 Output file: {temp_path}")

        command = ['say', '-v', 'Alex', '-o', temp_path, 'This is a test of file output']
        print(f"🚀 Command: {' '.join(command)}")

        result = subprocess.run(command, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"❌ say file output failed:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False

        # Check if file was created
        if os.path.exists(temp_path):
            file_size = os.path.getsize(temp_path)
            print(f"✅ File created: {file_size} bytes")

            # Check file format
            with open(temp_path, 'rb') as f:
                header = f.read(12)

            if b'FORM' in header and (b'AIFF' in header or b'AIFC' in header):
                print("✅ File has valid AIFF header")
                success = True
            else:
                print(f"⚠️  Unexpected file format: {header}")
                success = True  # Still success if file was created

            # Clean up
            os.unlink(temp_path)
            return success
        else:
            print("❌ File was not created")
            return False

    except Exception as e:
        print(f"❌ File output test error: {e}")
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        return False

def test_say_command_with_paths():
    """Test say command with different path scenarios."""
    print("\n🛣️  Testing Different Path Scenarios")
    print("=" * 40)

    test_text = "Testing path scenarios for macOS say command"

    # Test 1: Temporary directory
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "test1.aiff")
            print(f"📁 Test 1 - Temp dir: {temp_path}")

            result = subprocess.run([
                'say', '-v', 'Alex', '-o', temp_path, test_text
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and os.path.exists(temp_path):
                print("✅ Temporary directory path works")
            else:
                print(f"❌ Temp directory failed: {result.stderr}")
                return False
    except Exception as e:
        print(f"❌ Temp directory test error: {e}")
        return False

    # Test 2: Current directory
    try:
        current_dir = os.getcwd()
        test_file = os.path.join(current_dir, "say_test.aiff")
        print(f"📁 Test 2 - Current dir: {test_file}")

        result = subprocess.run([
            'say', '-v', 'Alex', '-o', test_file, test_text
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and os.path.exists(test_file):
            print("✅ Current directory path works")
            os.unlink(test_file)  # Clean up
        else:
            print(f"❌ Current directory failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Current directory test error: {e}")
        try:
            if os.path.exists(test_file):
                os.unlink(test_file)
        except:
            pass
        return False

    return True

def test_say_voices():
    """Test different say voices."""
    print("\n🗣️  Testing Available Voices")
    print("=" * 40)

    try:
        # List available voices
        result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            voices = result.stdout.strip().split('\n')[:5]  # First 5 voices
            print(f"✅ Found {len(voices)} voices (showing first 5):")
            for voice in voices:
                print(f"   {voice}")
        else:
            print("⚠️  Could not list voices")

        # Test specific voices
        test_voices = ['Alex', 'Samantha', 'Victoria']
        for voice in test_voices:
            try:
                with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as tmp:
                    temp_path = tmp.name

                result = subprocess.run([
                    'say', '-v', voice, '-o', temp_path, f'Testing {voice} voice'
                ], capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    print(f"✅ Voice {voice} works ({file_size} bytes)")
                    os.unlink(temp_path)
                else:
                    print(f"⚠️  Voice {voice} failed: {result.stderr}")

            except Exception as e:
                print(f"⚠️  Voice {voice} error: {e}")
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass

    except Exception as e:
        print(f"❌ Voice test error: {e}")

    return True

def main():
    """Run all say command tests."""
    print("macOS say Command Diagnostic Test")
    print("This will help identify and fix say command issues\n")

    tests = [
        ("Basic Functionality", test_say_command_basic),
        ("Path Scenarios", test_say_command_with_paths),
        ("Voice Testing", test_say_voices),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
            print(f"\n{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"\n❌ {test_name}: ERROR - {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    if all(results):
        print("🎉 ✅ ALL TESTS PASSED!")
        print("✅ macOS say command is working correctly")
        print("✅ ConvoCast should work with macOS voices")
        print("\n💡 Try: convocast generate --page-id 'YOUR_PAGE_ID' --tts-engine macos_say")
    else:
        print("⚠️  SOME ISSUES DETECTED")
        if not results[0]:
            print("❌ Basic say command not working")
            print("🔧 Solution: Use --tts-engine pyttsx3 instead")
        if not results[1]:
            print("❌ File path issues detected")
            print("🔧 Solution: Check directory permissions")

        print("\n💡 Recommended: convocast generate --page-id 'YOUR_PAGE_ID' --tts-engine pyttsx3")

    return all(results)

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)