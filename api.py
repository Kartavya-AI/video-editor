from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import os
import subprocess
import time
import tempfile
import shutil
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Video Editor API", version="1.0.0")

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# Create directories
os.makedirs("temp_videos", exist_ok=True)
os.makedirs("output_videos", exist_ok=True)

@app.post("/edit-video/")
async def edit_video(file: UploadFile = File(...)):
    """
    Upload a video file and get an edited version with stutters and pauses removed
    """
    if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        raise HTTPException(status_code=400, detail="Only video files are supported")
    
    # Save uploaded file temporarily
    temp_input_path = f"temp_videos/{file.filename}"
    with open(temp_input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Upload to Gemini for analysis
        video_file_obj = genai.upload_file(path=temp_input_path)
        
        # Wait for processing
        while video_file_obj.state.name == "PROCESSING":
            time.sleep(5)
            video_file_obj = genai.get_file(video_file_obj.name)
        
        if video_file_obj.state.name == "FAILED":
            raise HTTPException(status_code=500, detail="Failed to process video")
        
        # Create prompt for Gemini
        prompt = f"""
        Analyze this video and provide only an FFmpeg command to improve it by removing stutters, long pauses, and loading times.
        
        The input video file path is: {temp_input_path}
        
        Look for issues like:
        - Stutters or repeated words
        - Long waiting time for loading screens
        - Long pauses or dead air
        - Sections that should be cut out
        
        Return ONLY the FFmpeg command, nothing else. Use the exact input path provided.
        
        Example format: ffmpeg -i "{temp_input_path}" -ss 5 -t 30 "output.mp4"
        """
        
        # Get FFmpeg command from Gemini
        response = gemini_model.generate_content([video_file_obj, prompt])
        ffmpeg_command = response.text.strip()
        
        # Clean up command formatting
        if ffmpeg_command.startswith('```'):
            lines = ffmpeg_command.split('\n')
            ffmpeg_command = '\n'.join([line for line in lines if not line.startswith('```')])
            ffmpeg_command = ffmpeg_command.strip()
        
        # Prepare output path
        output_filename = f"edited_{file.filename}"
        output_path = f"output_videos/{output_filename}"
        
        # Modify command to use correct paths
        edited_command = ffmpeg_command
        
        # Replace input patterns
        input_patterns = [
            ("input.mp4", f'"{temp_input_path}"'),
            (file.filename, f'"{temp_input_path}"'),
            (f'"{file.filename}"', f'"{temp_input_path}"')
        ]
        
        for old_pattern, new_pattern in input_patterns:
            if old_pattern in edited_command:
                edited_command = edited_command.replace(old_pattern, new_pattern)
                break
        
        # Replace output patterns
        output_patterns = [
            ("output.mp4", f'"{output_path}"'),
            (f"edited_{file.filename}", f'"{output_path}"'),
            (output_filename, f'"{output_path}"')
        ]
        
        for old_pattern, new_pattern in output_patterns:
            if old_pattern in edited_command:
                edited_command = edited_command.replace(old_pattern, new_pattern)
                break
        
        # Add output path if not specified
        if not any(pattern in edited_command for pattern, _ in output_patterns):
            edited_command = edited_command + f' "{output_path}"'
        
        # Add -y flag to overwrite files
        if "-y" not in edited_command:
            edited_command = edited_command.replace("ffmpeg", "ffmpeg -y")
        
        # Execute FFmpeg command
        result = subprocess.run(
            edited_command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"FFmpeg failed: {result.stderr}"
            )
        
        # Clean up Gemini file
        genai.delete_file(video_file_obj.name)
        
        # Return the edited video
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type='video/mp4'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp input file
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

@app.get("/")
async def root():
    return {"message": "Video Editor API - Upload videos to /edit-video/"}