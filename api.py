from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import time
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

@app.post("/analyze-video/")
async def analyze_video(file: UploadFile = File(...)):
    """
    Upload a video file and get an FFmpeg command to edit it with stutters and pauses removed
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
        Format the output path as: edited_{file.filename}
        
        Example format: ffmpeg -i "{temp_input_path}" -ss 5 -t 30 "edited_{file.filename}"
        """
        
        # Get FFmpeg command from Gemini
        response = gemini_model.generate_content([video_file_obj, prompt])
        ffmpeg_command = response.text.strip()
        
        # Clean up command formatting
        if ffmpeg_command.startswith('```'):
            lines = ffmpeg_command.split('\n')
            ffmpeg_command = '\n'.join([line for line in lines if not line.startswith('```')])
            ffmpeg_command = ffmpeg_command.strip()
        
        # Prepare response data
        output_filename = f"edited_{file.filename}"
        
        # Clean up Gemini file
        genai.delete_file(video_file_obj.name)
        
        # Return the FFmpeg command and metadata
        return JSONResponse({
            "status": "success",
            "original_filename": file.filename,
            "suggested_output_filename": output_filename,
            "ffmpeg_command": ffmpeg_command,
            "instructions": [
                "1. Save the above FFmpeg command to a file or copy it",
                "2. Make sure FFmpeg is installed on your system",
                "3. Run the command in your terminal/command prompt",
                f"4. The edited video will be saved as '{output_filename}'"
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp input file
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

@app.post("/get-command-only/")
async def get_command_only(file: UploadFile = File(...)):
    """
    Alternative endpoint that returns just the FFmpeg command as plain text
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
        Format the output path as: edited_{file.filename}
        
        Example format: ffmpeg -i "{temp_input_path}" -ss 5 -t 30 "edited_{file.filename}"
        """
        
        # Get FFmpeg command from Gemini
        response = gemini_model.generate_content([video_file_obj, prompt])
        ffmpeg_command = response.text.strip()
        
        # Clean up command formatting
        if ffmpeg_command.startswith('```'):
            lines = ffmpeg_command.split('\n')
            ffmpeg_command = '\n'.join([line for line in lines if not line.startswith('```')])
            ffmpeg_command = ffmpeg_command.strip()
        
        # Clean up Gemini file
        genai.delete_file(video_file_obj.name)
        
        # Return just the command as plain text
        return ffmpeg_command
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp input file
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

@app.get("/")
async def root():
    return {
        "message": "Video Editor API - Get FFmpeg commands for video editing",
        "endpoints": {
            "/analyze-video/": "Upload video and get detailed response with FFmpeg command",
            "/get-command-only/": "Upload video and get just the FFmpeg command as plain text"
        }
    }
