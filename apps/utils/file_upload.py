"""
File upload utilities for handling large video files with chunked upload
"""

import os
import hashlib
import tempfile
import shutil
from typing import BinaryIO, Optional
import streamlit as st
from pathlib import Path

class ChunkedFileUploader:
    """Handles chunked upload of large files"""
    
    def __init__(self, chunk_size: int = 8 * 1024 * 1024):  # 8MB chunks
        self.chunk_size = chunk_size
        self.temp_dir = tempfile.gettempdir()
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file for integrity checking"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def save_uploaded_file_chunked(self, uploaded_file, target_path: str) -> bool:
        """
        Save uploaded file to target path using chunked reading
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            target_path: Path where the file should be saved
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create target directory if it doesn't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Create progress bar
            progress_bar = st.progress(0, text="Uploading file...")
            
            # Get file size for progress calculation
            file_size = uploaded_file.size if hasattr(uploaded_file, 'size') else None
            
            with open(target_path, 'wb') as target_file:
                bytes_written = 0
                
                # Read and write in chunks
                while True:
                    chunk = uploaded_file.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    target_file.write(chunk)
                    bytes_written += len(chunk)
                    
                    # Update progress if file size is known
                    if file_size:
                        progress = min(bytes_written / file_size, 1.0)
                        progress_bar.progress(progress, text=f"Uploading file... {bytes_written / (1024*1024):.1f}MB / {file_size / (1024*1024):.1f}MB")
            
            progress_bar.progress(1.0, text="Upload complete!")
            return True
            
        except Exception as e:
            st.error(f"Error saving file: {str(e)}")
            return False
    
    def create_temporary_file(self, uploaded_file, suffix: str = '.mp4') -> Optional[str]:
        """
        Create a temporary file from uploaded file using chunked reading
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            suffix: File suffix for temporary file
            
        Returns:
            str: Path to temporary file, or None if failed
        """
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_path = temp_file.name
            temp_file.close()
            
            # Save uploaded file to temporary location
            if self.save_uploaded_file_chunked(uploaded_file, temp_path):
                return temp_path
            else:
                # Clean up on failure
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
                
        except Exception as e:
            st.error(f"Error creating temporary file: {str(e)}")
            return None

class StreamedFileHandler:
    """Handles streaming file operations for large files"""
    
    @staticmethod
    def copy_file_with_progress(src_path: str, dst_path: str, chunk_size: int = 8 * 1024 * 1024) -> bool:
        """
        Copy file with progress indicator
        
        Args:
            src_path: Source file path
            dst_path: Destination file path
            chunk_size: Size of chunks to copy
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            # Get file size for progress calculation
            file_size = os.path.getsize(src_path)
            
            progress_bar = st.progress(0, text="Copying file...")
            
            with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                bytes_copied = 0
                
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    
                    dst.write(chunk)
                    bytes_copied += len(chunk)
                    
                    # Update progress
                    progress = min(bytes_copied / file_size, 1.0)
                    progress_bar.progress(progress, text=f"Copying file... {bytes_copied / (1024*1024):.1f}MB / {file_size / (1024*1024):.1f}MB")
            
            progress_bar.progress(1.0, text="Copy complete!")
            return True
            
        except Exception as e:
            st.error(f"Error copying file: {str(e)}")
            return False

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
