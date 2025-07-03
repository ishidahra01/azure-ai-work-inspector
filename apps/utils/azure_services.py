import os
import datetime
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Azure Storage Blob configuration
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AOAI_API_VERSION = '2024-12-01-preview'

def get_blob_service_client():
    """Returns a BlobServiceClient instance."""
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

def get_openai_client():
    """Returns an AzureOpenAI client instance for GPT-4o model."""
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AOAI_API_VERSION
    )
    return client

def create_caption_by_gpt_multi(image_infos):
    """
    Generate captions for multiple frames using GPT-4o.
    
    Args:
        image_infos: List of dictionaries with frame information (url, frame_number, timestamp)
        
    Returns:
        str: Generated caption
    """
    client = get_openai_client()
    
    system_message = """
    You are an expert in analyzing vehicle inspection procedures from video footage.  
    Given a set of frames extracted from a continuous video, along with descriptions of prior tasks already completed, your tasks are as follows:

    - Describe the sequence of actions observed in the frames, including the time taken for each action and any notable changes in the inspection process.
    - Identify inefficient movements or suboptimal work methods observed during the inspection process and propose concrete improvements.
    - Discover implicit knowledge and expert techniques demonstrated by experienced workers that may not be documented but contribute to efficient task execution.

    You should focus on the following aspects:
    - Analyze the sequence as a time-continuous process, not as isolated frames.
    - Consider temporal consistency and motion cues to understand how the inspection unfolds.
    - Take into account the context of previously completed tasks to infer the purpose and position of the current action within the overall workflow.
    - Provide a concise explanation in English (max 400 characters per task), explaining your reasoning based on observed changes across frames and the prior task context.
    """

    user_content = []
    for idx, info in enumerate(image_infos):
        user_content.append({
            "type": "text",
            "content": f"Frame {idx+1}: time={info['timestamp']:.2f} sec, frame_number={info['frame_number']}."
        })
        user_content.append({
            "type": "image_url",
            "image_url": {"url": info['url']}
        })

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_content},
    ]

    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0,
        max_tokens=1000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0
    )

    caption_text = completion.choices[0].message.content
    return caption_text

def create_caption_by_gpt_with_history(image_infos, history_captions, task_name="battery exchange"):
    """
    Generate captions for frames with context from history.
    
    Args:
        image_infos: List of dictionaries with frame information
        history_captions: List of previous caption texts
        task_name: Name of the task being analyzed
        
    Returns:
        str: Generated caption
    """
    client = get_openai_client()
    
    system_message = f"""
    You are an expert in analyzing vehicle inspection procedures from video footage, especially {task_name} tasks. 
    Given a set of frames extracted from a continuous video, along with descriptions of prior tasks already completed, your tasks are as follows:

    - Describe the sequence of actions observed in the frames, including the time taken for each action and any notable changes in the inspection process.
    - Identify inefficient movements or suboptimal work methods observed during the inspection process and propose concrete improvements.
    - Discover implicit knowledge and expert techniques demonstrated by experienced workers that may not be documented but contribute to efficient task execution.

    You should focus on the following aspects:
    - Analyze the sequence as a time-continuous process, not as isolated frames.
    - Consider temporal consistency and motion cues to understand how the inspection unfolds.
    - Take into account the context of previously completed tasks to infer the purpose and position of the current action within the overall workflow.
    - Provide a concise explanation in English (max 400 characters per task), explaining your reasoning based on observed changes across frames and the prior task context.
    
    Here is the history of captions for the previous frames:
    {history_captions}
    """

    user_content = []
    for idx, info in enumerate(image_infos):
        user_content.append({
            "type": "text",
            "content": f"Frame {idx+1}: time={info['timestamp']:.2f} sec, frame_number={info['frame_number']}."
        })
        user_content.append({
            "type": "image_url",
            "image_url": {"url": info['url']}
        })

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_content},
    ]

    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0,
        max_tokens=1000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0
    )

    return completion.choices[0].message.content

def generate_final_report(filtered_data, task_name="battery exchange"):
    """
    Generate a final report from all chunk data.
    
    Args:
        filtered_data: List of processed chunk data
        task_name: Name of the task being analyzed
        
    Returns:
        str: Generated report in Markdown format
    """
    client = get_openai_client()
    
    developer_message = f"""
    You are an expert in generating structured reports based on video analysis of vehicle inspection work, especially {task_name}.
    Analyze the video and create a detailed report with the following instructions:

    - Structure the findings into clear, organized sections ("Task description"," "Inefficient Movements", "Improvement Suggestions", "Implicit Expert Knowledge").
    - Do not omit any tasks and any insights you observe from the video. Even minor observations should be included if they provide meaningful insight.
    - Use bullet points, subheadings, and concise descriptions to make the report easy to read and actionable.
    - The output must be in Markdown format and in Japanese.
    - For each reported item, include one or more corresponding time frames (e.g., 00:01:23–00:01:35) from the video as supporting evidence, to ensure traceability and allow reviewers to reference the specific moments where the observations were made.

    Note: The original frame analysis results are based only on a limited time segment, so there may be inaccuracies due to missing context from preceding and following frames. Please review the full sequence of results, and revise any inconsistencies using information from the surrounding context.
    """

    response = client.chat.completions.create(
        model="o4-mini",  # Use appropriate model deployment name
        messages=[
            {"role": "developer", "content": developer_message},
            {"role": "user", "content": str(filtered_data)},
        ],
        max_completion_tokens=10000,  # Adjust as needed
    )

    return response.choices[0].message.content
