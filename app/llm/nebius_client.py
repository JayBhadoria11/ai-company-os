"""Nebius Token Factory client for NVIDIA Nemotron."""

from openai import OpenAI

from app.core.config import (
    NEBIUS_API_KEY,
    NEBIUS_BASE_URL,
    MODEL_NAME,
    validate_config,
)


def get_completion(
    prompt,
    system_prompt="You are a helpful AI business analyst.",
    temperature=0.1,
    max_tokens=8192,
):
    """Send a prompt to the configured NVIDIA model through Nebius."""

    validate_config()

    client = OpenAI(
        api_key=NEBIUS_API_KEY,
        base_url=NEBIUS_BASE_URL,
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    choice = response.choices[0]
    content = choice.message.content

    if content is None or not content.strip():
        raise ValueError(
            f"Nemotron returned empty content. "
            f"Finish reason: {choice.finish_reason}. "
            "Try increasing max_tokens or simplifying the prompt."
        )

    return content.strip()
