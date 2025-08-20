import os
import cv2
import json
import datetime
import concurrent.futures
import collections
from .azure_services import upload_to_blob, create_caption_by_gpt_with_history, convert_image_to_base64

def extract_and_save_frames(video_path, output_dir, interval=2):
    """
    Extract frames from video at specified intervals and save them locally.
    
    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        interval: Interval in seconds between extracted frames
        
    Returns:
        list: List of tuples (frame_path, frame_number, timestamp)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # fallback if metadata is missing/zero
    video_filename = os.path.basename(video_path)

    saved_frames = []
    frame_number = 0
    last_slot = -1  # ensure only one frame per interval slot

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Prefer accurate stream timestamp when available
        pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
        if pos_msec and pos_msec > 0:
            current_time = pos_msec / 1000.0
        else:
            current_time = frame_number / fps

        # Compute the current interval slot
        slot = int(current_time // interval)

        # Save only the first frame in each slot
        if slot != last_slot:
            frame_filename = f"{video_filename}_frame_{frame_number}.jpg"
            frame_filepath = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_filepath, frame)
            saved_frames.append((frame_filepath, frame_number, current_time))
            last_slot = slot

        frame_number += 1

    cap.release()
    return saved_frames

def chunkify(lst, chunk_size=5):
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: Input list
        chunk_size: Number of items per chunk
        
    Returns:
        generator: Yields chunks of the list
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i+chunk_size]

def process_video_with_history(video_path, output_dir, interval=5, chunk_size=5, task_name="battery exchange", custom_analysis_prompt=None):
    """
    Process video sequentially with history context.
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save outputs
        interval: Seconds between frames
        chunk_size: Number of frames per chunk
        task_name: Name of the task in the video
        custom_analysis_prompt: Optional custom system prompt for frame analysis
        
    Returns:
        list: All metadata for the video processing
    """
    video_filename = os.path.basename(video_path)
    frames = extract_and_save_frames(video_path, output_dir, interval=interval)
    frame_chunks = list(chunkify(frames, chunk_size=chunk_size))

    # Keep last 5 captions in history
    history = collections.deque(maxlen=5)
    all_metadata = []

    for chunk in frame_chunks:
        # Upload frames to blob and convert to base64 for OpenAI
        image_infos = []
        for frame_filepath, frame_number, timestamp in chunk:
            # Upload to blob for storage
            blob_url, sas_token = upload_to_blob(frame_filepath, f"images/{os.path.basename(frame_filepath)}")
            # Convert to base64 for OpenAI processing
            base64_data = convert_image_to_base64(frame_filepath)
            
            image_infos.append({
                "base64_data": base64_data,  # For OpenAI processing
                "blob_url": blob_url,        # For storage reference
                "sas_token": sas_token,      # For storage access
                "frame_number": frame_number,
                "timestamp": timestamp
            })

        # Generate caption with history and custom prompt (uses base64_data)
        caption = create_caption_by_gpt_with_history(image_infos, list(history), task_name, custom_analysis_prompt)

        # Compile metadata
        chunk_meta = {
            "video_filename": video_filename,
            "frames": [
                {
                    "frame_number": info["frame_number"],
                    "timestamp": info["timestamp"],
                    "frame_path": frames[i][0],  # Local file path
                    "blob_url": info["blob_url"],  # Blob storage URL
                    "blob_url_with_sas": f"{info['blob_url']}?{info['sas_token']}"  # URL with SAS for access
                }
                for i, info in enumerate(image_infos)
            ],
            "chunk_caption": caption
        }

        # Add to history and results
        history.append(caption)
        all_metadata.append(chunk_meta)

    # Save metadata to JSON and upload to blob
    metadata_json_path = os.path.join(output_dir, f"{video_filename}_metadata.json")
    with open(metadata_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=4)
    
    upload_to_blob(metadata_json_path, f"metadata/{video_filename}_metadata.json")
    
    return all_metadata
