"""YouTube source processor compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import fetch_youtube_transcript

class YouTubeProcessor:
    """Processor for YouTube videos"""
    def process(self, video_url, context=None):
        return fetch_youtube_transcript(video_url)

__all__ = ['YouTubeProcessor']