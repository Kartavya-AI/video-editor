import streamlit as st
import os
import time
import subprocess
import json
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="AI Video Editor",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Gemini client
@st.cache_resource
def initialize_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel('gemini-2.5-flash')

gemini_model = initialize_gemini()

# Create directories for file management
@st.cache_resource
def setup_directories():
    directories = {
        'input': 'streamlit_input',
        'output': 'streamlit_output', 
        'logs': 'streamlit_logs'
    }
    for name, path in directories.items():
        os.makedirs(path, exist_ok=True)
    return directories

directories = setup_directories()

# Title and description
st.title("🎬 AI Video Editor")
st.markdown("Upload a video and let AI analyze it to remove stutters, pauses, and improve the overall quality using FFmpeg.")

# Sidebar for settings
st.sidebar.header("⚙️ Settings")
st.sidebar.markdown("### Video Analysis Options")

analysis_options = st.sidebar.multiselect(
    "What should the AI look for?",
    ["Stutters or repeated words", "Long pauses", "Loading screens", "Background noise", "Dead air"],
    default=["Stutters or repeated words", "Long pauses", "Loading screens"]
)

# Main interface
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload Video")
    
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'mov', 'avi', 'mkv'],
        help="Upload a video file to analyze and edit"
    )
    
    if uploaded_file is not None:
        # Save uploaded file to input directory
        video_filename = f"temp_{uploaded_file.name}"
        video_path = os.path.join(directories['input'], video_filename)
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ Video uploaded: {uploaded_file.name}")
        st.success(f"📁 Saved to: {video_path}")
        st.video(video_path)
        
        # Video info
        st.subheader("📊 Video Information")
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
        st.write(f"**File size:** {file_size:.2f} MB")
        st.write(f"**File name:** {uploaded_file.name}")

with col2:
    st.header("🤖 AI Analysis & Editing")
    
    if uploaded_file is not None:
        if st.button("🔍 Analyze Video", type="primary", use_container_width=True):
            
            # Create containers for real-time updates
            status_container = st.container()
            progress_bar = st.progress(0)
            
            with status_container:
                st.info("🚀 Starting video analysis...")
                progress_bar.progress(10)
                
                try:
                    # Upload video to Gemini
                    st.info("📤 Uploading video to AI...")
                    video_file_obj = genai.upload_file(path=video_path)
                    progress_bar.progress(30)
                    
                    # Wait for processing
                    st.info("⏳ AI is processing video...")
                    while video_file_obj.state.name == "PROCESSING":
                        time.sleep(5)
                        video_file_obj = genai.get_file(video_file_obj.name)
                    
                    if video_file_obj.state.name == "FAILED":
                        st.error("❌ Failed to process video")
                    else:
                        progress_bar.progress(60)
                        
                        # Create prompt based on selected options
                        issues_text = ", ".join([f"- {option}" for option in analysis_options])
                        
                        # Normalize the path for Windows
                        normalized_video_path = os.path.abspath(video_path).replace('\\', '/')
                        
                        prompt = f"""
                        Analyze this video and provide only a valid PowerShell FFmpeg command without any non real filters to improve it or remove any lags or loading times.
                        
                        The input video file name is: {uploaded_file.name}
                        The input file path will be: {video_path}
                        Use the full path in your command for the input file.
                        
                        Look for these specific issues:
                        {issues_text}
                        
                        Return ONLY the valid FFmpeg command, nothing else. No JSON, no explanations, just the command.
                        Remember to use the actual input file path in your command.
                        
                        """
                        
                        st.info("🧠 AI is analyzing video content...")
                        response = gemini_model.generate_content([video_file_obj, prompt])
                        ffmpeg_command = response.text.strip()
                        
                        # Clean up command
                        if ffmpeg_command.startswith('```'):
                            lines = ffmpeg_command.split('\n')
                            ffmpeg_command = '\n'.join([line for line in lines if not line.startswith('```')])
                            ffmpeg_command = ffmpeg_command.strip()
                        
                        progress_bar.progress(80)
                        
                        # Store results in session state
                        st.session_state.ffmpeg_command = ffmpeg_command
                        st.session_state.video_path = video_path
                        st.session_state.original_filename = uploaded_file.name
                        
                        # Clean up uploaded file from Gemini
                        genai.delete_file(video_file_obj.name)
                        progress_bar.progress(100)
                        
                        st.success("✅ Video analysis complete!")
                        
                except Exception as e:
                    st.error(f"❌ Error during analysis: {str(e)}")

