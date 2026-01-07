import pytest
import asyncio

from pyscrai_forge.agents.narrator import NarratorAgent
from pyscrai_forge.prompts.narrative import NarrativeMode


class FakeProvider:
    def __init__(self, responses):
        # responses is a list of strings to return sequentially from complete_simple
        self._responses = list(responses)
        self.default_model = "test-model"

    async def complete_simple(self, prompt: str, model: str, system_prompt: str | None = None, temperature: float = 0.7):
        await asyncio.sleep(0)  # yield control
        if not self._responses:
            return ""
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_generate_narrative_pass():
    # Draft then PASS
    draft = "This is a correct narrative."
    provider = FakeProvider([draft, "PASS"])
    agent = NarratorAgent(provider)

    entities = [{"name": "Unit Alpha", "type": "actor", "resources": {"wealth": 12000}}]
    relationships = []

    result = await agent.generate_narrative(entities, relationships, mode=NarrativeMode.SITREP, focus="Economy")
    assert result == draft


@pytest.mark.asyncio
async def test_generate_narrative_refine():
    draft = "Narrative says 100 credits."
    critique = "Error: Narrative says 100 credits, Source says 12000"
    final = "Narrative: Unit Alpha has 12000 credits."

    provider = FakeProvider([draft, critique, final])
    agent = NarratorAgent(provider)

    entities = [{"name": "Unit Alpha", "type": "actor", "resources": {"wealth": 12000}}]
    relationships = []

    result = await agent.generate_narrative(entities, relationships, mode=NarrativeMode.DOSSIER, focus="Wealth")
    assert result == final
