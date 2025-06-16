"""GitHub source processors compatibility module"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from onefilellm import process_github_repo, process_github_pull_request, process_github_issue

class GitHubRepoProcessor:
    """Processor for GitHub repositories"""
    def process(self, repo_url, context=None):
        github_token = context.get('github_token') if context else None
        # The original function uses the global TOKEN, so we need to temporarily set it
        old_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            os.environ['GITHUB_TOKEN'] = github_token
        try:
            result = process_github_repo(repo_url)
            return result
        finally:
            if old_token:
                os.environ['GITHUB_TOKEN'] = old_token
            elif github_token:
                del os.environ['GITHUB_TOKEN']

class GitHubPRProcessor:
    """Processor for GitHub pull requests"""
    def process(self, pr_url, context=None):
        github_token = context.get('github_token') if context else None
        # Set token temporarily
        old_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            os.environ['GITHUB_TOKEN'] = github_token
        try:
            return process_github_pull_request(pr_url)
        finally:
            if old_token:
                os.environ['GITHUB_TOKEN'] = old_token
            elif github_token:
                del os.environ['GITHUB_TOKEN']

class GitHubIssueProcessor:
    """Processor for GitHub issues"""
    def process(self, issue_url, context=None):
        github_token = context.get('github_token') if context else None
        # Set token temporarily
        old_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            os.environ['GITHUB_TOKEN'] = github_token
        try:
            return process_github_issue(issue_url)
        finally:
            if old_token:
                os.environ['GITHUB_TOKEN'] = old_token
            elif github_token:
                del os.environ['GITHUB_TOKEN']

__all__ = ['GitHubRepoProcessor', 'GitHubPRProcessor', 'GitHubIssueProcessor']