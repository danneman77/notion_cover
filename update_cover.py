import os
import base64
import requests
from datetime import datetime, timezone, timedelta

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

SHANGHAI_TZ = timezone(timedelta(hours=8))

def generate_image() -> bytes:
    now = datetime.now(SHANGHAI_TZ)
    date_str = now.strftime("%B %d, %Y")

    prompt = (
        f"A beautiful, minimal, high-quality dashboard cover image for {date_str}.Include date and day in image "
        "Abstract visualization of global markets, data flows, and world connectivity. "
        "Dark background with subtle gold and blue tones. "
        "Cinematic, sophisticated, no text, no numbers, no charts."
    )

    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "3000x1200",
            "quality": "standard",
        },
    )

    if response.status_code != 200:
        print(f"OpenAI error: {response.status_code} {response.json()}")
        response.raise_for_status()

    image_url = response.json()["data"][0]["url"]
    print(f"Generated image URL: {image_url}")

    image_bytes = requests.get(image_url).content
    print(f"Downloaded image: {len(image_bytes)} bytes")
    return image_bytes

def push_to_github(image_bytes: bytes):
    github_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    get_response = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/cover.png",
        headers=github_headers,
    )

    sha = get_response.json().get("sha") if get_response.status_code == 200 else None

    payload = {
        "message": f"Update cover image {datetime.now(SHANGHAI_TZ).strftime('%Y-%m-%d')}",
        "content": base64.b64encode(image_bytes).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/cover.png",
        headers=github_headers,
        json=payload,
    )

    if put_response.status_code not in [200, 201]:
        print(f"ERROR pushing to GitHub: {put_response.status_code} {put_response.json()}")
    else:
        print(f"cover.png updated at: https://raw.githubusercontent.com/{GITHUB_REPO}/main/cover.png")

def main():
    print("Generating daily cover image with DALL-E 3...")
    image_bytes = generate_image()

    print("Pushing to GitHub...")
    push_to_github(image_bytes)

    print("Done.")

if __name__ == "__main__":
    main()
