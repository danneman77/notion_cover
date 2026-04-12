import os
import base64
import requests
from datetime import datetime, timezone, timedelta

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_MAIN_PAGE_ID = os.environ["NOTION_MAIN_PAGE_ID"]

SHANGHAI_TZ = timezone(timedelta(hours=8))

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def generate_image():
    now = datetime.now(SHANGHAI_TZ)
    date_str = now.strftime("%A, %B %d, %Y")

    prompt = (
    f"A wide, ultra-minimal dark background image, pure dark charcoal or near-black. "
    f"Very subtle, soft blue gradient light from one side. Almost completely empty. "
    f"In the lower right corner, display the text '{date_str}' in an extremely large, "
    "clean, modern white sans-serif font. The date text should be massive — "
    "taking up roughly 30% of the image width. "
    "Nothing else in the image. No phones, no devices, no UI elements, no charts, "
    "no circles, no decorative elements, no clutter whatsoever. "
    "Just dark background, subtle gradient, and the large date text."
)

    print(f"Prompt: {prompt}")

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
            "size": "1792x1024",
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
    return image_bytes, image_url

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
        print(f"cover.png updated on GitHub.")

def update_notion_cover(image_url: str):
    # Step 1 — remove current cover
    requests.patch(
        f"https://api.notion.com/v1/pages/{NOTION_MAIN_PAGE_ID}",
        headers=NOTION_HEADERS,
        json={"cover": None},
    )
    print("Cleared existing cover.")

    import time
    time.sleep(2)

    # Step 2 — set new cover
    response = requests.patch(
        f"https://api.notion.com/v1/pages/{NOTION_MAIN_PAGE_ID}",
        headers=NOTION_HEADERS,
        json={
            "cover": {
                "type": "external",
                "external": {"url": image_url},
            }
        },
    )
    if response.status_code != 200:
        print(f"ERROR updating Notion cover: {response.status_code} {response.json()}")
    else:
        print("Notion cover updated successfully.")

def main():
    print("Generating daily cover image with DALL-E 3...")
    image_bytes, openai_url = generate_image()

    print("Updating Notion cover...")
    update_notion_cover(openai_url)

    print("Pushing to GitHub for archive...")
    push_to_github(image_bytes)

    print("Done.")

if __name__ == "__main__":
    main()
