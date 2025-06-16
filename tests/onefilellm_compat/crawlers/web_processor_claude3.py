"""Web processor compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import crawl_and_extract_text as _crawl_and_extract_text

class WebContentProcessor:
    """Processor for web content"""
    async def process_async(self, url, context=None):
        # Extract crawler arguments from context
        kwargs = context if context else {}
        # Remove non-crawler args
        kwargs.pop('console', None)
        kwargs.pop('progress_bar', None)
        
        # Default values for required args if not provided
        if 'max_depth' not in kwargs:
            kwargs['max_depth'] = 3
        if 'include_pdfs' not in kwargs:
            kwargs['include_pdfs'] = False
        if 'ignore_epubs' not in kwargs:
            kwargs['ignore_epubs'] = True
            
        result = _crawl_and_extract_text(url, **kwargs)
        # Return just the content part
        if isinstance(result, dict) and 'content' in result:
            return result['content']
        return result

# Export the original synchronous function for tests
crawl_and_extract_text = _crawl_and_extract_text

__all__ = ['WebContentProcessor', 'crawl_and_extract_text']