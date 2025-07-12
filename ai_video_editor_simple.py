import os
import ffmpeg
import json
import time
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
# Initialize Gemini client
genai.configure(api_key="AIzaSyCHD6V5571LaYBE4A0VPlMg_RNfVRxY4Pk")
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# Create directories for file management
input_dir = "input_videos"
output_dir = "output_videos"
logs_dir = "logs"

for directory in [input_dir, output_dir, logs_dir]:
    os.makedirs(directory, exist_ok=True)
    print(f"Created/verified directory: {directory}")

# Define the input video files (place these in the input_videos folder)
video_files = [
   "excel.mp4",  # Example video file
    # Add more video files as needed
]

print("Starting video analysis process...")
print(f"Analyzing {len(video_files)} video files")

# Analyze each video with Gemini
for video_file in video_files:
    input_path = os.path.join(input_dir, video_file)
    
    if not os.path.exists(input_path):
        print(f"Warning: Video file '{input_path}' not found. Skipping...")
        print(f"Please place '{video_file}' in the '{input_dir}' folder.")
        continue
    
    print(f"\nAnalyzing video: {input_path}")
    
    try:
        # Upload video to Gemini
        video_file_obj = genai.upload_file(path=input_path)
        
        # Wait for processing
        while video_file_obj.state.name == "PROCESSING":
            print("Processing video...")
            time.sleep(10)
            video_file_obj = genai.get_file(video_file_obj.name)
        
        if video_file_obj.state.name == "FAILED":
            print(f"Failed to process video: {video_file}")
            continue
        
        # Create prompt for Gemini
        prompt = f"""
        Analyze this video and provide only a PowerShell FFmpeg command to improve it by removing stutters, long pauses, and loading times.
        
        The input video file name is: {video_file}
        The input file path will be: {input_path}
        Use the full path in your command for the input file.
        
        Look for issues like:
        - Stutters or repeated words
        - Long waiting time for some output/loading screens
        - Long pauses or dead air
        - Sections that should be cut out
        
        Return ONLY the FFmpeg command, nothing else. No JSON, no explanations, just the command.
        Remember to use the actual input file path in your command.
        
        Example format: ffmpeg -i "{input_path}" -ss 5 -t 30 "output_path.mp4"
        """
        
        # Send to Gemini for analysis
        response = gemini_model.generate_content([video_file_obj, prompt])
        response_text = response.text.strip()
        
        print(f"\nGemini command for {video_file}:")
        print(response_text)
        
        # Use the response directly as the FFmpeg command
        ffmpeg_command = response_text
        
        # Clean up any potential formatting
        if ffmpeg_command.startswith('```'):
            # Remove code block formatting if present
            lines = ffmpeg_command.split('\n')
            ffmpeg_command = '\n'.join([line for line in lines if not line.startswith('```')])
            ffmpeg_command = ffmpeg_command.strip()
        
        print(f"\nFFmpeg Command to execute:")
        print(ffmpeg_command)
        
        # Save the command to a file
        command_filename = f"command_{video_file.replace('.mp4', '')}.txt"
        command_path = os.path.join(logs_dir, command_filename)
        with open(command_path, 'w') as f:
            f.write(f"FFmpeg command for {video_file}:\n")
            f.write(ffmpeg_command)
        
        print(f"Command saved to: {command_path}")
        
        # Execute the FFmpeg command
        print(f"\nExecuting FFmpeg command...")
        try:
            # Create output path
            output_filename = f"edited_{video_file}"
            output_path = os.path.join(output_dir, output_filename)
            
            # Modify the command to use the actual input file and create proper output
            # Replace generic paths with actual paths
            edited_command = ffmpeg_command
            
            # Replace common input patterns
            patterns_to_replace = [
                ("input.mp4", f'"{input_path}"'),
                (video_file, f'"{input_path}"'),
                (f'"{video_file}"', f'"{input_path}"'),
                (input_path, f'"{input_path}"')  # Ensure quotes
            ]
            
            for old_pattern, new_pattern in patterns_to_replace:
                if old_pattern in edited_command:
                    edited_command = edited_command.replace(old_pattern, new_pattern)
                    break
            
            # Replace output patterns
            output_patterns = [
                ("output.mp4", f'"{output_path}"'),
                (f"edited_{video_file}", f'"{output_path}"'),
                (output_filename, f'"{output_path}"')
            ]
            
            for old_pattern, new_pattern in output_patterns:
                if old_pattern in edited_command:
                    edited_command = edited_command.replace(old_pattern, new_pattern)
                    break
            
            # If no output specified, add it at the end
            if not any(pattern in edited_command for pattern, _ in output_patterns):
                edited_command = edited_command + f' "{output_path}"'
            
            # Add -y flag to overwrite output files without asking
            if "-y" not in edited_command:
                edited_command = edited_command.replace("ffmpeg", "ffmpeg -y")
            
            print(f"Executing: {edited_command}")
            
            # Run the command using subprocess
            result = subprocess.run(
                edited_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                print(f"SUCCESS: FFmpeg command executed successfully!")
                print(f"OUTPUT: {output_path}")
                
                # Save execution log
                log_filename = f"execution_log_{video_file.replace('.mp4', '')}.txt"
                log_path = os.path.join(logs_dir, log_filename)
                with open(log_path, 'w') as f:
                    f.write(f"Execution log for {video_file}:\n")
                    f.write(f"Input path: {input_path}\n")
                    f.write(f"Output path: {output_path}\n")
                    f.write(f"Command: {edited_command}\n")
                    f.write(f"Return code: {result.returncode}\n")
                    f.write(f"STDOUT:\n{result.stdout}\n")
                    f.write(f"STDERR:\n{result.stderr}\n")
                
                print(f"LOG: Execution log saved to: {log_path}")
                
            else:
                print(f"ERROR: FFmpeg command failed with return code: {result.returncode}")
                print(f"Error output: {result.stderr}")
                
                # Save error log
                error_filename = f"error_log_{video_file.replace('.mp4', '')}.txt"
                error_path = os.path.join(logs_dir, error_filename)
                with open(error_path, 'w') as f:
                    f.write(f"Error log for {video_file}:\n")
                    f.write(f"Input path: {input_path}\n")
                    f.write(f"Output path: {output_path}\n")
                    f.write(f"Command: {edited_command}\n")
                    f.write(f"Return code: {result.returncode}\n")
                    f.write(f"STDOUT:\n{result.stdout}\n")
                    f.write(f"STDERR:\n{result.stderr}\n")
                
                print(f"LOG: Error log saved to: {error_path}")
                
        except Exception as exec_error:
            print(f"ERROR: Error executing command: {exec_error}")
            error_filename = f"execution_error_{video_file.replace('.mp4', '')}.txt"
            error_path = os.path.join(logs_dir, error_filename)
            with open(error_path, 'w') as f:
                f.write(f"Execution error for {video_file}:\n")
                f.write(f"Input path: {input_path}\n")
                f.write(f"Command: {edited_command}\n")
                f.write(f"Error: {str(exec_error)}\n")
            print(f"LOG: Error details saved to: {error_path}")
        
        # Clean up uploaded file
        genai.delete_file(video_file_obj.name)
        
    except Exception as e:
        print(f"Error analyzing video {video_file}: {e}")

print("\nVideo analysis and editing process completed!")
print("Check the generated files:")
print(f"- {logs_dir}/command_*.txt: FFmpeg commands")
print(f"- {output_dir}/edited_*.mp4: Processed video files") 
print(f"- {logs_dir}/execution_log_*.txt: Execution logs")
print(f"- {logs_dir}/error_log_*.txt: Error logs (if any)")
print(f"\nDirectory structure:")
print(f"- {input_dir}/: Place your input videos here")
print(f"- {output_dir}/: Processed videos will be saved here")
print(f"- {logs_dir}/: All logs and commands will be saved here")
