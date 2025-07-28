import os
import streamlit as st
import tempfile
import pandas as pd
import time
import base64
from pathlib import Path
from datetime import datetime
from utils.video_processor import process_video_with_history
from utils.result_manager import (create_result_directory, get_all_result_dirs, 
                                save_metadata, save_final_report, get_result_info,
                                load_metadata, load_report)
from utils.file_upload import ChunkedFileUploader, StreamedFileHandler, format_file_size
import config

# Set page configuration
st.set_page_config(
    page_title="AI Work Inspector",
    page_icon="🎥",
    layout="wide"
)

# Load custom CSS
def load_css():
    css_file = os.path.join(os.path.dirname(__file__), "css/style.css")
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Function to create a base64 encoded version of a video file for embedding
def get_video_base64(video_path):
    with open(video_path, "rb") as video_file:
        return base64.b64encode(video_file.read()).decode()

# Function to display video content
def display_video(video_path):
    st.video(str(video_path))

# Initialize app state
if 'current_result_dir' not in st.session_state:
    st.session_state.current_result_dir = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results_base_path' not in st.session_state:
    st.session_state.results_base_path = config.RESULTS_BASE_DIR
if 'file_uploader' not in st.session_state:
    st.session_state.file_uploader = ChunkedFileUploader(chunk_size=config.CHUNK_SIZE_MB * 1024 * 1024)
if 'uploaded_video_path' not in st.session_state:
    st.session_state.uploaded_video_path = None

# Ensure the results directory exists
if not os.path.exists(st.session_state.results_base_path):
    os.makedirs(st.session_state.results_base_path)

# Load CSS
load_css()

# App Title
st.markdown("<h1 class='page-title'>AI Work Inspector</h1>", unsafe_allow_html=True)

# Sidebar for configuration and result selection
with st.sidebar:
    st.header("Configuration")
    
    # Parameters input
    st.subheader("Analysis Parameters")
    with st.container(border=True):
        interval = st.slider("Frame Interval (seconds)", min_value=1, max_value=10, value=config.DEFAULT_FRAME_INTERVAL)
        chunk_size = st.slider("Frames per Chunk", min_value=5, max_value=config.MAX_FRAMES_PER_CHUNK, value=config.DEFAULT_CHUNK_SIZE)
        task_name = st.text_input("Task Name", "battery exchange")
    
    # Custom prompts section
    st.subheader("Custom Prompts (Optional)")
    with st.container(border=True):
        with st.expander("Frame Analysis Prompt"):
            custom_analysis_prompt = st.text_area(
                "Custom system prompt for frame analysis",
                placeholder="Leave empty to use default prompt...",
                height=100,
                help="Override the default system prompt used for analyzing video frames"
            )
        
        with st.expander("Report Generation Prompt"):
            custom_report_prompt = st.text_area(
                "Custom system prompt for report generation", 
                placeholder="Leave empty to use default prompt...",
                height=100,
                help="Override the default system prompt used for generating the final report"
            )
        
    # Video upload
    st.subheader("Upload Video")
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Choose a video file", 
            type=config.SUPPORTED_VIDEO_FORMATS,
            help=f"Supported formats: {', '.join(config.SUPPORTED_VIDEO_FORMATS).upper()}. Maximum size: {config.MAX_UPLOAD_SIZE_GB}GB."
        )
        
        # Display file info if file is uploaded
        if uploaded_file is not None:
            file_size = uploaded_file.size if hasattr(uploaded_file, 'size') else 0
            st.info(f"**File:** {uploaded_file.name}")
            st.info(f"**Size:** {format_file_size(file_size)}")
            
            # Check file size limit
            max_size_bytes = config.MAX_UPLOAD_SIZE_GB * 1024 * 1024 * 1024
            if file_size > max_size_bytes:
                st.error(config.ERROR_MESSAGES['file_too_large'])
                st.stop()
            
            # Show warning for large files
            if file_size > config.LARGE_FILE_WARNING_SIZE_MB * 1024 * 1024:
                st.warning("⚠️ Large file detected. Upload may take several minutes.")
        
        if uploaded_file is not None and not st.session_state.processing:
            if st.button("Process Video", type="primary"):
                try:
                    # Create a new result directory
                    result_dir = create_result_directory(st.session_state.results_base_path)
                    st.session_state.current_result_dir = result_dir
                    st.session_state.processing = True
                    
                    # Display processing message
                    st.toast("Video processing started!")
                    
                    with st.spinner("Uploading and processing video..."):
                        # Create temporary file using chunked upload
                        st.write("🔄 Creating temporary file...")
                        video_path = st.session_state.file_uploader.create_temporary_file(uploaded_file)
                        
                        if video_path is None:
                            st.error(config.ERROR_MESSAGES['temp_file_creation_failed'])
                            st.session_state.processing = False
                            st.stop()
                        
                        st.session_state.uploaded_video_path = video_path
                        
                        # Save the original video in the result directory using streamed copy
                        st.write("💾 Saving video to result directory...")
                        video_save_path = os.path.join(result_dir, uploaded_file.name)
                        
                        if not StreamedFileHandler.copy_file_with_progress(video_path, video_save_path):
                            st.error(config.ERROR_MESSAGES['file_copy_failed'])
                            # Clean up temporary file
                            if os.path.exists(video_path):
                                os.unlink(video_path)
                            st.session_state.processing = False
                            st.stop()
                        
                        st.write("🎬 Processing video frames...")
                        # Process the video with custom prompts
                        metadata = process_video_with_history(
                            video_path=video_path,
                            output_dir=os.path.join(result_dir, "frames"),
                            interval=interval,
                            chunk_size=chunk_size,
                            task_name=task_name,
                            custom_analysis_prompt=custom_analysis_prompt.strip() if custom_analysis_prompt.strip() else None,
                        )
                        
                        st.write("📊 Generating analysis report...")
                        # Save the metadata and generate a report
                        save_metadata(metadata, result_dir, uploaded_file.name)
                        save_final_report(metadata, result_dir, uploaded_file.name, task_name, custom_report_prompt.strip() if custom_report_prompt.strip() else None)
                        
                        # Clean up temporary file
                        if os.path.exists(video_path):
                            os.unlink(video_path)
                        st.session_state.uploaded_video_path = None
                        
                        st.session_state.processing = False
                        st.success("✅ Processing complete!")
                        
                        # Rerun the app to update the results list
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")
                    # Clean up temporary file on error
                    if 'uploaded_video_path' in st.session_state and st.session_state.uploaded_video_path:
                        if os.path.exists(st.session_state.uploaded_video_path):
                            os.unlink(st.session_state.uploaded_video_path)
                        st.session_state.uploaded_video_path = None
                    st.session_state.processing = False
    
    # Result selection
    st.subheader("Results History")
    result_dirs = get_all_result_dirs(st.session_state.results_base_path)
    
    if result_dirs:
        with st.container(border=True):
            for result_dir in result_dirs:
                result_info = get_result_info(result_dir)
                if result_info["video_name"]:
                    timestamp_formatted = result_info["timestamp"].replace("_", " ")
                    if st.button(f"{result_info['video_name']} - {timestamp_formatted}", key=result_dir):
                        st.session_state.current_result_dir = result_dir
                        st.rerun()
    else:
        st.info("No results found. Process a video to get started.")

