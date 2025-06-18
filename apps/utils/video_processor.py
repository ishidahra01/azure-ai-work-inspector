import os
import cv2
import json
import datetime
import concurrent.futures
import collections
from .azure_services import upload_to_blob, create_caption_by_gpt_multi, create_caption_by_gpt_with_history

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

    # Load video file
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_filename = os.path.basename(video_path)

    saved_frames = []  # [(frame_path, frame_number, timestamp), ...]

    frame_number = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        current_time = frame_number / fps

        # Save frame at each interval
        if current_time % interval < 1.0 / fps:
            frame_filename = f"{video_filename}_frame_{frame_number}.jpg"
            frame_filepath = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_filepath, frame)
            saved_frames.append((frame_filepath, frame_number, current_time))

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

def process_frame_chunk(chunk, video_filename):
    """
    Process a chunk of frames (upload to blob and generate caption).
    
    Args:
        chunk: List of frame tuples
        video_filename: Name of the video file
        
    Returns:
        dict: Metadata for the chunk including caption
    """
    # Upload frames to blob and collect information
    image_infos = []
    for (frame_filepath, frame_number, timestamp) in chunk:
        frame_filename = os.path.basename(frame_filepath)
        blob_url, sas_token = upload_to_blob(frame_filepath, f"images/{frame_filename}")
        image_infos.append({
            "url": f"{blob_url}?{sas_token}",
            "frame_number": frame_number,
            "timestamp": timestamp
        })
    
    # Generate caption for the chunk
    caption = create_caption_by_gpt_multi(image_infos)

    # Compile metadata
    chunk_metadata = {
        "video_filename": video_filename,
        "frames": [
            {
                "frame_number": info["frame_number"],
                "timestamp": info["timestamp"],
                "frame_url_with_sas": info["url"]
            }
            for info in image_infos
        ],
        "chunk_caption": caption
    }
    return chunk_metadata

def process_video_in_chunks(video_path, output_dir, interval=5, parallel_degree=4, chunk_size=5):
    """
    Process a video by extracting frames, splitting into chunks,
    and processing each chunk in parallel.
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save outputs
        interval: Seconds between frames
        parallel_degree: Number of parallel threads
        chunk_size: Number of frames per chunk
        
    Returns:
        str: Path to metadata JSON file
    """
    video_filename = os.path.basename(video_path)
    frames = extract_and_save_frames(video_path, output_dir, interval=interval)

    # Split frames into chunks
    frame_chunks = list(chunkify(frames, chunk_size=chunk_size))

    chunk_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_degree) as executor:
        future_to_chunk = {
            executor.submit(process_frame_chunk, chunk, video_filename): chunk
            for chunk in frame_chunks
        }
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                data = future.result()
                chunk_results.append(data)
            except Exception as exc:
                print(f"chunk {chunk} generated an exception: {exc}")

    # Save metadata to JSON
    metadata_json_path = os.path.join(output_dir, f"{video_filename}_metadata.json")
    with open(metadata_json_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_results, f, ensure_ascii=False, indent=4)

    # Upload metadata to blob
    upload_to_blob(metadata_json_path, f"metadata/{video_filename}_metadata.json")

    return metadata_json_path

def process_video_with_history(video_path, output_dir, interval=5, chunk_size=5, task_name="battery exchange"):
    """
    Process video sequentially with history context.
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save outputs
        interval: Seconds between frames
        chunk_size: Number of frames per chunk
        task_name: Name of the task in the video
        
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
        # Upload frames to blob and collect information
        image_infos = []
        for frame_filepath, frame_number, timestamp in chunk:
            blob_url, sas_token = upload_to_blob(frame_filepath, f"images/{os.path.basename(frame_filepath)}")
            image_infos.append({
                "url": f"{blob_url}?{sas_token}",
                "frame_number": frame_number,
                "timestamp": timestamp
            })

        # Generate caption with history
        caption = create_caption_by_gpt_with_history(image_infos, list(history), task_name)

        # Compile metadata
        chunk_meta = {
            "video_filename": video_filename,
            "frames": [
                {
                    "frame_number": info["frame_number"],
                    "timestamp": info["timestamp"],
                    "frame_url_with_sas": info["url"]
                }
                for info in image_infos
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
