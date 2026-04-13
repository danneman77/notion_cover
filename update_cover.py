import os
import base64
import requests
import time
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
import io

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_MAIN_PAGE_ID = os.environ["NOTION_MAIN_PAGE_ID"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]

SHANGHAI_TZ = timezone(timedelta(hours=8))

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def generate_image() -> bytes:
    now = datetime.now(SHANGHAI_TZ)
    day_str = now.strftime("%A").upper()
    date_str = now.strftime("%B %d").upper()

    width, height = 1792, 1024
    img = Image.new("RGB", (width, height), color=(10, 10, 15))
    draw = ImageDraw.Draw(img)

    # Subtle blue gradient on left side
    for x in range(width // 2):
        alpha = int(18 * (1 - x / (width // 2)))
        for y in range(height):
            r, g, b = img.getpixel((x, y))
            img.putpixel((x, y), (r, min(g + alpha, 255), min(b + alpha * 3, 255)))

    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 70)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()

    draw.text((120, 400), day_str, font=font_small, fill=(255, 255, 255))
    draw.text((120, 450), date_str, font=font_large, fill=(255, 255, 255))
    draw.text((120, 530), "D'S DASHBOARD", font=font_title, fill=(100, 130, 200))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    print(f"Generated image: {len(image_bytes)} bytes")
    return image_bytes

def upload_to_imgbb(image_bytes: bytes) -> str:
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key": IMGBB_API_KEY,
            "image": base64.b64encode(image_bytes).decode("utf-8"),
        },
    )
    if response.status_code != 200:
        print(f"ERROR uploading to imgbb: {response.status_code} {response.json()}")
        response.raise_for_status()

    url = response.json()["data"]["url"]
    print(f"Uploaded to imgbb: {url}")
    return url

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

def main():
    print("Generating cover image...")
    image_bytes = generate_image()

    print("Uploading to imgbb...")
    image_url = upload_to_imgbb(image_bytes)

    print("Updating Notion cover...")
    update_notion_cover(image_url)

    print("Pushing to GitHub for archive...")
    push_to_github(image_bytes)

    print("Done.")

if __name__ == "__main__":
    main()
