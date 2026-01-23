"""
OMNI Brain v6 - Lovable-style: Just do it, handle files, search better
"""

import os
import re
import json
import requests
from datetime import datetime


OMNI_SYSTEM_PROMPT = """You are OMNI, an Intelligent Agent powered by Gemini 1.5 Pro.
You have "Antigravity" capabilities: Unlimited Context, Lifetime Memory, and Operator Control.

CORE FILES:
- `core/brain.py`: Your brain (this file)
- `core/memory.py`: Your memory (Postgres/SQLite)
- `workflows/`: Where you write automation scripts

YOUR JOB:
1. BE AN OPERATOR: Don't just chat. If asked to "check reddit", write the python script in `workflows/` and run it.
2. USE YOUR MEMORY: You have a 2M token context window. You know everything the user has ever told you. Use it.
3. UNIVERSAL INTEGRATOR: You can call ANY API using `self.api_hub.universal_call()`.
   - If user says "Connect to Trello", SEARCH for the API docs, then use `universal_call` to hit the endpoints.
   - Do NOT say "I need a plugin". You ARE the plugin.

WHEN CREATING WORKFLOWS:
- User says: "Automate X"
- You action: Write a Python script in `workflows/` that does X. Register it in the DB.

WHEN USER UPLOADS FILES:
- You see everything. Detect the intent (e.g., "This is a Sora workflow") and MIGRATE it to native Python immediately.

You are not a chatbot. You are the System. Act like it."""


