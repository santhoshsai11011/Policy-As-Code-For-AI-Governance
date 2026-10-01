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
    policy_pdf_path,
    policy_excel_path,
):
    """
    Upload the policy PDF and policy Excel for a completed run
    into the private run-artifacts Supabase Storage bucket.
    """

    run_folder = f"run_{run_id}"

    pdf_storage_path = (
        f"{run_folder}/policy.pdf"
    )

    excel_storage_path = (
        f"{run_folder}/policy.xlsx"
    )

    pdf_path = Path(policy_pdf_path)
    excel_path = Path(policy_excel_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Policy PDF not found: {pdf_path}"
        )

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Policy Excel not found: {excel_path}"
        )

    # --------------------------------------------------------
    # Upload Policy PDF
    # --------------------------------------------------------

    with open(
        pdf_path,
        "rb",
    ) as pdf_file:

        supabase.storage \
            .from_(BUCKET_NAME) \
            .upload(
                path=pdf_storage_path,
                file=pdf_file,
                file_options={
                    "content-type": "application/pdf",
                    "upsert": "false",
                },
            )

    # --------------------------------------------------------
    # Upload Policy Excel
    # --------------------------------------------------------

    with open(
        excel_path,
        "rb",
    ) as excel_file:

        supabase.storage \
            .from_(BUCKET_NAME) \
            .upload(
                path=excel_storage_path,
                file=excel_file,
                file_options={
                    "content-type": (
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    "upsert": "false",
                },
            )

    return {
        "policy_pdf_path": pdf_storage_path,
        "policy_excel_path": excel_storage_path,
    }


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