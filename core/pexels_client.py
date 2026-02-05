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
                return self._broader_search(query, orientation, min_duration, headers)

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

    def _broader_search(self, query: str, orientation: str, min_duration: int, headers: dict) -> dict:
        """Try broader search terms if specific search fails - still filters for REAL wildlife"""
        # Extract main animal word and try variations with "real wildlife" focus
        words = query.lower().split()
        animal_word = words[0] if words else query

        broader_terms = [
            f"{animal_word} wild nature",
            f"{animal_word} wildlife documentary",
            f"{animal_word} in nature",
            "wildlife documentary",
            "wild animals nature",
            "safari wildlife"
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

    def get_animal_video(self, animal_name: str, fallback_to_other_animal: bool = True) -> dict:
        """
        Get a REAL wildlife video for a specific animal.
        Only returns actual nature footage - no puppets, cartoons, or fake content.

        Args:
            animal_name: Name of the animal to search for
            fallback_to_other_animal: If True, will try generic wildlife if animal not found

        Returns:
            dict with video info or None if no REAL wildlife found
        """
        logger.info(f"Searching for REAL {animal_name} wildlife footage...")

        # Search terms optimized for REAL wildlife (not toys/puppets/cartoons)
        search_terms = [
            f"{animal_name} wild nature",
            f"{animal_name} wildlife documentary",
            f"{animal_name} in habitat",
            f"wild {animal_name}",
            f"{animal_name} safari",
            f"{animal_name} zoo",  # Zoo footage is still real
        ]

        for term in search_terms:
            result = self.search_video(term, orientation="portrait", min_duration=8)
            if result:
                logger.info(f"Found REAL wildlife video for {animal_name}")
                return result

        # If specific animal not found and fallback enabled, try generic wildlife
        if fallback_to_other_animal:
            logger.warning(f"No real footage for {animal_name}, trying generic wildlife...")
            generic_terms = [
                "wildlife documentary nature",
                "wild animals safari",
                "nature documentary animals",
                "rainforest wildlife",
                "ocean wildlife"
            ]
            for term in generic_terms:
                result = self.search_video(term, orientation="portrait", min_duration=8)
                if result:
                    logger.info(f"Using generic wildlife footage instead of {animal_name}")
                    return result

        logger.warning(f"No REAL Pexels video found for {animal_name}")
        return None


# Singleton instance
_client = None

def get_pexels_client() -> PexelsClient:
    """Get or create Pexels client instance"""
    global _client
    if _client is None:
        _client = PexelsClient()
    return _client
