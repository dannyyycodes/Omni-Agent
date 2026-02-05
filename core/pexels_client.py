"""
Pexels Video Client - Fetches stock wildlife footage
Used as fallback when Sora is unavailable

IMPORTANT: Only returns REAL wildlife footage - no puppets, cartoons, animations, toys
"""

import os
import requests
import logging
import random

logger = logging.getLogger(__name__)

# Keywords that indicate FAKE content (puppets, toys, cartoons, etc.)
FAKE_CONTENT_KEYWORDS = [
    'puppet', 'toy', 'plush', 'stuffed', 'cartoon', 'animation', 'animated',
    'drawing', 'illustration', 'sketch', 'art', 'painting', 'cgi', '3d',
    'render', 'digital', 'graphic', 'doll', 'figurine', 'model', 'miniature',
    'claymation', 'stop motion', 'mascot', 'costume', 'suit', 'fake'
]

# Keywords that indicate REAL wildlife footage
REAL_WILDLIFE_KEYWORDS = [
    'wildlife', 'wild', 'nature', 'documentary', 'safari', 'habitat',
    'forest', 'ocean', 'jungle', 'savanna', 'arctic', 'zoo', 'sanctuary',
    'national park', 'reserve', 'natural', 'outdoor'
]


class PexelsClient:
    """Fetch videos from Pexels API - ONLY real wildlife footage"""

    def __init__(self):
        self.api_key = os.environ.get('PEXELS_API_KEY')
        self.base_url = "https://api.pexels.com/videos"

    def is_available(self) -> bool:
        """Check if Pexels is configured"""
        return bool(self.api_key)

    def search_video(self, query: str, orientation: str = "portrait", min_duration: int = 8, animal_name: str = None) -> dict:
        """
        Search for a video matching the query.

        Args:
            query: Search term (e.g., "elephant wildlife")
            orientation: "portrait" for shorts, "landscape" for YouTube
            min_duration: Minimum video length in seconds
            animal_name: The specific animal we're searching for (used to prevent wrong animal fallbacks)

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
                # Try broader search with same animal
                logger.info(f"No results for '{query}', trying broader search...")
                return self._broader_search(query, orientation, min_duration, headers, animal_name)

            # Filter by duration AND ensure it's REAL wildlife footage
            suitable_videos = []
            for v in videos:
                if v.get("duration", 0) >= min_duration:
                    if self._is_real_wildlife(v):
                        suitable_videos.append(v)

            if not suitable_videos:
                # Second pass: check all videos regardless of duration
                for v in videos:
                    if self._is_real_wildlife(v):
                        suitable_videos.append(v)

            if not suitable_videos:
                logger.warning(f"No REAL wildlife videos found for '{query}', trying broader search...")
                return self._broader_search(query, orientation, min_duration, headers, animal_name)

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

    def _is_real_wildlife(self, video: dict) -> bool:
        """
        Check if a video appears to be REAL wildlife footage.
        Filters out puppets, toys, cartoons, animations, etc.
        """
        # Get all text content to check
        url = video.get("url", "").lower()
        user = video.get("user", {}).get("name", "").lower()

        # Check video files for suspicious URLs
        for vf in video.get("video_files", []):
            file_url = vf.get("link", "").lower()
            for keyword in FAKE_CONTENT_KEYWORDS:
                if keyword in file_url:
                    logger.debug(f"Filtered out video {video.get('id')}: '{keyword}' in URL")
                    return False

        # Check the Pexels URL for fake content keywords
        for keyword in FAKE_CONTENT_KEYWORDS:
            if keyword in url:
                logger.debug(f"Filtered out video {video.get('id')}: '{keyword}' in Pexels URL")
                return False

        # Check uploader name (some uploaders specialize in animations)
        animation_uploaders = ['animation', 'cartoon', 'puppet', 'toy', 'art', 'digital']
        for term in animation_uploaders:
            if term in user:
                logger.debug(f"Filtered out video {video.get('id')}: suspicious uploader '{user}'")
                return False

        # Video passed all checks
        return True

    def _broader_search(self, query: str, orientation: str, min_duration: int, headers: dict, animal_name: str = None) -> dict:
        """
        Try broader search terms if specific search fails.
        CRITICAL: Only searches for the SAME animal - NEVER returns a different animal.
        """
        # Extract main animal word
        words = query.lower().split()
        animal_word = animal_name.lower() if animal_name else (words[0] if words else query)

        # ONLY search for this specific animal - never generic wildlife
        broader_terms = [
            f"{animal_word}",
            f"{animal_word} animal",
            f"{animal_word} wild",
            f"{animal_word} nature",
            f"{animal_word} close up",
        ]

        for term in broader_terms:
            try:
                response = requests.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params={
                        "query": term,
                        "orientation": orientation,
                        "per_page": 20  # More results to filter from
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    videos = response.json().get("videos", [])

                    # Filter for REAL wildlife
                    real_videos = [v for v in videos if self._is_real_wildlife(v)]

                    if real_videos:
                        video = random.choice(real_videos)
                        video_files = video.get("video_files", [])
                        best_file = self._pick_best_file(video_files, orientation)

                        if best_file:
                            logger.info(f"Found real wildlife video via broader search: {term}")
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
        Get a REAL wildlife video for a specific animal.

        CRITICAL: Only returns video of the REQUESTED animal - NEVER a different animal.
        If no video found for this animal, returns None (workflow should pick different animal).

        Args:
            animal_name: Name of the animal to search for

        Returns:
            dict with video info or None if no video found for THIS SPECIFIC animal
        """
        logger.info(f"Searching for REAL {animal_name} wildlife footage (strict match)...")

        # Search terms - all MUST include the animal name
        search_terms = [
            f"{animal_name}",
            f"{animal_name} animal",
            f"{animal_name} wildlife",
            f"{animal_name} wild",
            f"{animal_name} nature",
            f"{animal_name} zoo",
            f"wild {animal_name}",
        ]

        for term in search_terms:
            result = self.search_video(term, orientation="portrait", min_duration=8, animal_name=animal_name)
            if result:
                logger.info(f"Found REAL wildlife video for {animal_name}")
                return result

        # NO FALLBACK - if we can't find this animal, return None
        # The workflow must choose a different animal
        logger.warning(f"No Pexels video found for {animal_name} - workflow should try different animal")
        return None


# Singleton instance
_client = None

def get_pexels_client() -> PexelsClient:
    """Get or create Pexels client instance"""
    global _client
    if _client is None:
        _client = PexelsClient()
    return _client
