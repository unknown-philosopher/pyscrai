"""Specialized Sub-Agents for the PyScrAI Pipeline.

Includes the JSON Refiner and the Narrative Chronicler.
"""

import json
from typing import Dict, Any, List, Optional
from pyscrai_core.llm_interface import LLMProvider
from pyscrai_forge.prompts.architect_prompts  import NARRATIVE_SYSTEM_PROMPT, JSON_REFINER_PROMPT

class JSONRefiner:
    """The JSON Agent responsible for cleaning and structuring data."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def refine(self, raw_data: Any, schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw harvester output into structured project data."""
        prompt = f"SCHEMA CONTEXT:\n{json.dumps(schema_context)}\n\nRAW DATA:\n{json.dumps(raw_data)}"
        
        messages = [
            {"role": "system", "content": JSON_REFINER_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.provider.complete(messages=messages, model=self.provider.default_model)
        content = response["choices"][0]["message"]["content"]
        
        # Extract JSON block
        try:
            start = content.find("{")
            end = content.rfind("}")
            return json.loads(content[start:end+1])
        except:
            return {"error": "Failed to parse refined JSON", "raw": content}

class NarrativeChronicler:
    """The Narrative Agent responsible for scenario generation."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def generate_scenario(self, corpus_data: List[Dict], project_config: Dict) -> str:
        """Generate a data-driven narrative scenario."""
        context = f"PROJECT CONFIG:\n{json.dumps(project_config)}\n\nDATA CORPUS:\n{json.dumps(corpus_data)}"
        
        messages = [
            {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate a scenario based on this data:\n{context}"}
        ]
        
        # In the future, we would add tools: [{ "google_search": {} }] here for verification
        response = await self.provider.complete(messages=messages, model=self.provider.default_model)
        return response["choices"][0]["message"]["content"]