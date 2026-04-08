import os
import datetime
import base64
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from dotenv import load_dotenv
from .llm_provider import get_video_analysis_provider

# Load environment variables
load_dotenv(override=False)

# Azure Storage Blob configuration
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")

def get_blob_service_client():
    """Returns a BlobServiceClient instance."""
    if not BLOB_CONNECTION_STRING:
        raise ValueError("Missing required environment variable: BLOB_CONNECTION_STRING")
    return BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)

def upload_to_blob(file_path, blob_name):
    """
    Uploads a file to Azure Blob Storage and returns its URL with SAS token.
    
    Args:
        file_path: Path to the local file
        blob_name: Name to use in blob storage
        
    Returns:
        tuple: (blob_url, sas_token)
    """
    if not BLOB_CONTAINER_NAME:
        raise ValueError("Missing required environment variable: BLOB_CONTAINER_NAME")

    blob_service_client = get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=blob_name)
    
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = start_time + datetime.timedelta(days=1)

    # Generate SAS token
    sas_token = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=blob_client.container_name,
        blob_name=blob_client.blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )
    
    blob_url = blob_client.url
    return blob_url, sas_token

def convert_image_to_base64(image_path):
    """
    Convert an image file to Base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Base64 encoded image data with data URI prefix
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_string}"

def create_caption_with_history(
    image_infos,
    history_captions,
    task_name="battery exchange",
    custom_system_prompt=None,
    provider_name=None,
    analysis_model=None,
    report_model=None,
):
    """
    Generate captions for frames with context from history.
    
    Args:
        image_infos: List of dictionaries with frame information
        history_captions: List of previous caption texts
        task_name: Name of the task being analyzed
        custom_system_prompt: Optional custom system prompt to override default
        provider_name: LLM provider identifier
        analysis_model: Optional deployment name for frame analysis
        report_model: Optional deployment name for report generation
        
    Returns:
        str: Generated caption
    """
    provider = get_video_analysis_provider(
        provider_name=provider_name,
        analysis_model=analysis_model,
        report_model=report_model,
    )
    return provider.create_caption(
        image_infos=image_infos,
        history_captions=history_captions,
        task_name=task_name,
        custom_system_prompt=custom_system_prompt,
    )


def create_caption_by_gpt_with_history(
    image_infos,
    history_captions,
    task_name="battery exchange",
    custom_system_prompt=None,
    provider_name=None,
    analysis_model=None,
    report_model=None,
):
    return create_caption_with_history(
        image_infos=image_infos,
        history_captions=history_captions,
        task_name=task_name,
        custom_system_prompt=custom_system_prompt,
        provider_name=provider_name,
        analysis_model=analysis_model,
        report_model=report_model,
    )


def generate_final_report(
    filtered_data,
    task_name="battery exchange",
    custom_system_prompt=None,
    provider_name=None,
    analysis_model=None,
    report_model=None,
):
    """
    Generate a final report from all chunk data.
    
    Args:
        filtered_data: List of processed chunk data
        task_name: Name of the task being analyzed
        custom_system_prompt: Optional custom system prompt to override default
        provider_name: LLM provider identifier
        analysis_model: Optional deployment name for frame analysis
        report_model: Optional deployment name for report generation
        
    Returns:
        str: Generated report in Markdown format
    """
    provider = get_video_analysis_provider(
        provider_name=provider_name,
        analysis_model=analysis_model,
        report_model=report_model,
    )
    return provider.generate_report(
        filtered_data=filtered_data,
        task_name=task_name,
        custom_system_prompt=custom_system_prompt,
    )
