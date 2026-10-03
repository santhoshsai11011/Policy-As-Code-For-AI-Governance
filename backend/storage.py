from pathlib import Path

from backend.supabase_client import (
    supabase,
    BUCKET_NAME,
)


# ============================================================
# UPLOAD RUN ARTIFACTS
# ============================================================

def upload_run_artifacts(
    run_id,
    artifacts,
    original_policy_filename=None,
):
    """
    Upload all artifacts for a completed run
    into the private run-artifacts Supabase Storage bucket.
    """

    run_folder = f"run_{run_id}"

    content_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".json": "application/json",
        ".xlsx": (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        ".rego": "text/plain",
    }

    uploaded_paths = {}

    for artifact_name, local_path in artifacts.items():

        path = Path(local_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Run artifact not found: {path}"
            )

        artifact_filename = path.name

        if (
            artifact_name == "policy_pdf"
            and original_policy_filename
        ):
            artifact_filename = Path(
                original_policy_filename
            ).name

        storage_path = (
            f"{run_folder}/{artifact_filename}"
        )

        content_type = content_types.get(
            path.suffix.lower(),
            "application/octet-stream",
        )

        with open(
            path,
            "rb",
        ) as artifact_file:

            supabase.storage                 .from_(BUCKET_NAME)                 .upload(
                    path=storage_path,
                    file=artifact_file,
                    file_options={
                        "content-type": content_type,
                        "upsert": "false",
                    },
                )

        uploaded_paths[artifact_name] = storage_path

    return uploaded_paths


# ============================================================
# CREATE SIGNED DOWNLOAD URL
# ============================================================

def create_run_artifact_url(
    storage_path,
    expires_in=300,
):
    """
    Create a temporary signed URL for a private
    run artifact in Supabase Storage.
    """

    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_url(
            storage_path,
            expires_in,
            {"download": True},
        )
    )

    return response["signedURL"]