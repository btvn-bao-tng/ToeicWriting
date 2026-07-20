from dataclasses import dataclass
import os

import requests


@dataclass
class ImageResult:
    image_url: str
    page_url: str
    photographer: str
    alt_text: str


def word_to_image(query: str, api_key: str) -> ImageResult | None:
    """
    Search Pexels and return the first matching image.
    """
    endpoint = "https://api.pexels.com/v1/search"

    response = requests.get(
        endpoint,
        headers={"Authorization": api_key},
        params={
            "query": query,
            "per_page": 1,
            "orientation": "landscape",
        },
        timeout=15,
    )
    response.raise_for_status()

    photos = response.json().get("photos", [])
    if not photos:
        return None

    photo = photos[0]

    return ImageResult(
        image_url=photo["src"]["medium"],
        page_url=photo["url"],
        photographer=photo["photographer"],
        alt_text=photo.get("alt", query),
    )


if __name__ == "__main__":
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key:
        print("Set PEXELS_API_KEY in the environment before running this script.")
        raise SystemExit(1)

    result = word_to_image(
        query="office worker jotting notes while speaking on the phone",
        api_key=api_key,
    )

    if result:
        print(result)
    else:
        print("No suitable image was found.")
