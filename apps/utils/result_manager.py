import os
import json
import copy
import datetime
from .azure_services import generate_final_report

def create_result_directory(base_path="results"):
    """
    Create a unique result directory with timestamp.
    
    Args:
        base_path: Base directory for results
        
    Returns:
        str: Path to the created directory
    """
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        
    # Create timestamp-based directory name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_dir = os.path.join(base_path, timestamp)
    
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        
    return result_dir

def get_all_result_dirs(base_path="results"):
    """
    Get all result directories sorted by creation time (newest first).
    
    Args:
        base_path: Base directory for results
        
    Returns:
        list: List of result directory paths
    """
    if not os.path.exists(base_path):
        return []
        
    result_dirs = [os.path.join(base_path, d) for d in os.listdir(base_path) 
                   if os.path.isdir(os.path.join(base_path, d))]
    
    # Sort by creation time (newest first)
    result_dirs.sort(key=lambda x: os.path.getctime(x), reverse=True)
    
    return result_dirs

def save_metadata(metadata, result_dir, video_filename):
    """
    Save processing metadata to the result directory.
    
    Args:
        metadata: Processing metadata to save
        result_dir: Directory to save metadata
        video_filename: Name of the processed video
        
    Returns:
        str: Path to the saved metadata file
    """
    metadata_path = os.path.join(result_dir, f"{video_filename}_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    return metadata_path

def save_final_report(metadata, result_dir, video_filename, task_name="battery exchange"):
    """
    Generate and save a final analysis report.
    
    Args:
        metadata: Processing metadata to analyze
        result_dir: Directory to save the report
        video_filename: Name of the processed video
        task_name: Name of the task in the video
        
    Returns:
        str: Path to the saved report file
    """
    # Create filtered data without unnecessary fields
    filtered_data = copy.deepcopy(metadata)
    for obj in filtered_data:
        obj.pop('video_filename', None)
        for frame in obj['frames']:
            frame.pop('frame_number', None)
            frame.pop('frame_url_with_sas', None)
    
    # Generate the report
    report_content = generate_final_report(filtered_data, task_name)
    
    # Save the report
    report_path = os.path.join(result_dir, f"{video_filename}_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    return report_path

def get_result_info(result_dir):
    """
    Get information about a result directory.
    
    Args:
        result_dir: Path to a result directory
        
    Returns:
        dict: Information about the result
    """
    # Get timestamp from directory name
    dir_name = os.path.basename(result_dir)
    
    # Find metadata and report files
    metadata_files = [f for f in os.listdir(result_dir) if f.endswith("_metadata.json")]
    report_files = [f for f in os.listdir(result_dir) if f.endswith("_report.md")]
    
    # Extract video name from first metadata file if available
    video_name = None
    if metadata_files:
        video_name = metadata_files[0].replace("_metadata.json", "")
    
    return {
        "dir": result_dir,
        "timestamp": dir_name,
        "video_name": video_name,
        "has_metadata": len(metadata_files) > 0,
        "has_report": len(report_files) > 0,
        "metadata_file": metadata_files[0] if metadata_files else None,
        "report_file": report_files[0] if report_files else None
    }

def load_metadata(result_dir, metadata_filename):
    """
    Load metadata from a result directory.
    
    Args:
        result_dir: Path to the result directory
        metadata_filename: Name of the metadata file
        
    Returns:
        dict: Loaded metadata
    """
    metadata_path = os.path.join(result_dir, metadata_filename)
    if not os.path.exists(metadata_path):
        return None
        
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_report(result_dir, report_filename):
    """
    Load a report from a result directory.
    
    Args:
        result_dir: Path to the result directory
        report_filename: Name of the report file
        
    Returns:
        str: Report content
    """
    report_path = os.path.join(result_dir, report_filename)
    if not os.path.exists(report_path):
        return None
        
    with open(report_path, 'r', encoding='utf-8') as f:
        return f.read()
