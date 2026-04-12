import os
import base64
import requests
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
import io

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

def generate_image() -> bytes:
    now = datetime.now(SHANGHAI_TZ)
    day_str = now.strftime("%A").upper()       # SUNDAY
    date_str = now.strftime("%B %d").upper()   # APRIL 12

    # Canvas — 1792x1024 to match previous DALL-E size
    width, height = 1792, 1024
    img = Image.new("RGB", (width, height), color=(10, 10, 15))
    draw = ImageDraw.Draw(img)

    # Subtle blue gradient overlay on left side
    for x in range(width // 2):
        alpha = int(18 * (1 - x / (width // 2)))
        for y in range(height):
            r, g, b = img.getpixel((x, y))
            img.putpixel((x, y), (r, min(g + alpha, 255), min(b + alpha * 3, 255)))

    # Try to use a bold system font, fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 280)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 100)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw day name (smaller, lighter)
    draw.text((120, 180), day_str, font=font_small, fill=(180, 180, 200))

    # Draw date (huge, dominant)
    draw.text((100, 280), date_str, font=font_large, fill=(255, 255, 255))

    # Thin horizontal accent line
    draw.rectangle([100, 250, 600, 253], fill=(50, 100, 200))

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    print(f"Generated image: {len(image_bytes)} bytes")
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
        print("cover.png updated on GitHub.")

def update_notion_cover(image_url: str):
    # Clear first
    requests.patch(
        f"https://api.notion.com/v1/pages/{NOTION_MAIN_PAGE_ID}",
        headers=NOTION_HEADERS,
        json={"cover": None},
    )
    print("Cleared existing cover.")

    import time
    time.sleep(2)

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

defdef main():
    print("Generating cover image...")
    image_bytes = generate_image()

    print("Updating Notion cover...")
    # Upload raw bytes to Notion via a temporary file server
    # Use transfer.sh — no account needed, free, instant URL
    response = requests.put(
        "https://transfer.sh/cover.png",
        data=image_bytes,
        headers={"Max-Days": "1"},
    )
    temp_url = response.text.strip()
    print(f"Temporary URL: {temp_url}")

    update_notion_cover(temp_url)

    print("Pushing to GitHub for archive...")
    push_to_github(image_bytes)

    print("Done.")

if __name__ == "__main__":
    main()
