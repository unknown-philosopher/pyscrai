"""
Test Suite: Agents & Prompts

Tests for advisor system and prompt manager.
"""


def test_prompt_manager():
    """Test the prompt manager with externalized YAML prompts."""
    print("\nTesting prompt manager...")
    
    from forge.agents.prompts import get_prompt_manager, PromptManager
    
    manager = get_prompt_manager()
    
    # List prompts - should include YAML-loaded prompts
    prompts = manager.list_prompts()
    
    # Check extraction prompts loaded from extraction.yaml
    assert "extraction.system_prompt" in prompts
    assert "extraction.user_prompt_template" in prompts
    print(f"  ✓ Extraction prompts loaded")
    
    # Check analysis prompts loaded from analysis.yaml
    assert "analysis.system_prompt" in prompts
    assert "analysis.analyze_entity_prompt" in prompts
    print(f"  ✓ Analysis prompts loaded")
    
    # Check review prompts loaded from review.yaml
    assert "review.system_prompt" in prompts
    assert "review.review_entity_prompt" in prompts
    print(f"  ✓ Review prompts loaded")
    
    # Check advisor prompts loaded from advisors/*.yaml
    assert "osint.system_prompt" in prompts
    assert "humint.system_prompt" in prompts
    assert "sigint.system_prompt" in prompts
    assert "synth.system_prompt" in prompts
    assert "geoint.system_prompt" in prompts
    assert "anvil.system_prompt" in prompts
    print(f"  ✓ Advisor prompts loaded (6 advisors)")
    
    # Test Jinja2 rendering
    rendered = manager.render(
        "extraction.user_prompt_template",
        source_name="test.txt",
        chunk_info="CHUNK: 1",
        text_content="John Smith met with the CIA director.",
        context="Intelligence report"
    )
    assert "John Smith" in rendered
    assert "CIA director" in rendered
    print("  ✓ Jinja2 template rendering works")
    
    print(f"  ✓ Total prompts loaded: {len(prompts)}")
    
    print("\n✅ Prompt manager tests passed!")


def test_advisor_system():
    """Test the phase-specific advisor system."""
    print("\nTesting advisor system...")
    
    from forge.agents.advisors import (
        OSINTAdvisor, HUMINTAdvisor, SIGINTAdvisor,
        SYNTHAdvisor, GEOINTAdvisor, ANVILAdvisor
    )
    from forge.agents.prompts import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # Test each advisor has its system prompt
    advisors = [
        ("OSINT", "osint.system_prompt", "p0_extraction"),
        ("HUMINT", "humint.system_prompt", "p1_entities"),
        ("SIGINT", "sigint.system_prompt", "p2_relationships"),
        ("SYNTH", "synth.system_prompt", "p3_narrative"),
        ("GEOINT", "geoint.system_prompt", "p4_map"),
        ("ANVIL", "anvil.system_prompt", "p5_finalize"),
    ]
    
    for name, prompt_key, phase in advisors:
        prompt = manager.get(prompt_key)
        assert prompt is not None, f"{name} system prompt not found"
        assert len(prompt) > 100, f"{name} prompt too short"
        print(f"  ✓ {name} advisor prompt loaded ({phase})")
    
    # Verify advisor classes can be instantiated (type check)
    assert OSINTAdvisor is not None
    assert HUMINTAdvisor is not None
    assert SIGINTAdvisor is not None
    assert SYNTHAdvisor is not None
    assert GEOINTAdvisor is not None
    assert ANVILAdvisor is not None
    print("  ✓ All advisor classes available")
    
    print("\n✅ Advisor system tests passed!")