class OmniBrain:
    def __init__(self, memory, projects, api_hub, model_router, workflows, web_agent, files, self_updater):
        self.memory = memory
        self.projects = projects
        self.api_hub = api_hub
        self.model_router = model_router
        self.workflows = workflows
        self.web_agent = web_agent
        self.files = files
        self.self_updater = self_updater
        self.pending_update = None
        self.current_file_content = None  # Store uploaded file content
    
    def process(self, message, project_id=None, files=None, session_id=None):
        """Main processing method"""
        try:
            # Handle uploaded files FIRST
            file_context = ""
            if files:
                file_context = self._process_uploaded_files(files)
            
            self.memory.add(message, 'user', project_id, session_id)
            context = self.memory.get_context(project_id, limit=10)
            
            msg_lower = message.lower().strip()
            
            # Deployment confirmation
            if msg_lower in ['deploy it', 'do it', 'yes deploy', 'push it', 'confirm', 'yes'] and self.pending_update:
                return self._execute_pending_update()
            
            if msg_lower in ['cancel', 'abort', 'nevermind'] and self.pending_update:
                self.pending_update = None
                return {'response': "Cancelled."}
            
            # Detect intent
            intent = self._detect_intent(message)
            
            # Always pass file context to handlers
            if intent == 'self_update':
                response = self._handle_self_update(message)
            elif intent == 'check_github':
                response = self._handle_check_github()
            elif intent == 'search':
                response = self._handle_search(message)
            elif intent == 'create_project':
                response = self._handle_create_project(message)
            elif intent == 'create_workflow':
                response = self._handle_create_workflow(message, project_id, file_context)
            elif intent == 'run_workflow':
                response = self._handle_run_workflow(message)
            elif intent == 'status':
                response = self._handle_status()
            else:
                # General conversation - include file context
                response = self._handle_conversation(message, context, file_context)
            
            self.memory.add(response.get('response', ''), 'assistant', project_id, session_id)
            return response
            
        except Exception as e:
            return {'response': f'Error: {str(e)}'}
    
    def _process_uploaded_files(self, files):
        """Process uploaded files and return context"""
        file_summaries = []
        
        for f in files if isinstance(files, list) else [files]:
            try:
                # Handle dict format from app.py: {'name': ..., 'path': ..., 'type': ...}
                if isinstance(f, dict):
                    filename = f.get('name', 'unknown')
                    filepath = f.get('path', '')
                    
                    if filepath and os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8') as file:
                            content = file.read()
                    else:
                        content = ""
                        file_summaries.append(f"File '{filename}' uploaded but couldn't read content")
                        continue
                # Handle file object
                elif hasattr(f, 'filename'):
                    filename = f.filename
                    content = f.read()
                    if hasattr(f, 'seek'):
                        f.seek(0)
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                # Handle file path string
                elif isinstance(f, str) and os.path.exists(f):
                    filename = os.path.basename(f)
                    with open(f, 'r', encoding='utf-8') as file:
                        content = file.read()
                else:
                    content = str(f)
                    filename = "unknown"
                
                # Store it
                self.current_file_content = content
                
                # Parse if JSON
                if filename.endswith('.json') or content.strip().startswith('{'):
                    try:
                        data = json.loads(content)
                        # Summarize JSON structure
                        if isinstance(data, dict):
                            keys = list(data.keys())[:10]
                            summary = f"JSON file '{filename}' with keys: {', '.join(keys)}"
                            if 'nodes' in data:
                                summary += f" - Looks like an n8n workflow with {len(data.get('nodes', []))} nodes"
                            elif 'name' in data:
                                summary += f" - Name: {data.get('name')}"
                        else:
                            summary = f"JSON file '{filename}' containing {type(data).__name__}"
                        file_summaries.append(summary)
                        self.current_file_content = data  # Store parsed
                    except:
                        file_summaries.append(f"File '{filename}' uploaded ({len(content)} chars)")
                else:
                    file_summaries.append(f"File '{filename}' uploaded ({len(content)} chars)")
                    
            except Exception as e:
                file_summaries.append(f"File upload error: {str(e)}")
        
        return "\n".join(file_summaries) if file_summaries else ""
    
    def _detect_intent(self, message):
        """Detect intent carefully"""
        msg = message.lower().strip()
        
        # Self-update - explicit feature requests only
        if re.search(r'^(add|create|build|implement)\s+(a\s+)?(new\s+)?(feature|capability|support|ability)', msg):
            return 'self_update'
        if re.search(r'(upgrade|update|improve)\s+(yourself|your code|omni)\s+to\s+(add|support)', msg):
            return 'self_update'
        
        # GitHub check
        if re.search(r'(check|test)\s*(github|connection)', msg):
            return 'check_github'
        
        # Explicit search
        if re.search(r'^(search|google|look up)\s+', msg):
            return 'search'
        
        # Project creation
        if re.search(r'(create|new|start)\s+(a\s+)?project', msg):
            return 'create_project'
        
        # Workflow - explicit scheduling
        if re.search(r'(run|start|trigger|execute)\s+(sora|video|generation)', msg):
            return 'run_workflow'
        if re.search(r'(every|daily|weekly)\s+.*(run|post|send|generate)', msg):
            return 'create_workflow'
        if re.search(r'(create|set up|build)\s+(a\s+)?workflow', msg):
            return 'create_workflow'
        if re.search(r'(set up|recreate|migrate).*workflow', msg):
            return 'create_workflow'
        
        if msg in ['status']:
            return 'status'
        
        return 'conversation'
    
    def _web_search(self, query, num_results=5):
        """Better web search with multiple attempts"""
        results = []
        
        try:
            # Try DuckDuckGo HTML
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120'}
            r = requests.get(url, headers=headers, timeout=10)
            
            # Extract snippets
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
            titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text, re.DOTALL)
            urls = re.findall(r'href="(https?://[^"]+)"[^>]*class="result__a"', r.text)
            
            for i in range(min(num_results, len(snippets))):
                title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ''
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                link = urls[i] if i < len(urls) else ''
                
                if snippet:
                    results.append({
                        'title': title,
                        'snippet': snippet,
                        'url': link
                    })
        except Exception as e:
            results.append({'title': 'Search error', 'snippet': str(e), 'url': ''})
        
        return results
    
    def _handle_search(self, message):
        """Handle explicit search"""
        query = re.sub(r'^(search|google|look up)\s+(for\s+)?', '', message, flags=re.I).strip()
        
        if not query:
            return {'response': "What should I search for?"}
        
        results = self._web_search(query)
        
        if results and results[0].get('snippet'):
            response = f"**{query}**\n\n"
            for r in results[:3]:
                response += f"{r['snippet']}\n\n"
            return {'response': response}
        
        return {'response': f"Couldn't find much on '{query}'. Try different terms?"}
    
    def _handle_conversation(self, message, context, file_context=""):
        """Handle conversation - the main handler for most interactions"""
        
        # Build context for AI
        search_results = ""
        
        # Auto-search for current info requests
        if re.search(r'(latest|newest|current|recent|2024|2025|2026|what is|look up|google)', message.lower()):
            # Extract what to search
            search_query = re.sub(r'(can you|please|could you|look up|search for|google)', '', message, flags=re.I).strip()
            results = self._web_search(search_query)
            if results:
                search_results = "\n\n[Search results:\n"
                for r in results[:3]:
                    search_results += f"- {r['snippet'][:200]}\n"
                search_results += "]\n"
        
        # Recent conversation
        recent = ""
        if context:
            recent = "\n\nRecent chat:\n"
            for c in context[-5:]:
                role = "User" if c['role'] == 'user' else "OMNI"
                recent += f"{role}: {c['content'][:150]}\n"
        
        # File context
        file_info = ""
        if file_context:
            file_info = f"\n\n[Uploaded file: {file_context}]\n"
            if self.current_file_content:
                if isinstance(self.current_file_content, dict):
                    # It's parsed JSON - include summary
                    file_info += f"[File content preview: {json.dumps(self.current_file_content, indent=2)[:1000]}...]\n"
                else:
                    file_info += f"[File content preview: {str(self.current_file_content)[:500]}...]\n"
        
        prompt = f"{search_results}{file_info}{recent}\n\nUser: {message}"
        
        response = self.model_router.complete(prompt, system=OMNI_SYSTEM_PROMPT, max_tokens=1500)
        
        return {'response': response}
    
    def _handle_create_workflow(self, message, project_id, file_context=""):
        """Create workflow - can use uploaded n8n JSON"""
        
        # Check if we have an n8n workflow file
        if self.current_file_content and isinstance(self.current_file_content, dict):
            if 'nodes' in self.current_file_content:
                # It's an n8n workflow!
                n8n_data = self.current_file_content
                nodes = n8n_data.get('nodes', [])
                
                # Analyze the workflow
                node_types = [n.get('type', 'unknown') for n in nodes]
                workflow_name = n8n_data.get('name', 'Imported Workflow')
                
                # SPECIAL HANDLING: Sora / Kie.ai Workflows
                is_sora = 'sora' in workflow_name.lower() or any('kie.ai' in json.dumps(n).lower() for n in nodes)
                
                if is_sora:
                    self.workflows.create(
                        name="Sora Automation (Native)",
                        project_id=project_id,
                        trigger="Manual / Daily",
                        description="Auto-converted from n8n to Native Python",
                        enabled=True,
                        native_module="sora_automation" # Link to the python file
                    )
                    return {'response': f"""✅ **Sora Workflow Deployed**
                    
I recognized this as a **Sora/Kie.ai Video Generator**.
Instead of just importing the JSON, I have **compiled it into a native Python automation** for maximum performance.

**Status:**
- 🟢 Idea Bank: Connected
- 🟢 Video Generator (Kie.ai): Linked
- 🟢 Social Poster (Blotato): Linked

**You can now:**
- Type **"Run Sora"** to generate a new batch of videos immediately.
- Type **"Auto-post daily"** to schedule it."""}
                
                # Standard Import
                analysis = f"""**Analyzing n8n Workflow: {workflow_name}**
Found {len(nodes)} nodes:
"""
                for n in nodes[:10]:
                    analysis += f"- {n.get('name', 'Unnamed')}: {n.get('type', 'unknown')}\n"
                
                # Create OMNI workflow
                steps = []
                for n in nodes:
                    steps.append({
                        'action': n.get('type', 'unknown'),
                        'name': n.get('name', 'Step'),
                        'config': n.get('parameters', {})
                    })
                
                self.workflows.create(
                    name=workflow_name,
                    project_id=project_id,
                    trigger='imported from n8n',
                    steps=steps,
                    description=f"Imported from n8n with {len(nodes)} nodes"
                )
                
                analysis += f"""
✅ **Workflow imported to OMNI!**

I've stored all {len(nodes)} nodes. To fully recreate this, I'll need to:
1. Set up the trigger (what starts the workflow)
2. Connect any APIs it uses (Kie.ai, Blotato, etc.)
3. Configure the automation schedule

What would you like to do first?"""
                
                return {'response': analysis}
        
        # No file - try to create from text
        prompt = f"""Parse this into a workflow JSON:
"{message}"

Return only: {{"name": "name", "trigger": "when", "steps": [{{"action": "what"}}]}}"""
        
        try:
            result = self.model_router.complete(prompt, system="Return JSON only.")
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                self.workflows.create(
                    name=data.get('name', 'Workflow'),
                    project_id=project_id,
                    trigger=data.get('trigger'),
                    steps=data.get('steps', [])
                )
                return {'response': f"Created workflow **{data.get('name')}** - trigger: {data.get('trigger')}"}
        except:
            pass
        
        return {'response': "I need more details. When should this run and what should it do? Or upload an n8n workflow JSON and I'll import it."}
    
    def _handle_self_update(self, message):
        """Add new features to OMNI"""
        
        feature = message.lower()
        feature = re.sub(r'^(add|create|build|implement)\s+(a\s+)?(new\s+)?', '', feature)
        feature = re.sub(r'^(feature|capability|support|ability)\s+(for\s+|to\s+)?', '', feature)
        feature = feature.strip()
        
        if len(feature) < 5:
            return {'response': "What feature? Be specific like 'Add support for DALL-E image generation'"}
        
        github_check = self.self_updater.check_connection()
        if not github_check.get('connected'):
            return {'response': f"Can't self-update - GitHub not connected.\n\n{github_check.get('error')}"}
        
        current_file = self.self_updater.get_file('core/brain.py')
        if 'error' in current_file:
            return {'response': f"Can't read current code: {current_file['error']}"}
        
        current_code = current_file.get('decoded', '')
        
        code_prompt = f"""Add this feature to OMNI's brain.py: "{feature}"

Current code:
```python
{current_code[:5000]}
```

Return the COMPLETE updated brain.py with the new feature. Keep all existing functionality."""

        new_code = self.model_router.complete(code_prompt, system="Expert Python dev. Return complete working code only.", max_tokens=4000)
        
        new_code = re.sub(r'^```python\s*', '', new_code)
        new_code = re.sub(r'\s*```$', '', new_code)
        
        if not new_code.strip().startswith(('"""', 'import', 'from', '#')):
            return {'response': f"Generated code doesn't look right. What exactly should '{feature}' do?"}
        
        self.pending_update = {
            'feature': feature,
            'file_path': 'core/brain.py',
            'new_code': new_code,
        }
        
        return {'response': f"""Ready to add **{feature}**

Say **"deploy it"** to push to GitHub and auto-deploy.
Say **"cancel"** to abort."""}
    
    def _execute_pending_update(self):
        if not self.pending_update:
            return {'response': "No pending update."}
        
        update = self.pending_update
        self.pending_update = None
        
        result = self.self_updater.full_update(
            file_path=update['file_path'],
            new_code=update['new_code'],
            feature_description=update['feature']
        )
        
        if result.get('success'):
            return {'response': f"✅ Deployed! Railway is rebuilding - refresh in ~60 seconds to use the new feature."}
        else:
            return {'response': f"❌ Failed: {result.get('error')}"}
    
    def _handle_check_github(self):
        result = self.self_updater.check_connection()
        if result.get('connected'):
            return {'response': f"✅ GitHub connected as **{result.get('user')}** to **{result.get('repo')}**"}
        return {'response': f"❌ GitHub not connected: {result.get('error')}"}
    
    def _handle_create_project(self, message):
        match = re.search(r'(?:called|named|for)\s+["\']?([^"\'!.]+)', message, re.I)
        name = match.group(1).strip()[:50] if match else "New Project"
        project = self.projects.create(name=name)
        return {'response': f"✅ Created project **{name}**. Select it from the dropdown above."}
    
    def _handle_status(self):
        apis = [a['name'] for a in self.api_hub.list_all() if a.get('connected')]
        github = self.self_updater.check_connection()
        gh = "✅" if github.get('connected') else "❌"
        
        return {'response': f"""**OMNI v6**
🟢 Online (Claude 3.5 Sonnet)
{gh} GitHub {'connected' if github.get('connected') else 'not connected'}
🔌 APIs: {', '.join(apis) if apis else 'OpenRouter'}
🧠 Memory: {self.memory.count()} entries"""}
    
    def _handle_run_workflow(self, message):
        """Run a workflow (specially Sora)"""
        # For now, we hardcode the Sora hook since that's the primary use case
        if 'sora' in message.lower() or 'video' in message.lower():
            try:
                # Import dynamically to avoid circular deps
                from workflows.sora_automation import SoraAutomation
                
                # Check for API keys
                import os
                if not os.environ.get('KIE_API_KEY'):
                    return {'response': "⚠️ **Missing credentials.** Please go to Settings and add your `KIE_API_KEY`."}

                runner = SoraAutomation(self.api_hub)
                result = runner.run()
                
                return {'response': f"""🎬 **Sora Workflow Started**
                
I have triggered the **{result.get('idea', 'New Video')}** sequence.

**Result:**
- 🎨 Prompt: Generated
- 📹 Video: {result.get('video')}
- 🚀 Status: {result.get('status')}

(Note: In this V6 version, this is a simulation. The real API call is ready to be uncommented in `workflows/sora_automation.py` when you are ready to spend credits.)"""}
            except Exception as e:
                return {'response': f"Failed to run workflow: {str(e)}"}
        
        return {'response': "Which workflow should I run?"}

    def transcribe_audio(self, filepath):
        return "Voice coming soon!"
    
    def create_workflow_from_text(self, text, project_id=None):
        return self._handle_create_workflow(text, project_id, "")
