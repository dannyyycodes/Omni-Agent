"""
OMNI Model Router - Uses Claude 3.5 Sonnet via OpenRouter (best available model)
"""

import os
import requests


class ModelRouter:
    """Routes requests to AI models via OpenRouter"""
    
    def __init__(self, api_hub):
        self.api_hub = api_hub
        # Use Claude 3.5 Sonnet - best coding/reasoning model
        self.default_model = 'anthropic/claude-3.5-sonnet'
        self.fallback_model = 'anthropic/claude-3-haiku'
    
    def _get_api_key(self):
        """Get OpenRouter API key"""
        if self.api_hub:
            key = self.api_hub.get_key('openrouter')
            if key:
                return key
        return os.environ.get('OPENROUTER_API_KEY', '')
    
    def complete(self, prompt, system=None, model=None, max_tokens=4000, temperature=0.7):
        """Make a completion request via OpenRouter"""
        key = self._get_api_key()
        
        if not key:
            return "Error: No OpenRouter API key. Add OPENROUTER_API_KEY to environment variables."
        
        model = model or self.default_model
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'https://omni.up.railway.app'),
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                # Try fallback model
                if model != self.fallback_model:
                    return self.complete(prompt, system, self.fallback_model, max_tokens, temperature)
                return f"API Error: {response.status_code} - {response.text[:200]}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def list_available(self):
        """List available models"""
        return [
            {'id': 'anthropic/claude-3.5-sonnet', 'name': 'Claude 3.5 Sonnet', 'best_for': 'coding, reasoning'},
            {'id': 'anthropic/claude-3-opus', 'name': 'Claude 3 Opus', 'best_for': 'complex tasks'},
            {'id': 'anthropic/claude-3-haiku', 'name': 'Claude 3 Haiku', 'best_for': 'fast, cheap'},
            {'id': 'openai/gpt-4-turbo', 'name': 'GPT-4 Turbo', 'best_for': 'general'},
            {'id': 'openai/gpt-4o', 'name': 'GPT-4o', 'best_for': 'multimodal'},
        ]
    
    def get_default(self):
        return {'model': self.default_model}
    
    def set_default(self, model):
        self.default_model = model
        return True
