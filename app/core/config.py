"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")

NEBIUS_BASE_URL = os.getenv(
    "NEBIUS_BASE_URL",
    "https://api.studio.nebius.ai/v1",
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
)


def validate_config():
    """Validate that the required API key is present."""

    if not NEBIUS_API_KEY:
        raise ValueError(
            "NEBIUS_API_KEY environment variable is not set. "
            "Please add it to your .env file."
        )


def get_config():
    """Return validated application configuration."""

    validate_config()

    return {
        "NEBIUS_API_KEY": NEBIUS_API_KEY,
        "NEBIUS_BASE_URL": NEBIUS_BASE_URL,
        "MODEL_NAME": MODEL_NAME,
    }