"""Simple LLM Provider Tests.

Tests for the LLM provider infrastructure, including provider creation
and basic chat completion functionality.
"""

import asyncio
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

from forge.infrastructure.llm.provider_factory import ProviderFactory

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class LLMProviderTest(unittest.IsolatedAsyncioTestCase):
    """Test LLM provider functionality."""

    async def test_provider_factory_creates_openrouter_provider(self) -> None:
        """Test that ProviderFactory can create an OpenRouter provider."""
        provider = ProviderFactory.create("openrouter")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.provider_name, "openrouter")
        await provider.close()

    async def test_provider_factory_reads_default_model_from_env(self) -> None:
        """Test that ProviderFactory reads OPENROUTER_MODEL from environment."""
        model = ProviderFactory.get_default_model()
        # Should read from OPENROUTER_MODEL or OPENROUTER_DEFAULT_MODEL
        self.assertIsNotNone(model, "OPENROUTER_MODEL or OPENROUTER_DEFAULT_MODEL should be set in .env")
        
        # Verify the provider uses the default model
        provider, default_model = ProviderFactory.create_from_env()
        self.assertEqual(default_model, model)
        await provider.close()

    async def test_provider_can_list_models(self) -> None:
        """Test that provider can list available models."""
        provider = ProviderFactory.create("openrouter")
        
        try:
            models = await provider.list_models()
            self.assertIsInstance(models, list)
            self.assertGreater(len(models), 0, "Should have at least one model available")
            
            # Verify model structure
            if models:
                model = models[0]
                self.assertTrue(hasattr(model, 'id'))
                self.assertTrue(hasattr(model, 'name'))
        finally:
            await provider.close()

    async def test_provider_can_make_chat_completion(self) -> None:
        """Test that provider can make a simple chat completion."""
        provider, default_model = ProviderFactory.create_from_env()
        
        try:
            # Get available models if default_model is not set
            if not default_model:
                models = await provider.list_models()
                if not models:
                    self.skipTest("No models available for testing")
                default_model = models[0].id
            
            # Make a simple completion request
            response = await provider.complete(
                messages=[{"role": "user", "content": "Say 'Hello, world!' and nothing else."}],
                model=default_model,
                max_tokens=20,
                temperature=0.0
            )
            
            # Verify response structure
            self.assertIn("choices", response)
            self.assertGreater(len(response["choices"]), 0)
            
            message = response["choices"][0].get("message", {})
            self.assertIn("content", message)
            content = message["content"]
            self.assertIsInstance(content, str)
            self.assertGreater(len(content), 0)
            
        except Exception as e:
            # If authentication fails, skip the test with a helpful message
            if "Authentication failed" in str(e) or "401" in str(e):
                self.skipTest(f"Authentication failed - check OPENROUTER_API_KEY: {e}")
            else:
                raise
        finally:
            await provider.close()

    async def test_provider_supports_both_model_env_vars(self) -> None:
        """Test that provider supports both OPENROUTER_MODEL and OPENROUTER_DEFAULT_MODEL."""
        # Check if OPENROUTER_MODEL is set
        openrouter_model = os.getenv("OPENROUTER_MODEL")
        openrouter_default_model = os.getenv("OPENROUTER_DEFAULT_MODEL")
        
        # At least one should be set, or we skip
        if not openrouter_model and not openrouter_default_model:
            self.skipTest("Neither OPENROUTER_MODEL nor OPENROUTER_DEFAULT_MODEL is set")
        
        # ProviderFactory should read from OPENROUTER_MODEL first, then OPENROUTER_DEFAULT_MODEL
        model = ProviderFactory.get_default_model()
        if openrouter_model:
            self.assertEqual(model, openrouter_model)
        elif openrouter_default_model:
            self.assertEqual(model, openrouter_default_model)


if __name__ == "__main__":
    unittest.main()
