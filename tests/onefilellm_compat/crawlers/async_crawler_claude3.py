"""Async crawler compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import crawl_and_extract_text

class AsyncWebCrawler:
    """Async web crawler"""
    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.kwargs = kwargs
        # Set defaults
        if 'max_depth' not in self.kwargs:
            self.kwargs['max_depth'] = 3
        if 'include_pdfs' not in self.kwargs:
            self.kwargs['include_pdfs'] = False
        if 'ignore_epubs' not in self.kwargs:
            self.kwargs['ignore_epubs'] = True
    
    async def crawl(self, progress_bar=None):
        result = crawl_and_extract_text(self.base_url, **self.kwargs)
        # Return just the content part
        if isinstance(result, dict) and 'content' in result:
            return result['content']
        return result

__all__ = ['AsyncWebCrawler']