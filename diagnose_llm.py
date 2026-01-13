#!/usr/bin/env python3
"""Diagnostic script to test LLM provider and prompt rendering."""

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from forge.infrastructure.llm.provider_factory import ProviderFactory
from forge.config.prompts import render_prompt
from forge.core.services import call_llm_and_parse_json

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_prompt_rendering():
    """Test that prompt templates can be rendered."""
    print("\n" + "="*80)
    print("TEST 1: Prompt Template Rendering")
    print("="*80)
    
    try:
        # Test extraction service prompt
        content = "Alice works at PyScrAI, a company focused on AI research."
        prompt = render_prompt("extraction_service", content=content)
        print(f"✅ Extraction prompt rendered successfully")
        print(f"   Prompt length: {len(prompt)} characters")
        print(f"   First 200 chars: {prompt[:200]}...")
    except Exception as e:
        print(f"❌ Failed to render extraction prompt: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test resolution service prompt
        entities = [
            {"type": "PERSON", "text": "Alice"},
            {"type": "ORG", "text": "PyScrAI"}
        ]
        prompt = render_prompt("resolution_service", 
                              document_content=content,
                              entities=entities)
        print(f"✅ Resolution prompt rendered successfully")
        print(f"   Prompt length: {len(prompt)} characters")
        print(f"   First 200 chars: {prompt[:200]}...")
    except Exception as e:
        print(f"❌ Failed to render resolution prompt: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_llm_provider_initialization():
    """Test that LLM provider can be initialized."""
    print("\n" + "="*80)
    print("TEST 2: LLM Provider Initialization")
    print("="*80)
    
    try:
        provider, model = ProviderFactory.create_from_env()
        print(f"✅ LLM provider initialized successfully")
        print(f"   Provider type: {provider.provider_name}")
        print(f"   Default model: {model or provider.default_model}")
        print(f"   Base URL: {provider.base_url}")
        return provider
    except Exception as e:
        print(f"❌ Failed to initialize LLM provider: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_llm_call(provider):
    """Test a simple LLM call."""
    print("\n" + "="*80)
    print("TEST 3: Simple LLM Call")
    print("="*80)
    
    if provider is None:
        print("❌ Skipping LLM call test - provider not available")
        return False
    
    try:
        # Test simple completion
        response = await provider.complete(
            messages=[{"role": "user", "content": "Say 'Hello' and nothing else."}],
            model=provider.default_model or "openai/gpt-3.5-turbo",
            max_tokens=50,
            temperature=0.3
        )
        
        print(f"✅ LLM call succeeded")
        print(f"   Response keys: {list(response.keys())}")
        
        if "choices" in response and response["choices"]:
            content = response["choices"][0].get("message", {}).get("content", "")
            print(f"   Content: {content[:200]}")
        else:
            print(f"   ⚠️  No 'choices' in response: {response}")
        
        return True
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_entity_extraction(provider):
    """Test entity extraction with actual prompt."""
    print("\n" + "="*80)
    print("TEST 4: Entity Extraction (Full Pipeline)")
    print("="*80)
    
    if provider is None:
        print("❌ Skipping entity extraction test - provider not available")
        return False
    
    try:
        content = "Alice works at PyScrAI, a company focused on AI research."
        prompt = render_prompt("extraction_service", content=content)
        
        print(f"📝 Sending extraction prompt to LLM...")
        print(f"   Prompt length: {len(prompt)} characters")
        
        entities = await call_llm_and_parse_json(
            llm_provider=provider,
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
            service_name="DiagnosticTest",
            doc_id="test_doc"
        )
        
        if entities is None:
            print(f"❌ Entity extraction returned None")
            print(f"   This means the LLM call failed or returned invalid JSON")
            return False
        
        print(f"✅ Entity extraction succeeded")
        print(f"   Entities returned: {entities}")
        print(f"   Type: {type(entities)}")
        
        if isinstance(entities, list):
            print(f"   Number of entities: {len(entities)}")
            for i, entity in enumerate(entities[:5]):  # Show first 5
                print(f"     [{i+1}] {entity}")
        else:
            print(f"   ⚠️  Entities is not a list: {type(entities)}")
        
        return True
    except Exception as e:
        print(f"❌ Entity extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_relationship_extraction(provider):
    """Test relationship extraction with actual prompt."""
    print("\n" + "="*80)
    print("TEST 5: Relationship Extraction (Full Pipeline)")
    print("="*80)
    
    if provider is None:
        print("❌ Skipping relationship extraction test - provider not available")
        return False
    
    try:
        content = "Alice works at PyScrAI, a company focused on AI research."
        entities = [
            {"type": "PERSON", "text": "Alice"},
            {"type": "ORG", "text": "PyScrAI"}
        ]
        prompt = render_prompt("resolution_service",
                              document_content=content,
                              entities=entities)
        
        print(f"📝 Sending relationship extraction prompt to LLM...")
        print(f"   Prompt length: {len(prompt)} characters")
        
        relationships = await call_llm_and_parse_json(
            llm_provider=provider,
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
            service_name="DiagnosticTest",
            doc_id="test_doc"
        )
        
        if relationships is None:
            print(f"❌ Relationship extraction returned None")
            print(f"   This means the LLM call failed or returned invalid JSON")
            return False
        
        print(f"✅ Relationship extraction succeeded")
        print(f"   Relationships returned: {relationships}")
        print(f"   Type: {type(relationships)}")
        
        if isinstance(relationships, list):
            print(f"   Number of relationships: {len(relationships)}")
            for i, rel in enumerate(relationships[:5]):  # Show first 5
                print(f"     [{i+1}] {rel}")
        else:
            print(f"   ⚠️  Relationships is not a list: {type(relationships)}")
        
        return True
    except Exception as e:
        print(f"❌ Relationship extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostic tests."""
    print("\n" + "="*80)
    print("LLM PIPELINE DIAGNOSTIC TOOL")
    print("="*80)
    print("\nThis tool will test each component of the LLM pipeline to identify")
    print("where failures are occurring.\n")
    
    results = {}
    
    # Test 1: Prompt rendering
    results['prompt_rendering'] = await test_prompt_rendering()
    
    # Test 2: Provider initialization
    provider = await test_llm_provider_initialization()
    results['provider_init'] = provider is not None
    
    # Test 3: Simple LLM call
    results['simple_llm_call'] = await test_llm_call(provider)
    
    # Test 4: Entity extraction
    results['entity_extraction'] = await test_entity_extraction(provider)
    
    # Test 5: Relationship extraction
    results['relationship_extraction'] = await test_relationship_extraction(provider)
    
    # Summary
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    # Cleanup
    if provider:
        try:
            await provider.close()
        except:
            pass
    
    print("\n" + "="*80)
    print("Diagnostic complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
