import os
# This MUST be set before importing huggingface_hub
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1" 

from huggingface_hub import HfApi

api = HfApi()

file_path = "uq_modified_dataset_stage_2.zip"
repo_id = "OliseNS/AerialBirdDetection_2ndPlace_NexusLADevDays"

print(f"Uploading {file_path} using high-speed transfer...")

api.upload_file(
    path_or_fileobj=file_path,
    path_in_repo=file_path, 
    repo_id=repo_id,
    repo_type="dataset",
    commit_message="Uploading zipped YOLO dataset via hf_transfer"
)

print("Upload complete!")
