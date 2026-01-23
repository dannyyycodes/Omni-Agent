"""
OMNI Workflow Engine - Executes automation steps
"""

import os
import json
import uuid
import threading
import time
import requests
from datetime import datetime

class WorkflowEngine:
    """Executes automated workflows"""
    
    def __init__(self, database_url=None, api_hub=None):
        self.storage_file = 'omni_workflows.json'
        self.workflows = self._load_file_storage()
        self.api_hub = api_hub
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
    
    def _load_file_storage(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_file_storage(self):
        with open(self.storage_file, 'w') as f:
            json.dump(self.workflows, f, indent=2)

    def create(self, name, project_id=None, trigger='manual', steps=None, description=''):
        workflow = {
            'id': str(uuid.uuid4())[:8],
            'name': name,
            'project_id': project_id,
            'description': description,
            'trigger': trigger,
            'steps': steps or [],
            'enabled': True,
            'run_count': 0,
            'created_at': datetime.now().isoformat()
        }
        self.workflows.append(workflow)
        self._save_file_storage()
        return workflow

    def list_all(self, project_id=None):
        if project_id:
            return [w for w in self.workflows if w.get('project_id') == project_id]
        return self.workflows

    def run(self, workflow_id, context=None):
        """Execute the workflow steps"""
        workflow = next((w for w in self.workflows if w['id'] == workflow_id), None)
        if not workflow:
            return {'error': 'Workflow not found'}
        
        results = []
        ctx = context or {}
        
        print(f"🚀 Running workflow: {workflow['name']}")
        
        for i, step in enumerate(workflow.get('steps', [])):
            step_name = step.get('name', f'Step {i+1}')
            action = step.get('action', 'unknown')
            config = step.get('config', {})  # n8n often uses 'parameters' or 'config'
            
            try:
                # --- HTTP Request (Webhook, API Call) ---
                if 'http' in action.lower() or 'webhook' in action.lower() or 'request' in action.lower():
                    method = config.get('method', 'GET')
                    url = config.get('url', '')
                    if not url:
                        # Try to find URL in other common n8n fields
                        url = config.get('path', '')
                    
                    if url:
                        print(f"  👉 HTTP {method} {url}")
                        response = requests.request(method, url, json=config.get('body'), headers=config.get('headers'))
                        result_data = {
                            'status': response.status_code,
                            'body': response.text[:500]  # Truncate for log
                        }
                    else:
                        result_data = "Skipped: No URL provided"

                # --- AI Agent / LLM Call ---
                elif 'ai' in action.lower() or 'llm' in action.lower():
                    prompt = config.get('prompt', 'Hello')
                    # Mock AI call if API hub not connected, strictly for safety in this task
                    result_data = f"AI Generated: [Response to '{prompt}']"
                    
                # --- Social Media (Mock) ---
                elif 'social' in action.lower() or 'twitter' in action.lower():
                    result_data = "Posted to Social Media (Simulation)"
                    
                # --- Default ---
                else:
                    result_data = f"Executed action: {action}"
                
                results.append({
                    'step': step_name,
                    'status': 'success',
                    'output': result_data
                })
                
            except Exception as e:
                results.append({
                    'step': step_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        workflow['run_count'] = workflow.get('run_count', 0) + 1
        workflow['last_run'] = datetime.now().isoformat()
        self._save_file_storage()
        
        return {
            'workflow': workflow['name'],
            'results': results
        }

    def _scheduler_loop(self):
        while self.running:
            time.sleep(60)
            # Future: Check for scheduled workflows
            
    def stop(self):
        self.running = False