# Main content area
if st.session_state.processing:
    st.markdown("<div class='processing-status'>Processing video... Please wait.</div>", unsafe_allow_html=True)
    
    # Show current processing step
    if st.session_state.uploaded_video_path:
        st.info("📁 Temporary file created successfully")
    
    # Add cancel button for processing
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Cancel Processing", type="secondary"):
            # Clean up temporary file
            if st.session_state.uploaded_video_path and os.path.exists(st.session_state.uploaded_video_path):
                os.unlink(st.session_state.uploaded_video_path)
                st.session_state.uploaded_video_path = None
            st.session_state.processing = False
            st.warning("Processing cancelled.")
            st.rerun()

elif st.session_state.current_result_dir:
    # Display selected result
    result_info = get_result_info(st.session_state.current_result_dir)
    
    st.header(f"Analysis Results: {result_info['video_name']}")
    st.subheader(f"Processed on: {result_info['timestamp'].replace('_', ' ')}")
    
    # Container for video and report
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Video Preview")
        video_path = os.path.join(st.session_state.current_result_dir, result_info["video_name"])
        if os.path.exists(video_path):
            display_video(video_path)
        else:
            st.warning("Video file not found.")
    
    with col2:
        st.subheader("Analysis Report")
        if result_info["has_report"]:
            report_content = load_report(
                st.session_state.current_result_dir, 
                result_info["report_file"]
            )
            st.markdown(report_content)
        else:
            st.warning("Report not found.")
    
    # Display metadata and frames
    if result_info["has_metadata"]:
        metadata = load_metadata(
            st.session_state.current_result_dir, 
            result_info["metadata_file"]
        )
        
        # Create a table of frames in an expander
        with st.expander("Raw Analysis Data"):
            if metadata:
                all_frames = []
                for chunk in metadata:
                    for frame in chunk["frames"]:
                        all_frames.append({
                            "Frame Number": frame["frame_number"],
                            "Timestamp (s)": f"{frame['timestamp']:.2f}",
                        })
                
                if all_frames:
                    df = pd.DataFrame(all_frames)
                    st.dataframe(df.head(1000), use_container_width=True)
                else:
                    st.warning("No frame data found.")
            else:
                st.warning("No metadata found.")
        
        # Show chunk captions in separate expanders (NOT nested)
        if metadata:
            st.subheader("Chunk Captions")
            for i, chunk in enumerate(metadata, 1):
                with st.expander(f"Chunk {i}"):
                    st.markdown(chunk["chunk_caption"])
    
else:
    # Welcome message when no result is selected
    st.markdown("""
    ## Welcome to AI Work Inspector
    
    This application helps you analyze work procedures in videos using AI vision and language models.
    
    ### To get started:
    1. Configure your analysis parameters in the sidebar
    2. Upload a video file
    3. Click "Process Video" to begin analysis
    
    ### Features:
    - Extract frames from videos at regular intervals
    - Analyze work procedures and inefficiencies
    - Generate detailed reports with improvement suggestions
    - Review past analyses
    
    Upload a video to begin!
    """)

# Footer
st.markdown("---")
st.markdown("AI Work Inspector | Built with Streamlit and Azure AI")

# Cleanup function for app termination
def cleanup_temp_files():
    """Clean up temporary files when app is terminated"""
    if 'uploaded_video_path' in st.session_state and st.session_state.uploaded_video_path:
        if os.path.exists(st.session_state.uploaded_video_path):
            try:
                os.unlink(st.session_state.uploaded_video_path)
            except:
                pass  # Ignore cleanup errors

# Register cleanup function
import atexit
atexit.register(cleanup_temp_files)
