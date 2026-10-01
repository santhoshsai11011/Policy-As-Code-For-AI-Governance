import os

from dotenv import load_dotenv
from supabase import create_client, Client


# Load variables from the root .env file
load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL is not set in the environment."
    )

if not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "SUPABASE_SECRET_KEY is not set in the environment."
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


BUCKET_NAME = "run-artifacts"