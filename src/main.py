#!/usr/bin/env python3
"""
GitHub Action: AI-powered Helm values generator
"""

import os
import sys
import json
import yaml
import requests
from typing import Dict, Any, Optional, List

class GitHubActionAIGenerator:
    def __init__(self):
        # Get inputs from GitHub Action environment
        self.app_name = os.getenv('INPUT_APP_NAME')
        self.environment = os.getenv('INPUT_ENVIRONMENT')
        self.current_values = os.getenv('INPUT_CURRENT_VALUES')
        self.operational_context = os.getenv('INPUT_OPERATIONAL_CONTEXT')
        self.helm_templates = json.loads(os.getenv('INPUT_HELM_TEMPLATES', '[]'))
        self.ai_provider = os.getenv('INPUT_AI_PROVIDER', 'copilot')
        self.ai_token = os.getenv('INPUT_AI_TOKEN')
        self.ai_model = os.getenv('INPUT_AI_MODEL')
        
        if not all([self.app_name, self.environment, self.current_values, self.operational_context]):
            self.error("Missing required inputs")
    
    def error(self, message: str):
        """Output error and exit"""
        print(f"::error::{message}")
        sys.exit(1)
    
    def output(self, name: str, value: str):
        """Set GitHub Action output"""
        print(f"::set-output name={name}::{value}")
    
    def run(self):
        """Main action execution"""
        print(f"🤖 Generating values for {self.app_name} in {self.environment}")
        
        try:
            # Parse inputs
            current_values = yaml.safe_load(self.current_values)
            operational_data = yaml.safe_load(self.operational_context)
            
            # Generate AI analysis context
            context = self.build_analysis_context(current_values, operational_data)
            
            # Generate recommendations
            recommendations = self.generate_ai_recommendations(context)
            
            if not recommendations:
                self.error("Failed to generate AI recommendations")
            
            # Apply recommendations to current values
            updated_values = self.apply_recommendations(current_values, recommendations)
            
            # Generate outputs
            generated_yaml = yaml.dump(updated_values, default_flow_style=False, sort_keys=False)
            changes = self.summarize_changes(current_values, updated_values)
            
            # Set outputs
            self.output('generated_values', generated_yaml)
            self.output('ai_analysis', recommendations.get('analysis', ''))
            self.output('changes_summary', changes)
            
            print("✅ Successfully generated optimized values.yaml")
            
        except Exception as e:
            self.error(f"Action failed: {str(e)}")
    
    def build_analysis_context(self, current_values: Dict, operational_data: Dict) -> str:
        """Build context for AI analysis"""
        context_parts = [
            f"APPLICATION: {self.app_name}",
            f"ENVIRONMENT: {self.environment}",
            "",
            "CURRENT VALUES:",
            yaml.dump(current_values, default_flow_style=False),
            "",
            "OPERATIONAL CONTEXT:",
            yaml.dump(operational_data, default_flow_style=False)
        ]
        
        if self.helm_templates:
            context_parts.extend([
                "",
                "HELM TEMPLATES:",
                *self.helm_templates
            ])
        
        return "\n".join(context_parts)
    
    def generate_ai_recommendations(self, context: str) -> Optional[Dict[str, Any]]:
        """Generate AI recommendations"""
        prompt = f"""Analyze the operational problems and generate Helm values recommendations.

{context}

Based on the operational incidents, metrics, and current values, provide:
1. Analysis of current problems
2. Specific value recommendations to solve issues
3. Justification for each change

Respond in JSON format:
{{
  "analysis": "Detailed analysis of problems found",
  "recommendations": {{
    "resources.requests.cpu": "new_value",
    "resources.requests.memory": "new_value",
    "resources.limits.cpu": "new_value",
    "resources.limits.memory": "new_value",
    "autoscaling.minReplicas": new_number,
    "autoscaling.maxReplicas": new_number,
    "livenessProbe.config.initialDelaySeconds": new_number,
    "readinessProbe.config.initialDelaySeconds": new_number
  }},
  "justifications": {{
    "resources.limits.memory": "Reason for this change"
  }}
}}"""

        if self.ai_provider == 'copilot':
            return self.call_github_models(prompt)
        elif self.ai_provider == 'openai':
            return self.call_openai(prompt)
        else:
            self.error(f"Unsupported AI provider: {self.ai_provider}")
    
    def call_github_models(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call GitHub Models API"""
        if not self.ai_token:
            self.error("AI token required for GitHub Models")
        
        try:
            response = requests.post(
                'https://models.github.ai/inference/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.ai_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.ai_model or 'gpt-4o',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1000,
                    'temperature': 0.1
                },
                timeout=60
            )
            response.raise_for_status()
            
            ai_response = response.json()['choices'][0]['message']['content']
            return json.loads(ai_response)
            
        except Exception as e:
            print(f"::warning::GitHub Models API error: {e}")
            return None
    
    def call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI API"""
        if not self.ai_token:
            self.error("AI token required for OpenAI")
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.ai_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.ai_model or 'gpt-4',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1000,
                    'temperature': 0.1
                },
                timeout=60
            )
            response.raise_for_status()
            
            ai_response = response.json()['choices'][0]['message']['content']
            return json.loads(ai_response)
            
        except Exception as e:
            print(f"::warning::OpenAI API error: {e}")
            return None
    
    def apply_recommendations(self, current_values: Dict[str, Any], recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI recommendations to current values"""
        updated_values = current_values.copy()
        
        for path, value in recommendations.get('recommendations', {}).items():
            self.set_nested_value(updated_values, path, value)
        
        return updated_values
    
    def set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """Set nested dictionary value using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def summarize_changes(self, old_values: Dict[str, Any], new_values: Dict[str, Any]) -> str:
        """Summarize changes made"""
        changes = []
        
        def compare_dicts(old_dict, new_dict, prefix=""):
            for key, new_val in new_dict.items():
                path = f"{prefix}.{key}" if prefix else key
                old_val = old_dict.get(key)
                
                if isinstance(new_val, dict) and isinstance(old_val, dict):
                    compare_dicts(old_val, new_val, path)
                elif old_val != new_val:
                    changes.append(f"• {path}: {old_val} → {new_val}")
        
        compare_dicts(old_values, new_values)
        return "\n".join(changes) if changes else "No changes made"

if __name__ == '__main__':
    generator = GitHubActionAIGenerator()
    generator.run()