"""
Configuration settings for the AI Work Inspector application
"""

# File upload settings
MAX_UPLOAD_SIZE_GB = 5  # Maximum upload size in GB
CHUNK_SIZE_MB = 8      # Chunk size for file operations in MB
PROGRESS_UPDATE_INTERVAL = 1024 * 1024  # Update progress every 1MB

# Video processing settings
DEFAULT_FRAME_INTERVAL = 2
DEFAULT_CHUNK_SIZE = 15
MAX_FRAMES_PER_CHUNK = 50

# Supported video formats
SUPPORTED_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'webm']

# Directory settings
RESULTS_BASE_DIR = "results"
TEMP_DIR_PREFIX = "ai_work_inspector_"

# UI settings
LARGE_FILE_WARNING_SIZE_MB = 500  # Show warning for files larger than this
PROGRESS_BAR_UPDATE_FREQUENCY = 10  # Update every N chunks

# Error messages
ERROR_MESSAGES = {
    'file_too_large': f'File size exceeds the maximum limit of {MAX_UPLOAD_SIZE_GB}GB.',
    'unsupported_format': f'Unsupported file format. Please use one of: {", ".join(SUPPORTED_VIDEO_FORMATS)}',
    'upload_failed': 'Failed to upload file. Please check your internet connection and try again.',
    'processing_failed': 'Video processing failed. Please check the file and try again.',
    'temp_file_creation_failed': 'Failed to create temporary file. Please check disk space and permissions.',
    'file_copy_failed': 'Failed to copy file to result directory. Please check disk space.',
}
