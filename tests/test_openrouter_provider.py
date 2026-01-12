import asyncio
import logging
import os
import pytest
from forge.infrastructure.llm.openrouter_provider import OpenRouterProvider

logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_openrouter_model_selection():
	"""Test that OpenRouter returns the requested model or logs the actual model used."""
	api_key = os.getenv("OPENROUTER_API_KEY")
	base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
	requested_model = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free")
	provider = OpenRouterProvider(api_key=api_key, base_url=base_url, default_model=requested_model)
	messages = [
		{"role": "system", "content": "You are a helpful assistant."},
		{"role": "user", "content": "Say hello."}
	]
	response = await provider.complete(messages=messages, model=requested_model, temperature=0.5, max_tokens=32)
	returned_model = response.get("model", None)
	print(f"Requested model: {requested_model}")
	print(f"Returned model: {returned_model}")
	assert returned_model is not None, "No model field returned in response"
	# Optionally, assert that returned_model matches requested_model
	# assert returned_model == requested_model, f"Returned model does not match requested: {returned_model} vs {requested_model}"
