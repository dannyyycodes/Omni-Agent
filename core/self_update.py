"""
OMNI Self-Updater - Actually pushes code to GitHub for auto-deployment
"""

import os
import re
import json
import base64
import requests
from datetime import datetime


class SelfUpdater:
    """
    Allows OMNI to modify its own code and deploy updates
    Uses GitHub API to push changes, Railway auto-deploys
    """
    
    def __init__(self, api_hub):
        self.api_hub = api_hub
        self.repo_owner = os.environ.get('GITHUB_OWNER', '')
        self.repo_name = os.environ.get('GITHUB_REPO', 'omni-ai-agent')
        self.branch = os.environ.get('GITHUB_BRANCH', 'main')
    
    def _get_github_token(self):
        """Get GitHub token"""
        token = self.api_hub.get_key('github') if self.api_hub else None
        return token or os.environ.get('GITHUB_TOKEN', '')
    
    def _github_api(self, endpoint, method='GET', data=None):
        """Make GitHub API request"""
        token = self._get_github_token()
        if not token:
            return {'error': 'GitHub token not configured'}
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        url = f"https://api.github.com{endpoint}"
        
        try:
            if method == 'GET':
                r = requests.get(url, headers=headers, timeout=30)
            elif method == 'PUT':
                r = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == 'POST':
                r = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                return {'error': f'Unknown method: {method}'}
            
            if r.status_code in [200, 201]:
                return r.json()
            else:
                return {'error': f'GitHub API error {r.status_code}: {r.text[:500]}'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_file(self, path):
        """Get file content from repo"""
        if not self.repo_owner:
            return {'error': 'GITHUB_OWNER not set'}
        
        result = self._github_api(f'/repos/{self.repo_owner}/{self.repo_name}/contents/{path}')
        
        if 'content' in result:
            try:
                result['decoded'] = base64.b64decode(result['content']).decode('utf-8')
            except:
                pass
        
        return result
    
    def update_file(self, path, new_content, commit_message):
        """Update a file in the repo"""
        if not self.repo_owner:
            return {'error': 'GITHUB_OWNER not set in Railway variables'}
        
        # Get current file to get SHA
        current = self.get_file(path)
        sha = current.get('sha')
        
        # Encode content
        encoded = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        data = {
            'message': commit_message,
            'content': encoded,
            'branch': self.branch
        }
        
        if sha:
            data['sha'] = sha
        
        result = self._github_api(
            f'/repos/{self.repo_owner}/{self.repo_name}/contents/{path}',
            'PUT',
            data
        )
        
        return result
    
    def get_repo_info(self):
        """Get repo information"""
        if not self.repo_owner:
            return {'error': 'GITHUB_OWNER not set'}
        
        return self._github_api(f'/repos/{self.repo_owner}/{self.repo_name}')
    
    def list_files(self, path=''):
        """List files in repo"""
        if not self.repo_owner:
            return {'error': 'GITHUB_OWNER not set'}
        
        return self._github_api(f'/repos/{self.repo_owner}/{self.repo_name}/contents/{path}')
    
    def full_update(self, file_path, new_code, feature_description):
        """
        Complete update process:
        1. Update file on GitHub
        2. Railway auto-deploys from GitHub
        """
        commit_msg = f"🔄 OMNI Self-Update: {feature_description[:50]}"
        
        result = self.update_file(file_path, new_code, commit_msg)
        
        if 'error' in result:
            return {
                'success': False,
                'error': result['error']
            }
        
        return {
            'success': True,
            'message': f"✅ Code pushed to GitHub!\n\nFile: {file_path}\nCommit: {commit_msg}\n\nRailway will auto-deploy in ~60 seconds.",
            'commit_url': result.get('commit', {}).get('html_url', '')
        }
    
    def check_connection(self):
        """Verify GitHub connection works"""
        token = self._get_github_token()
        
        if not token:
            return {
                'connected': False,
                'error': 'No GitHub token. Add GITHUB_TOKEN to Railway variables.'
            }
        
        if not self.repo_owner:
            return {
                'connected': False,
                'error': 'No repo owner. Add GITHUB_OWNER to Railway variables.'
            }
        
        # Test API access
        result = self._github_api('/user')
        
        if 'error' in result:
            return {
                'connected': False,
                'error': result['error']
            }
        
        # Test repo access
        repo_result = self.get_repo_info()
        
        if 'error' in repo_result:
            return {
                'connected': False,
                'error': f"Can't access repo: {repo_result['error']}"
            }
        
        return {
            'connected': True,
            'user': result.get('login'),
            'repo': f"{self.repo_owner}/{self.repo_name}",
            'message': f"✅ GitHub connected as {result.get('login')}. Repo: {self.repo_owner}/{self.repo_name}"
        }
