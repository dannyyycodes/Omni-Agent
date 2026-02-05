"""
Pexels Video Client - Fetches stock wildlife footage
Used as fallback when Sora is unavailable
"""

import os
import requests
import logging
import random

logger = logging.getLogger(__name__)


class PexelsClient:
    """Fetch videos from Pexels API"""

    def __init__(self):
        self.api_key = os.environ.get('PEXELS_API_KEY')
        self.base_url = "https://api.pexels.com/videos"

    def is_available(self) -> bool:
        """Check if Pexels is configured"""
        return bool(self.api_key)

    def search_video(self, query: str, orientation: str = "portrait", min_duration: int = 8) -> dict:
        """
        Search for a video matching the query.

        Args:
            query: Search term (e.g., "elephant wildlife")
            orientation: "portrait" for shorts, "landscape" for YouTube
            min_duration: Minimum video length in seconds

        Returns:
            dict with video_url, duration, width, height or None if not found
        """
        if not self.api_key:
            logger.error("PEXELS_API_KEY not configured")
            return None

        try:
            headers = {"Authorization": self.api_key}

            # Search for videos
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params={
                    "query": query,
                    "orientation": orientation,
                    "size": "medium",  # medium quality for faster downloads
                    "per_page": 15
                },
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Pexels API error: {response.status_code}")
                return None

            data = response.json()
            videos = data.get("videos", [])

            if not videos:
                # Try broader search
                logger.info(f"No results for '{query}', trying broader search...")
                return self._broader_search(query, orientation, min_duration, headers)

            # Filter by duration and pick a random one for variety
            suitable_videos = [
                v for v in videos
                if v.get("duration", 0) >= min_duration
            ]

            if not suitable_videos:
                suitable_videos = videos  # Use any if none meet duration

            video = random.choice(suitable_videos)

            # Get the best video file (prefer HD)
            video_files = video.get("video_files", [])
            best_file = self._pick_best_file(video_files, orientation)

            if not best_file:
                logger.error("No suitable video file found")
                return None

            result = {
                "video_url": best_file.get("link"),
                "duration": video.get("duration"),
                "width": best_file.get("width"),
                "height": best_file.get("height"),
                "pexels_id": video.get("id"),
                "source": "pexels"
            }

            logger.info(f"Found Pexels video: {result['video_url'][:50]}... ({result['duration']}s)")
            return result

        except Exception as e:
            logger.error(f"Pexels search failed: {e}")
            return None

    def _broader_search(self, query: str, orientation: str, min_duration: int, headers: dict) -> dict:
        """Try broader search terms if specific search fails"""
        # Extract main animal word and try variations
        words = query.lower().split()
        broader_terms = [
            f"{words[0]} animal" if words else query,
            "wildlife nature",
            "animal documentary"
        ]

        for term in broader_terms:
            try:
                response = requests.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params={
                        "query": term,
                        "orientation": orientation,
                        "per_page": 10
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    videos = response.json().get("videos", [])
                    if videos:
                        video = random.choice(videos)
                        video_files = video.get("video_files", [])
                        best_file = self._pick_best_file(video_files, orientation)

                        if best_file:
                            return {
                                "video_url": best_file.get("link"),
                                "duration": video.get("duration"),
                                "width": best_file.get("width"),
                                "height": best_file.get("height"),
                                "pexels_id": video.get("id"),
                                "source": "pexels"
                            }
            except:
                continue

        return None

    def _pick_best_file(self, video_files: list, orientation: str) -> dict:
        """Pick the best video file based on quality and orientation"""
        if not video_files:
            return None

        # For portrait (shorts), prefer files where height > width
        # For landscape, prefer width > height

        # Sort by quality (width * height) descending
        sorted_files = sorted(
            video_files,
            key=lambda f: (f.get("width", 0) * f.get("height", 0)),
            reverse=True
        )

        # Pick HD quality (not 4K to save bandwidth, not SD for quality)
        for f in sorted_files:
            width = f.get("width", 0)
            height = f.get("height", 0)

            # For shorts, we want portrait or square
            if orientation == "portrait":
                if height >= width and width >= 720:
                    return f
            else:
                if width >= height and width >= 1280:
                    return f

        # Fallback to first available
        return sorted_files[0] if sorted_files else None

    def get_animal_video(self, animal_name: str) -> dict:
        """
        Get a video for a specific animal.
        Tries multiple search strategies.
        """
        # Try specific animal name first
        search_terms = [
            f"{animal_name} wildlife",
            f"{animal_name} nature",
            animal_name,
            f"{animal_name} animal"
        ]

        for term in search_terms:
            result = self.search_video(term, orientation="portrait", min_duration=8)
            if result:
                return result

        logger.warning(f"No Pexels video found for {animal_name}")
        return None


# Singleton instance
_client = None

def get_pexels_client() -> PexelsClient:
    """Get or create Pexels client instance"""
    global _client
    if _client is None:
        _client = PexelsClient()
    return _client
