"""
OMNI Web Agent - Browser automation and web scraping
"""

import os
import re
import json
import hashlib
import requests
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class WebAgent:
    """Web automation agent for scraping, monitoring, and browser tasks"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch(self, url, method='GET', data=None, headers=None):
        """Fetch a URL"""
        try:
            if method.upper() == 'GET':
                r = self.session.get(url, headers=headers, timeout=30)
            else:
                r = self.session.post(url, data=data, headers=headers, timeout=30)
            return {'success': True, 'status': r.status_code, 'content': r.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def scrape(self, url, selectors=None):
        """Scrape data from a webpage"""
        if not HAS_BS4:
            return {'error': 'BeautifulSoup not installed. Run: pip install beautifulsoup4'}
        
        result = self.fetch(url)
        if not result.get('success'):
            return result
        
        soup = BeautifulSoup(result['content'], 'html.parser')
        
        if not selectors:
            return {
                'success': True,
                'title': soup.title.string if soup.title else '',
                'text': soup.get_text(separator='\n', strip=True)[:10000]
            }
        
        data = {}
        for name, selector in selectors.items():
            elements = soup.select(selector)
            data[name] = [el.get_text(strip=True) for el in elements]
        
        return {'success': True, 'data': data}
    
    def scrape_table(self, url, table_selector='table'):
        """Scrape tabular data"""
        if not HAS_BS4:
            return {'error': 'BeautifulSoup not installed'}
        
        result = self.fetch(url)
        if not result.get('success'):
            return result
        
        soup = BeautifulSoup(result['content'], 'html.parser')
        table = soup.select_one(table_selector)
        
        if not table:
            return {'success': False, 'error': 'Table not found'}
        
        rows = []
        headers = []
        
        header_row = table.select_one('thead tr') or table.select_one('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.select('th, td')]
        
        for row in table.select('tbody tr, tr')[1:]:
            cells = [td.get_text(strip=True) for td in row.select('td')]
            if cells:
                rows.append(dict(zip(headers, cells)) if headers else cells)
        
        return {'success': True, 'headers': headers, 'rows': rows}
    
    def find_links(self, url, pattern=None):
        """Find all links on a page"""
        if not HAS_BS4:
            return {'error': 'BeautifulSoup not installed'}
        
        result = self.fetch(url)
        if not result.get('success'):
            return result
        
        soup = BeautifulSoup(result['content'], 'html.parser')
        
        links = []
        for a in soup.select('a[href]'):
            href = a.get('href', '')
            absolute_url = urljoin(url, href)
            
            if pattern and not re.search(pattern, absolute_url):
                continue
            
            links.append({'url': absolute_url, 'text': a.get_text(strip=True)[:100]})
        
        return {'success': True, 'links': links}
    
    def monitor_page(self, url, selector=None, last_hash=None):
        """Check if a page has changed"""
        if selector:
            result = self.scrape(url, {'target': selector})
            content = str(result.get('data', {}).get('target', ''))
        else:
            result = self.fetch(url)
            content = result.get('content', '')
        
        if not content:
            return {'success': False, 'error': 'Could not fetch page'}
        
        current_hash = hashlib.md5(content.encode()).hexdigest()
        
        return {
            'success': True,
            'changed': last_hash is not None and current_hash != last_hash,
            'hash': current_hash
        }
    
    def search_google(self, query, num_results=10):
        """Search Google (basic implementation)"""
        # Note: For production, use Google Custom Search API
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num_results}"
        
        result = self.fetch(url)
        if not result.get('success'):
            return result
        
        if not HAS_BS4:
            return {'error': 'BeautifulSoup not installed'}
        
        soup = BeautifulSoup(result['content'], 'html.parser')
        
        results = []
        for div in soup.select('div.g'):
            link = div.select_one('a')
            title = div.select_one('h3')
            snippet = div.select_one('div.VwiC3b')
            
            if link and title:
                results.append({
                    'title': title.get_text(strip=True),
                    'url': link.get('href', ''),
                    'snippet': snippet.get_text(strip=True) if snippet else ''
                })
        
        return {'success': True, 'results': results[:num_results]}
    
    def download_file(self, url, save_path=None):
        """Download a file"""
        try:
            r = self.session.get(url, stream=True, timeout=60)
            
            if not save_path:
                filename = url.split('/')[-1].split('?')[0] or 'download'
                save_path = f'/tmp/{filename}'
            
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {'success': True, 'path': save_path, 'size': os.path.getsize(save_path)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def screenshot(self, url, save_path=None):
        """Take a screenshot (requires external service or Playwright)"""
        # Using a free screenshot API as fallback
        api_url = f"https://api.screenshotone.com/take?url={requests.utils.quote(url)}&format=png"
        
        return {
            'success': True,
            'message': 'Screenshot capability requires Playwright. Install with: pip install playwright && playwright install',
            'alternative_url': api_url
        }
