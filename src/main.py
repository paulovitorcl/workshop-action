#!/usr/bin/env python3
"""
GitHub Action: AI-powered Helm values generator
"""

import os
import sys
import json
import yaml
import requests
import base64
from typing import Dict, Any, Optional, List

class GitHubActionAIGenerator:
    def __init__(self):
        # Get inputs from GitHub Action environment
        self.app_name = os.getenv('INPUT_APP_NAME')
        self.environment = os.getenv('INPUT_ENVIRONMENT')
        
        # Decode base64 inputs
        self.current_values = self.decode_base64_input('INPUT_CURRENT_VALUES')
        self.operational_context = self.decode_base64_input('INPUT_OPERATIONAL_CONTEXT')
        
        # Safely handle helm_templates input (also base64 encoded)
        helm_templates_raw = self.decode_base64_input('INPUT_HELM_TEMPLATES')
        try:
            if not helm_templates_raw or helm_templates_raw.strip() == '':
                self.helm_templates = []
            else:
                self.helm_templates = json.loads(helm_templates_raw)
        except json.JSONDecodeError as e:
            print(f"::error::Failed to parse helm_templates JSON: {e}")
            print(f"::debug::Raw helm_templates value: {helm_templates_raw[:200]}...")
            self.error("Invalid helm_templates JSON format")
        
        self.ai_provider = os.getenv('INPUT_AI_PROVIDER', 'copilot')
        self.ai_token = os.getenv('INPUT_AI_TOKEN')
        self.ai_model = os.getenv('INPUT_AI_MODEL')
        
        if not all([self.app_name, self.environment, self.current_values, self.operational_context]):
            self.error("Missing required inputs")
    
    def decode_base64_input(self, env_var: str) -> str:
        """Decode base64 encoded input from environment variable"""
        encoded_value = os.getenv(env_var, '')
        if not encoded_value:
            return ''
        
        try:
            decoded_bytes = base64.b64decode(encoded_value)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"::error::Failed to decode base64 input {env_var}: {e}")
            return ''
    
    def error(self, message: str):
        """Output error and exit"""
        print(f"::error::{message}")
        sys.exit(1)
    
    def output(self, name: str, value: str):
        """Set GitHub Action output"""
        # Escape multiline output properly for GitHub Actions
        delimiter = f"EOF_{os.urandom(8).hex()}"
        escaped_value = value.replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D')
        print(f"::set-output name={name}::{escaped_value}")
    
    def run(self):
        """Main action execution"""
        print(f"🤖 Generating values for {self.app_name} in {self.environment}")
        
        try:
            # Parse inputs
            current_values = yaml.safe_load(self.current_values)
            operational_data = yaml.safe_load(self.operational_context)
            
            # Ensure operational_data is a dictionary
            if not isinstance(operational_data, dict):
                print(f"::error::Operational context failed to parse as YAML dict, got type: {type(operational_data)}")
                print(f"::debug::Raw operational context (first 200 chars): {str(self.operational_context)[:200]}...")
                self.error("Invalid operational context YAML format")
            
            print(f"📊 Loaded {len(self.helm_templates)} Helm templates")
            print(f"🔍 Processing operational data with {len(operational_data.get('recent_incidents', []))} incidents")
            
            # Generate AI analysis context
            context = self.build_analysis_context(current_values, operational_data)
            
            # Generate recommendations
            recommendations = self.generate_ai_recommendations(context)
            
            if not recommendations:
                self.error("Failed to generate AI recommendations - check AI provider configuration and token")
            
            # Apply recommendations to current values
            updated_values = self.apply_recommendations(current_values, recommendations)
            
            # Generate outputs
            generated_yaml = yaml.dump(updated_values, default_flow_style=False, sort_keys=False)
            changes = self.summarize_changes(current_values, updated_values)
            
            # Set outputs
            self.output('generated_values', generated_yaml)
            self.output('ai_analysis', recommendations.get('analysis', 'Analysis completed'))
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
                f"HELM TEMPLATES ({len(self.helm_templates)} files):",
                *[f"Template {i+1}:\n{template}" for i, template in enumerate(self.helm_templates)]
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
            print(f"::warning::Unsupported AI provider: {self.ai_provider}")
            return None
    
    def call_github_models(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call GitHub Models API"""
        if not self.ai_token:
            print("::error::AI token is required for GitHub Models API")
            return None
        
        try:
            print("🤖 Calling GitHub Models API...")
            response = requests.post(
                'https://models.github.ai/inference/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.ai_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.ai_model or 'gpt-4o',
                    'messages': [
                        {
                            'role': 'system', 
                            'content': 'You are a Kubernetes expert. Respond only with valid JSON.'
                        },
                        {
                            'role': 'user', 
                            'content': prompt
                        }
                    ],
                    'max_tokens': 1500,
                    'temperature': 0.1
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"::error::GitHub Models API returned {response.status_code}: {response.text}")
                return None
            
            ai_response = response.json()['choices'][0]['message']['content']
            print(f"🤖 AI Response received: {len(ai_response)} characters")
            
            # Clean and parse JSON response
            return self.parse_ai_json_response(ai_response)
            
        except Exception as e:
            print(f"::error::GitHub Models API error: {e}")
            return None
    
    def call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI API"""
        if not self.ai_token:
            print("::error::AI token is required for OpenAI API")
            return None
        
        try:
            print("🤖 Calling OpenAI API...")
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.ai_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.ai_model or 'gpt-4',
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are a Kubernetes expert. Respond only with valid JSON.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'max_tokens': 1500,
                    'temperature': 0.1
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"::error::OpenAI API returned {response.status_code}: {response.text}")
                return None
            
            ai_response = response.json()['choices'][0]['message']['content']
            print(f"🤖 AI Response received: {len(ai_response)} characters")
            
            # Clean and parse JSON response
            return self.parse_ai_json_response(ai_response)
            
        except Exception as e:
            print(f"::error::OpenAI API error: {e}")
            return None
    
    def parse_ai_json_response(self, ai_response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response and extract JSON"""
        try:
            # Remove markdown code blocks if present
            if '```json' in ai_response:
                json_start = ai_response.find('```json') + 7
                json_end = ai_response.find('```', json_start)
                ai_response = ai_response[json_start:json_end].strip()
            elif '```' in ai_response:
                json_start = ai_response.find('```') + 3
                json_end = ai_response.find('```', json_start)
                ai_response = ai_response[json_start:json_end].strip()
            
            # Parse JSON
            result = json.loads(ai_response)
            
            # Validate required fields
            if not isinstance(result, dict):
                print("::error::AI response is not a JSON object")
                return None
            
            if 'recommendations' not in result:
                print("::error::AI response missing 'recommendations' field")
                return None
            
            print(f"✅ Successfully parsed AI recommendations with {len(result.get('recommendations', {}))} changes")
            return result
            
        except json.JSONDecodeError as e:
            print(f"::error::Failed to parse AI response as JSON: {e}")
            print(f"::debug::AI response (first 500 chars): {ai_response[:500]}...")
            return None
    
    def apply_recommendations(self, current_values: Dict[str, Any], recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI recommendations to current values"""
        updated_values = self.deep_copy_dict(current_values)
        
        for path, value in recommendations.get('recommendations', {}).items():
            print(f"📝 Applying: {path} = {value}")
            self.set_nested_value(updated_values, path, value)
        
        return updated_values
    
    def deep_copy_dict(self, original: Dict) -> Dict:
        """Deep copy a dictionary"""
        import copy
        return copy.deepcopy(original)
    
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