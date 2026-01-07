from pydantic_ai import Embedder
from pydantic_ai.embeddings.sentence_transformers import (
    SentenceTransformersEmbeddingSettings,
)

embedder = Embedder(
    'sentence-transformers:all-MiniLM-L6-v2',
    settings=SentenceTransformersEmbeddingSettings(
        sentence_transformers_device='cuda',  # Use GPU
        sentence_transformers_normalize_embeddings=True,  # L2 normalize
    ),
)

async def main():
    result = await embedder.embed_query('Hello world')
    print(len(result.embeddings[0]))
    #> 384
# (This example is complete, it can be run "as is" — you'll need to add asyncio.run(main()) to run main)