# Display results if analysis is complete
if hasattr(st.session_state, 'ffmpeg_command'):
    st.header("📋 Analysis Results")
    
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.subheader("🛠️ Generated FFmpeg Command")
        st.code(st.session_state.ffmpeg_command, language="bash")
        
        # Allow user to edit the command
        edited_command = st.text_area(
            "Edit command if needed:",
            value=st.session_state.ffmpeg_command,
            height=100,
            help="You can modify the FFmpeg command before execution"
        )
        
        # Show alternative simple commands
        with st.expander("🔧 Alternative Simple Commands", expanded=False):
            safe_input_path = f'"{st.session_state.video_path}"'
            safe_output_path = f'"{os.path.join(directories["output"], f"edited_{st.session_state.original_filename}")}"'
            
            st.markdown("**If the AI command has issues, try these simple alternatives:**")
            
            # Simple copy command
            simple_copy = f"ffmpeg -y -i {safe_input_path} -c copy {safe_output_path}"
            st.code(simple_copy, language="bash")
            if st.button("Use Simple Copy", key="simple_copy"):
                st.session_state.ffmpeg_command = simple_copy
                st.rerun()
            
            # Re-encode with compression
            simple_reencode = f"ffmpeg -y -i {safe_input_path} -c:v libx264 -crf 23 -preset medium {safe_output_path}"
            st.code(simple_reencode, language="bash")
            if st.button("Use Re-encode", key="simple_reencode"):
                st.session_state.ffmpeg_command = simple_reencode
                st.rerun()
            
            # Trim first 30 seconds
            simple_trim = f"ffmpeg -y -i {safe_input_path} -ss 0 -t 30 -c copy {safe_output_path}"
            st.code(simple_trim, language="bash")
            if st.button("Use Trim (30s)", key="simple_trim"):
                st.session_state.ffmpeg_command = simple_trim
                st.rerun()
        
        if st.button("💾 Save Command", use_container_width=True):
            # Save command to file in logs directory
            command_filename = f"command_{Path(st.session_state.original_filename).stem}.txt"
            command_path = os.path.join(directories['logs'], command_filename)
            with open(command_path, 'w') as f:
                f.write(f"FFmpeg command for {st.session_state.original_filename}:\n")
                f.write(edited_command)
            st.success(f"Command saved to {command_path}")
    
    with col4:
        st.subheader("▶️ Execute Editing")
        
        if st.button("🎬 Process Video", type="primary", use_container_width=True):
            execution_container = st.container()
            exec_progress = st.progress(0)
            
            with execution_container:
                try:
                    # Create output path in output directory
                    output_filename = f"edited_{st.session_state.original_filename}"
                    output_path = os.path.join(directories['output'], output_filename)
                    
                    # Prepare command with proper paths
                    edited_command_clean = edited_command
                    
                    # Debug: Show original command
                    st.info(f"🔍 Original AI command: {edited_command}")
                    
                    # Normalize paths for better matching
                    input_path_normalized = os.path.abspath(st.session_state.video_path)
                    input_path_forward_slash = input_path_normalized.replace('\\', '/')
                    input_path_quoted = f'"{input_path_normalized}"'
                    input_path_quoted_forward = f'"{input_path_forward_slash}"'
                    
                    # Replace common input patterns - only replace if the pattern is definitely wrong
                    input_patterns = [
                        # First check for any nested directory issues and fix them
                        (f"streamlit_input\\temp_streamlit_input\\", "streamlit_input\\"),
                        (f"streamlit_input/temp_streamlit_input/", "streamlit_input/"),
                        # Direct filename patterns (only if they appear without proper path)
                        (f" {st.session_state.original_filename} ", f" {input_path_quoted} "),
                        (f'"{st.session_state.original_filename}"', input_path_quoted),
                        # Generic input patterns
                        ("input.mp4", input_path_quoted),
                        ('"input.mp4"', input_path_quoted),
                    ]
                    
                    # Apply input path replacements only if needed
                    path_replacement_applied = False
                    for old_pattern, new_pattern in input_patterns:
                        if old_pattern in edited_command_clean:
                            edited_command_clean = edited_command_clean.replace(old_pattern, new_pattern)
                            st.info(f"🔧 Replaced input pattern: `{old_pattern}` → `{new_pattern}`")
                            path_replacement_applied = True
                            break
                    
                    # If no replacement was made and the command doesn't contain the correct path, 
                    # check if we need to replace the entire input path
                    if not path_replacement_applied:
                        if input_path_quoted not in edited_command_clean and input_path_quoted_forward not in edited_command_clean:
                            # Only replace if the current path in the command doesn't exist
                            if st.session_state.video_path not in edited_command_clean:
                                st.warning("⚠️ Command may need manual path correction")
                            else:
                                st.info("✅ Command appears to use correct paths")
                    
                    # Replace output patterns
                    output_path_quoted = f'"{output_path}"'
                    output_patterns = [
                        ("output.mp4", output_path_quoted),
                        ('"output.mp4"', output_path_quoted),
                        (f"edited_{st.session_state.original_filename}", output_path_quoted),
                        (f'"edited_{st.session_state.original_filename}"', output_path_quoted),
                        (output_filename, output_path_quoted),
                        (f'"{output_filename}"', output_path_quoted)
                    ]
                    
                    # Apply output path replacements
                    output_replaced = False
                    for old_pattern, new_pattern in output_patterns:
                        if old_pattern in edited_command_clean:
                            edited_command_clean = edited_command_clean.replace(old_pattern, new_pattern)
                            st.info(f"🔧 Replaced output pattern: `{old_pattern}` → `{new_pattern}`")
                            output_replaced = True
                            break
                    
                    # If no output was found, add it at the end
                    if not output_replaced:
                        edited_command_clean = edited_command_clean.rstrip() + f' {output_path_quoted}'
                        st.info(f"🔧 Added output path at end: `{output_path_quoted}`")
                    
                    # Add -y flag to overwrite output files without asking
                    if "-y" not in edited_command_clean:
                        edited_command_clean = edited_command_clean.replace("ffmpeg", "ffmpeg -y")
                    
                    final_command = edited_command_clean
                    
                    st.info(f"⚙️ Executing FFmpeg command...")
                    st.code(final_command, language="bash")
                    
                    # Debug information
                    with st.expander("🔍 Debug Information"):
                        st.write(f"**Input video path:** `{st.session_state.video_path}`")
                        st.write(f"**Input path exists:** {os.path.exists(st.session_state.video_path)}")
                        st.write(f"**Input path (absolute):** `{os.path.abspath(st.session_state.video_path)}`")
                        st.write(f"**Output video path:** `{output_path}`")
                        st.write(f"**Original filename:** `{st.session_state.original_filename}`")
                        st.write(f"**Original command:** `{edited_command}`")
                        st.write(f"**Final command:** `{final_command}`")
                        if os.path.exists(st.session_state.video_path):
                            st.write(f"**File size:** {os.path.getsize(st.session_state.video_path)} bytes")
                        else:
                            st.error(f"❌ **Input file does not exist!** Path: {st.session_state.video_path}")
                            # Try to find the actual file
                            input_dir = directories['input']
                            if os.path.exists(input_dir):
                                files_in_input = os.listdir(input_dir)
                                st.write(f"**Files in input directory:** {files_in_input}")
                    
                    exec_progress.progress(20)
                    
                    # Validate command before execution
                    command_valid = True
                    validation_errors = []
                    
                    if not final_command.strip().startswith("ffmpeg"):
                        validation_errors.append("Command must start with 'ffmpeg'")
                        command_valid = False
                    
                    # Check if input file exists
                    if not os.path.exists(st.session_state.video_path):
                        validation_errors.append(f"Input file not found: {st.session_state.video_path}")
                        command_valid = False
                    
                    # Check if the command contains the correct input path
                    if input_path_quoted not in final_command and input_path_quoted_forward not in final_command:
                        validation_errors.append("Command may not contain the correct input path")
                        st.warning("⚠️ Warning: The command may not reference the correct input file path")
                    
                    # Show validation errors
                    if validation_errors:
                        for error in validation_errors:
                            st.error(f"❌ Validation Error: {error}")
                    
                    if command_valid:
                        # Execute command with better error handling
                        result = subprocess.run(
                            final_command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            cwd=os.getcwd(),
                            timeout=300  # 5 minute timeout
                        )
                        
                        exec_progress.progress(80)
                        
                        # Show detailed command output
                        if result.stdout:
                            st.text_area("FFmpeg Output (STDOUT):", result.stdout, height=100)
                        
                        if result.stderr:
                            st.text_area("FFmpeg Messages (STDERR):", result.stderr, height=150)
                        
                        if result.returncode == 0:
                            exec_progress.progress(100)
                            st.success("✅ Video processing completed successfully!")
                            
                            # Display processed video
                            if os.path.exists(output_path):
                                st.subheader("🎉 Processed Video")
                                st.video(output_path)
                                
                                # Download button
                                with open(output_path, "rb") as file:
                                    st.download_button(
                                        label="📥 Download Processed Video",
                                        data=file.read(),
                                        file_name=output_filename,
                                        mime="video/mp4",
                                        use_container_width=True
                                    )
                                
                                # File size comparison
                                original_size = os.path.getsize(st.session_state.video_path) / (1024 * 1024)
                                processed_size = os.path.getsize(output_path) / (1024 * 1024)
                                size_reduction = ((original_size - processed_size) / original_size) * 100
                                
                                col5, col6, col7 = st.columns(3)
                                with col5:
                                    st.metric("Original Size", f"{original_size:.2f} MB")
                                with col6:
                                    st.metric("Processed Size", f"{processed_size:.2f} MB")
                                with col7:
                                    st.metric("Size Reduction", f"{size_reduction:.1f}%")
                            else:
                                st.warning("⚠️ Output file was not created. Check the command and error messages above.")
                            
                            # Save execution log
                            log_filename = f"execution_log_{Path(st.session_state.original_filename).stem}.txt"
                            log_path = os.path.join(directories['logs'], log_filename)
                            with open(log_path, 'w') as f:
                                f.write(f"Execution log for {st.session_state.original_filename}:\n")
                                f.write(f"Input path: {st.session_state.video_path}\n")
                                f.write(f"Output path: {output_path}\n")
                                f.write(f"Command: {final_command}\n")
                                f.write(f"Return code: {result.returncode}\n")
                                f.write(f"STDOUT:\n{result.stdout}\n")
                                f.write(f"STDERR:\n{result.stderr}\n")
                            
                        else:
                            st.error(f"❌ FFmpeg command failed with return code: {result.returncode}")
                            
                            # Provide specific error analysis
                            error_msg = result.stderr.lower()
                            if "no such file or directory" in error_msg:
                                st.error("💡 **Issue**: Input file not found. Check file path.")
                            elif "invalid argument" in error_msg:
                                st.error("💡 **Issue**: Invalid FFmpeg arguments. Check command syntax.")
                            elif "permission denied" in error_msg:
                                st.error("💡 **Issue**: Permission denied. Check file permissions.")
                            elif "filtergraph" in error_msg:
                                st.error("💡 **Issue**: Filter graph error. The video filter syntax may be incorrect.")
                                st.info("🔧 **Suggestion**: Try a simpler command like: `ffmpeg -i input.mp4 -ss 0 -t 30 -c copy output.mp4`")
                            elif "codec" in error_msg:
                                st.error("💡 **Issue**: Codec error. The video format may not be supported.")
                            else:
                                st.error("💡 **Issue**: Unknown FFmpeg error. Check the error messages above.")
                            
                            # Suggest a simple fallback command
                            st.info("🔧 **Try this simple command instead:**")
                            simple_command = f'ffmpeg -y -i "{st.session_state.video_path}" -ss 0 -t 30 -c copy "{output_path}"'
                            st.code(simple_command, language="bash")
                            
                            if st.button("🚀 Try Simple Command", key="simple_cmd"):
                                # Execute simple fallback command
                                simple_result = subprocess.run(
                                    simple_command,
                                    shell=True,
                                    capture_output=True,
                                    text=True,
                                    cwd=os.getcwd()
                                )
                                
                                if simple_result.returncode == 0:
                                    st.success("✅ Simple command worked! Video processed successfully.")
                                    if os.path.exists(output_path):
                                        st.video(output_path)
                                else:
                                    st.error(f"❌ Simple command also failed: {simple_result.stderr}")
                            
                            # Save error log
                            error_filename = f"error_log_{Path(st.session_state.original_filename).stem}.txt"
                            error_path = os.path.join(directories['logs'], error_filename)
                            with open(error_path, 'w') as f:
                                f.write(f"Error log for {st.session_state.original_filename}:\n")
                                f.write(f"Input path: {st.session_state.video_path}\n")
                                f.write(f"Output path: {output_path}\n")
                                f.write(f"Command: {final_command}\n")
                                f.write(f"Return code: {result.returncode}\n")
                                f.write(f"STDOUT:\n{result.stdout}\n")
                                f.write(f"STDERR:\n{result.stderr}\n")
                            
                            st.write(f"📝 Error details saved to {error_path}")
                        
                except subprocess.TimeoutExpired:
                    st.error("❌ Command timed out after 5 minutes. The video may be too large or the command too complex.")
                except Exception as e:
                    st.error(f"❌ Error during execution: {str(e)}")
                    
                    # Save exception log
                    exception_filename = f"exception_log_{Path(st.session_state.original_filename).stem}.txt"
                    exception_path = os.path.join(directories['logs'], exception_filename)
                    with open(exception_path, 'w') as f:
                        f.write(f"Exception log for {st.session_state.original_filename}:\n")
                        f.write(f"Input path: {st.session_state.video_path}\n")
                        f.write(f"Command: {final_command}\n")
                        f.write(f"Exception: {str(e)}\n")
                    
                    st.write(f"📝 Exception details saved to {exception_path}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>🎬 AI Video Editor | Powered by Gemini AI & FFmpeg</p>
        <p><small>Upload videos, analyze with AI, and automatically remove stutters, pauses, and improve quality</small></p>
    </div>
    """,
    unsafe_allow_html=True
)

# Cleanup temporary files on app restart
if st.button("🧹 Clean Temporary Files", help="Remove temporary files created during processing"):
    temp_files = []
    for directory in directories.values():
        if os.path.exists(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                temp_files.append(file_path)
                try:
                    os.remove(file_path)
                except:
                    pass
    st.success(f"Cleaned {len(temp_files)} temporary files from all directories")
    
    # Show directory structure info
    st.info(f"""
    **Directory Structure:**
    - `{directories['input']}/`: Uploaded videos
    - `{directories['output']}/`: Processed videos  
    - `{directories['logs']}/`: Commands and logs
    """)
