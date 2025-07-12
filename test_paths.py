#!/usr/bin/env python3
"""
Test script to verify directory structure and file paths
"""

import os

# Test directory creation
directories = {
    'input': 'streamlit_input',
    'output': 'streamlit_output', 
    'logs': 'streamlit_logs'
}

print("🔍 Testing directory structure...")

# Create directories
for name, path in directories.items():
    os.makedirs(path, exist_ok=True)
    print(f"✅ Created/verified directory: {path}")

# Test file path creation
test_filename = "Excel.mp4"
video_filename = f"temp_{test_filename}"
video_path = os.path.join(directories['input'], video_filename)

print(f"\n📁 Testing file paths:")
print(f"Original filename: {test_filename}")
print(f"Temporary filename: {video_filename}")
print(f"Full video path: {video_path}")
print(f"Absolute path: {os.path.abspath(video_path)}")

# Test output path
output_filename = f"edited_{test_filename}"
output_path = os.path.join(directories['output'], output_filename)
print(f"Output path: {output_path}")
print(f"Absolute output path: {os.path.abspath(output_path)}")

# Test log path
log_filename = f"command_{test_filename.replace('.mp4', '')}.txt"
log_path = os.path.join(directories['logs'], log_filename)
print(f"Log path: {log_path}")

print(f"\n🧪 Path construction test:")
print(f"Input directory exists: {os.path.exists(directories['input'])}")
print(f"Output directory exists: {os.path.exists(directories['output'])}")
print(f"Logs directory exists: {os.path.exists(directories['logs'])}")

# Create a dummy file to test
dummy_content = "This is a test file"
with open(video_path, 'w') as f:
    f.write(dummy_content)

print(f"\n✅ Test file created: {video_path}")
print(f"File exists: {os.path.exists(video_path)}")
print(f"File size: {os.path.getsize(video_path)} bytes")

# Test FFmpeg command construction
test_command = f'ffmpeg -i "{video_path}" -ss 0 -t 30 "{output_path}"'
print(f"\n🎬 Sample FFmpeg command:")
print(test_command)

# Cleanup
os.remove(video_path)
print(f"\n🧹 Cleaned up test file")

print("\n✅ Path testing completed successfully!")
