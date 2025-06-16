"""Academic source processors compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import process_doi_or_pmid, process_arxiv_pdf, _process_pdf_content_from_path

class ArXivProcessor:
    """Processor for ArXiv papers"""
    def process(self, arxiv_url, context=None):
        # If it's an arxiv URL, use process_arxiv_pdf
        if "arxiv.org" in arxiv_url:
            return process_arxiv_pdf(arxiv_url)
        # Otherwise treat as identifier
        return process_doi_or_pmid(arxiv_url)

class DOIProcessor:
    """Processor for DOI papers"""
    def process(self, doi, context=None):
        return process_doi_or_pmid(doi)

class PMIDProcessor:
    """Processor for PubMed papers"""
    def process(self, pmid, context=None):
        return process_doi_or_pmid(pmid)

# Rename the internal function for compatibility
process_pdf_content_from_path = _process_pdf_content_from_path

__all__ = ['ArXivProcessor', 'DOIProcessor', 'PMIDProcessor', 'process_pdf_content_from_path']