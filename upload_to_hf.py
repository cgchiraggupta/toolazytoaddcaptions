import os

from huggingface_hub import HfApi

api = HfApi()
repo_id = "Ppreyy/hinglishcaptions"

# Upload modified files
files_to_upload = [
    ("app.py", "app.py"),
    ("batch.py", "batch.py"),
    ("requirements.txt", "requirements.txt"),
    ("README.md", "README.md"),
]

for local_path, path_in_repo in files_to_upload:
    if os.path.exists(local_path):
        print(f"Uploading {local_path}...")
        api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type="space",
        )
        print(f"Uploaded {local_path}")
    else:
        print(f"File not found: {local_path}")

print("\nAll files uploaded successfully!")
print("The Hugging Face Space will rebuild automatically.")
print("Visit: https://huggingface.co/spaces/Ppreyy/hinglishcaptions")
