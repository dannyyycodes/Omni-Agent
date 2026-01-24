"""
Workflow Scheduler
Uses APScheduler to run workflows on configurable schedules.
"""

import os
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger


class WorkflowScheduler:
    """Manages scheduled workflow execution."""
    
    def __init__(self, api_hub=None, model_router=None):
        self.scheduler = BackgroundScheduler()
        self.api_hub = api_hub
        self.model_router = model_router
        self.scheduled_jobs = {}
        self._load_schedules()
    
    def _load_schedules(self):
        """Load saved schedules from config file."""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.scheduled_jobs = json.load(f)
            except:
                self.scheduled_jobs = {}
    
    def _save_schedules(self):
        """Save schedules to config file."""
        config_path = self._get_config_path()
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.scheduled_jobs, f, indent=2)
    
    def _get_config_path(self):
        return os.path.join(os.path.dirname(__file__), '..', 'data', 'scheduler_config.json')
    
    def start(self):
        """Start the scheduler and activate all enabled jobs."""
        if self.scheduler.running:
            return
        
        # Add all enabled workflows
        for job_id, config in self.scheduled_jobs.items():
            if config.get('enabled', False):
                self._add_job(job_id, config)
        
        self.scheduler.start()
        print("🚀 Workflow Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            print("⏹️ Workflow Scheduler stopped")
    
    def _add_job(self, job_id, config):
        """Add a job to the scheduler."""
        workflow_type = config.get('workflow_type')
        interval_hours = config.get('interval_hours', 4)
        
        if workflow_type == 'animal_facts':
            self.scheduler.add_job(
                func=self._run_animal_facts,
                trigger=IntervalTrigger(hours=interval_hours),
                id=job_id,
                replace_existing=True,
                name=f"Animal Facts ({interval_hours}h)",
                max_instances=1
            )
    
    def _run_animal_facts(self):
        """Execute the Animal Facts workflow."""
        try:
            from workflows.animal_facts import AnimalFactsWorkflow
            
            if not os.environ.get('KIE_API_KEY'):
                print("⚠️ Scheduled Animal Facts skipped - missing KIE_API_KEY")
                return {'status': 'skipped', 'reason': 'missing API key'}
            
            workflow = AnimalFactsWorkflow(self.api_hub, self.model_router)
            result = workflow.run()
            
            # Log the result
            self._log_execution('animal_facts', result)
            
            return result
            
        except Exception as e:
            print(f"❌ Scheduled Animal Facts failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _log_execution(self, workflow_type, result):
        """Log workflow execution results."""
        log_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'scheduler_log.json')
        
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append({
                'timestamp': datetime.now().isoformat(),
                'workflow': workflow_type,
                'status': result.get('status', 'unknown'),
                'animal': result.get('animal'),
                'video': result.get('video')
            })
            
            # Keep only last 100 entries
            logs = logs[-100:]
            
            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"Failed to log execution: {e}")
    
    def schedule_animal_facts(self, interval_hours=4, enabled=True):
        """
        Schedule the Animal Facts workflow.
        Default: Every 4 hours = 6 posts per day.
        """
        job_id = 'animal_facts_auto'
        
        config = {
            'workflow_type': 'animal_facts',
            'interval_hours': interval_hours,
            'enabled': enabled,
            'created_at': datetime.now().isoformat()
        }
        
        self.scheduled_jobs[job_id] = config
        self._save_schedules()
        
        if enabled and self.scheduler.running:
            self._add_job(job_id, config)
            print(f"✅ Animal Facts scheduled every {interval_hours} hours")
        elif not enabled:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            print(f"⏸️ Animal Facts schedule disabled")
        
        return config
    
    def get_schedules(self):
        """Get all scheduled workflows."""
        schedules = []
        for job_id, config in self.scheduled_jobs.items():
            schedules.append({
                'id': job_id,
                'workflow': config.get('workflow_type'),
                'interval_hours': config.get('interval_hours'),
                'enabled': config.get('enabled', False),
                'posts_per_day': 24 // config.get('interval_hours', 4)
            })
        return schedules
    
    def toggle_schedule(self, job_id, enabled=None):
        """Enable or disable a scheduled workflow."""
        if job_id not in self.scheduled_jobs:
            return {'error': 'Schedule not found'}
        
        config = self.scheduled_jobs[job_id]
        
        # Toggle if enabled not specified
        if enabled is None:
            enabled = not config.get('enabled', False)
        
        config['enabled'] = enabled
        self._save_schedules()
        
        if enabled and self.scheduler.running:
            self._add_job(job_id, config)
        else:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
        
        return {
            'id': job_id,
            'enabled': enabled,
            'message': f"Schedule {'enabled' if enabled else 'disabled'}"
        }
    
    def get_logs(self, limit=20):
        """Get recent execution logs."""
        log_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'scheduler_log.json')
        
        try:
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    logs = json.load(f)
                return logs[-limit:]
        except:
            pass
        
        return []


# Global scheduler instance
scheduler = None

def get_scheduler(api_hub=None, model_router=None):
    """Get or create the global scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = WorkflowScheduler(api_hub, model_router)
    return scheduler

def init_scheduler(api_hub=None, model_router=None):
    """Initialize and start the scheduler."""
    global scheduler
    scheduler = WorkflowScheduler(api_hub, model_router)
    scheduler.start()
    return scheduler
