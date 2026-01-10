"""
Test Suite: Systems

Tests for database, file manager, LLM models, and memory systems.
"""
import tempfile
from pathlib import Path


def test_database_operations():
    """Test database CRUD operations."""
    print("\nTesting database operations...")
    
    from forge.core.models.entity import create_actor
    from forge.systems.storage.database import DatabaseManager
    
    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DatabaseManager(str(db_path))
        db.initialize()
        print(f"  ✓ Created database at {db_path}")
        
        # Save entity
        actor = create_actor("Test Actor", "A test entity")
        db.save_entity(actor)
        print(f"  ✓ Saved entity: {actor.name}")
        
        # Retrieve entity
        retrieved = db.get_entity(actor.id)
        assert retrieved is not None
        assert retrieved.name == actor.name
        print(f"  ✓ Retrieved entity: {retrieved.name}")
        
        # Get all entities
        all_entities = db.get_all_entities()
        assert len(all_entities) == 1
        print(f"  ✓ Get all entities: {len(all_entities)} found")
        
        # Delete entity
        db.delete_entity(actor.id)
        deleted = db.get_entity(actor.id)
        assert deleted is None
        print("  ✓ Deleted entity")
    
    print("\n✅ Database operation tests passed!")


def test_file_manager():
    """Test file I/O operations."""
    print("\nTesting file manager...")
    
    from forge.systems.storage.file_io import FileManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        fm = FileManager(tmpdir)
        fm.ensure_directories()
        
        # Check directories created
        assert fm.staging_path.exists()
        assert fm.sources_path.exists()
        assert fm.logs_path.exists()
        print("  ✓ Directory structure created")
        
        # Write staging JSON
        test_data = {"entities": [{"name": "John", "type": "actor"}]}
        path = fm.write_staging_json("test_entities.json", test_data)
        assert path.exists()
        print(f"  ✓ Written staging JSON: {path.name}")
        
        # Read staging JSON
        loaded = fm.read_staging_json("test_entities.json")
        assert loaded["entities"][0]["name"] == "John"
        print("  ✓ Read staging JSON back")
        
        # Write source document
        source_text = "This is a test document."
        source_path = fm.save_source_document("test_doc.txt", source_text)
        assert source_path.exists()
        print(f"  ✓ Written source document: {source_path.name}")
        
        # Read source document
        retrieved_text = fm.get_source_document("test_doc.txt")
        assert retrieved_text == source_text
        print("  ✓ Read source document back")
    
    print("\n✅ File manager tests passed!")


def test_llm_models():
    """Test LLM message and conversation models."""
    print("\nTesting LLM models...")
    
    from forge.systems.llm.models import LLMMessage, MessageRole, Conversation
    
    # Test message creation
    msg = LLMMessage(
        role=MessageRole.USER,
        content="Hello, world!",
        tokens_used=5
    )
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello, world!"
    print("  ✓ LLMMessage creation")
    
    # Test API format conversion
    api_format = msg.to_api_format()
    assert api_format["role"] == "user"
    assert api_format["content"] == "Hello, world!"
    print("  ✓ Message to API format")
    
    # Test dict serialization
    msg_dict = msg.to_dict()
    restored = LLMMessage.from_dict(msg_dict)
    assert restored.role == msg.role
    assert restored.content == msg.content
    print("  ✓ Message serialization/deserialization")
    
    # Test conversation
    conv = Conversation(
        id="conv_001",
        title="Test Conversation",
        system_prompt="You are a helpful assistant.",
    )
    conv.add_message(msg)
    conv.add_message(LLMMessage(role=MessageRole.ASSISTANT, content="Hi there!"))
    
    assert len(conv.messages) == 2
    assert conv.total_tokens == 5
    print(f"  ✓ Conversation with {len(conv.messages)} messages")
    
    # Test API messages with system prompt
    api_messages = conv.get_messages_for_api()
    assert api_messages[0]["role"] == "system"
    assert len(api_messages) == 3
    print("  ✓ Conversation to API format (with system prompt)")
    
    print("\n✅ LLM models tests passed!")


def test_vector_memory_serialization():
    """Test float32 vector serialization for embeddings."""
    print("\nTesting vector memory serialization...")
    
    import numpy as np
    from forge.systems.memory.vector_memory import (
        serialize_float32,
        deserialize_float32,
    )
    
    # Test float32 vector serialization
    test_vector = np.random.rand(384).astype(np.float32)
    serialized = serialize_float32(test_vector)
    assert isinstance(serialized, bytes)
    print("  ✓ Serialized float32 vector to bytes")
    
    # Verify deserialization
    deserialized = deserialize_float32(serialized)
    assert deserialized.shape == (384,)
    assert deserialized.dtype == np.float32
    np.testing.assert_array_almost_equal(test_vector, deserialized)
    print("  ✓ Deserialized bytes back to float32 array")
    
    # Test with list input
    list_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    serialized_list = serialize_float32(list_vector)
    assert isinstance(serialized_list, bytes)
    deserialized_list = deserialize_float32(serialized_list)
    np.testing.assert_array_almost_equal(deserialized_list, list_vector)
    print("  ✓ Serialization works with list input")
    
    # Test zero vector
    zero_vector = np.zeros(128, dtype=np.float32)
    serialized_zero = serialize_float32(zero_vector)
    deserialized_zero = deserialize_float32(serialized_zero)
    np.testing.assert_array_almost_equal(deserialized_zero, zero_vector)
    print("  ✓ Zero vector serialization works")
    
    # Test VectorMemory initialization
    from forge.systems.memory.vector_memory import VectorMemory
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_vectors.db"
        vm = VectorMemory(str(db_path), dimension=384)
        result = vm.initialize()
        print(f"  ✓ VectorMemory initialized (sqlite-vec available: {result})")
        
        # Verify embedding model is accessible
        assert vm.embedding_model is not None
        print("  ✓ Embedding model accessible")
        
        # Test compute similarity
        sim = vm.compute_similarity("hello world", "greetings universe")
        assert 0 <= sim <= 1
        print(f"  ✓ Compute similarity: {sim:.4f}")
    
    print("\n✅ Vector memory serialization tests passed!")
