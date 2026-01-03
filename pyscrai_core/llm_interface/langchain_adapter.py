"""Adapter for using existing LLM providers with LangChain."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any, List, Optional

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage as LangChainChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from .base import LLMClient


class LangChainLLMAdapter(BaseChatModel):
    """Adapter to make LLMClient compatible with LangChain BaseChatModel."""

    client: LLMClient
    model_name: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0

    def __init__(
        self,
        client: LLMClient,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs: Any,
    ):
        """Initialize the adapter."""
        super().__init__(
            client=client,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs,
        )

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "pyscrai-llm-adapter"

    def _convert_message_to_dict(self, message: BaseMessage) -> dict:
        """Convert a LangChain message to the dictionary format expected by LLMClient."""
        if isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            return {"role": "assistant", "content": message.content}
        elif isinstance(message, SystemMessage):
            return {"role": "system", "content": message.content}
        elif isinstance(message, LangChainChatMessage):
            return {"role": message.role, "content": message.content}
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert a list of LangChain messages to the dictionary format."""
        return [self._convert_message_to_dict(m) for m in messages]

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation. Uses asyncio.run to call the async client."""
        # Note: This might fail if called from within an existing event loop.
        # It's recommended to use astream or agenerate.
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
             raise RuntimeError(
                 "Cannot call synchronous _generate from a running event loop. "
                 "Use await agenerate() instead."
             )
             
        return loop.run_until_complete(
            self._agenerate(messages, stop=stop, run_manager=None, **kwargs)
        )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Asynchronous generation."""
        api_messages = self._convert_messages(messages)
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }
        # Update with run-time kwargs if any valid ones are passed
        # (Filtering can be added if strict validation is needed)
        
        response = await self.client.complete(api_messages, **params)
        
        # Handle stop sequences if provided (naive implementation as post-processing)
        # Since the underlying client doesn't support stop sequences directly yet.
        content = ""
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            
        if stop:
            for s in stop:
                if s in content:
                    content = content.split(s)[0]
        
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        
        return ChatResult(generations=[generation])

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Asynchronous streaming."""
        api_messages = self._convert_messages(messages)
        
        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }

        async for chunk_content in self.client.stream_complete(api_messages, **params):
            if stop:
                # Basic stop logic for streaming is complex without buffering.
                # Here we just check if the chunk contains the stop word.
                # A proper implementation would need a buffer.
                should_break = False
                for s in stop:
                    if s in chunk_content:
                        # Split and yield the part before stop
                        chunk_content = chunk_content.split(s)[0]
                        should_break = True
                        break
                
                if chunk_content:
                    yield ChatGenerationChunk(message=AIMessageChunk(content=chunk_content))
                
                if should_break:
                    break
            else:
                if chunk_content:
                    yield ChatGenerationChunk(message=AIMessageChunk(content=chunk_content))
