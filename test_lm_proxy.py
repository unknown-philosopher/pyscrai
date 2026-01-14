#!/usr/bin/env python3
"""Simple test script for lm_proxy LLM provider configuration.

Tests the connection and basic functionality of the lm_proxy provider.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from forge.infrastructure.llm.provider_factory import ProviderFactory

# Load environment variables
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


async def test_lm_proxy():
    """Test lm_proxy provider connection and basic completion."""
    print("Testing lm_proxy provider configuration...")
    print(f"PRIMARY_PROVIDER: {os.getenv('PRIMARY_PROVIDER')}")
    print(f"LM_PROXY_BASE_URL: {os.getenv('LM_PROXY_BASE_URL')}")
    print(f"LM_PROXY_MODEL: {os.getenv('LM_PROXY_MODEL')}")
    print()
    
    try:
        # Create provider from environment
        print("Creating provider from environment...")
        provider, model = ProviderFactory.create_from_env()
        print(f"✓ Provider created successfully")
        print(f"  Provider type: {type(provider).__name__}")
        print(f"  Default model: {model or provider.default_model}")
        print(f"  Base URL: {provider.base_url}")
        print()
        
        # Test connection with a simple completion
        print("Testing connection with simple completion...")
        async with provider:
            response = await provider.complete(
                model=model or provider.default_model,
                messages=[
                    {"role": "user", "content": "Say 'Hello, lm_proxy!' if you can hear me."}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            print(f"✓ Connection successful!")
            print(f"  Response: {response}")
            
            # Extract text if it's a dict
            if isinstance(response, dict):
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    print(f"  Content: {content}")
        
        print("\n✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_lm_proxy())
    sys.exit(0 if success else 1)
