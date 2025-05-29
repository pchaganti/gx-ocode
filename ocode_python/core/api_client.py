"""
Ollama API Client for streaming completions and model management.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
from pydantic import BaseModel


@dataclass
class Message:
    """Chat message structure."""

    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary format.

        Returns:
            Dictionary with role and content fields.
        """
        return {"role": self.role, "content": self.content}


@dataclass
class ToolCall:
    """Tool call structure for function calling."""

    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class StreamChunk:
    """Streaming response chunk."""

    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    done: bool = False
    model: Optional[str] = None
    created_at: Optional[str] = None

    @property
    def type(self) -> str:
        """Get the type of this chunk.

        Determines chunk type based on its content.

        Returns:
            One of: "tool_call", "content", "done", or "unknown".
        """
        if self.tool_call:
            return "tool_call"
        elif self.content:
            return "content"
        elif self.done:
            return "done"
        else:
            return "unknown"


class CompletionRequest(BaseModel):
    """Request structure for chat completions."""

    model: str
    messages: List[Dict[str, str]]
    stream: bool = True
    options: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None

    class Config:
        """Pydantic config for ChatRequest."""

        extra = "allow"


class OllamaAPIClient:
    """
    Async client for Ollama API with streaming support.

    Handles chat completions, model management, and tool calling.
    """

    def __init__(self, host: Optional[str] = None, timeout: int = 300):
        """
        Initialize Ollama API client.

        Args:
            host: Ollama host URL. Defaults to OLLAMA_HOST env var or localhost.
            timeout: Request timeout in seconds.
        """
        self.base_url = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "OllamaAPIClient":
        """Async context manager entry.

        Creates and returns an aiohttp ClientSession.

        Returns:
            Self for use in async with statements.
        """
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Closes the aiohttp session if it exists.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self.session:
            await self.session.close()

    async def _ensure_session(self) -> None:
        """Ensure we have an active session.

        Creates a new aiohttp ClientSession if one doesn't exist
        or if the existing one is closed.
        """
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a single prompt for /api/generate endpoint.

        Formats messages with role prefixes for the generate API.

        Args:
            messages: List of message dictionaries with role and content.

        Returns:
            Formatted prompt string with role-prefixed messages.
        """
        prompt_parts = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        return "\n\n".join(prompt_parts)

    async def stream_chat(
        self, request: CompletionRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream chat completion responses.

        Args:
            request: The completion request

        Yields:
            StreamChunk: Individual response chunks
        """
        await self._ensure_session()

        # Use /api/chat endpoint if tools are provided, otherwise use /api/generate for compatibility  # noqa: E501
        if request.tools:
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": request.model,
                "messages": request.messages,
                "stream": False,  # Disable streaming for tool calls - Ollama streaming doesn't work well with tools  # noqa: E501
                "tools": request.tools,
            }
        else:
            url = f"{self.base_url}/api/generate"
            # Convert messages to prompt format for /api/generate
            prompt = self._convert_messages_to_prompt(request.messages)
            payload = {
                "model": request.model,
                "prompt": prompt,
                "stream": request.stream,
            }

        headers = {"Content-Type": "application/json"}

        if request.options:
            payload["options"] = request.options

        try:
            await self._ensure_session()
            if not self.session:
                raise RuntimeError("Failed to create session")
            async with self.session.post(
                url, json=payload, headers=headers
            ) as response:
                response.raise_for_status()

                if request.tools and not payload["stream"]:
                    # Handle non-streaming response for tool calls
                    data = await response.json()
                    chunk = self._parse_chunk(data)
                    yield chunk
                else:
                    # Handle streaming response
                    async for line in response.content:
                        line_str = line.decode("utf-8").strip()
                        if not line_str:
                            continue

                        try:
                            data = json.loads(line_str)
                            chunk = self._parse_chunk(data)

                            # Always yield the chunk if it has any content
                            if chunk.content or chunk.done or chunk.tool_call:
                                yield chunk

                            # Only break if we get an explicit done signal
                            if chunk.done:
                                break

                        except json.JSONDecodeError:
                            # Log invalid JSON lines for debugging
                            print(f"Warning: Invalid JSON in stream: {line_str}")
                            continue

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            raise RuntimeError(f"Streaming error: {e}")

    def _parse_chunk(self, data: Dict[str, Any]) -> StreamChunk:
        """Parse raw response data into StreamChunk.

        Handles different response formats from /api/generate and /api/chat endpoints.
        Extracts content and tool calls as appropriate.

        Args:
            data: Raw JSON response data from Ollama API.

        Returns:
            Parsed StreamChunk object.
        """
        chunk = StreamChunk(
            done=data.get("done", False),
            model=data.get("model"),
            created_at=data.get("created_at"),
        )

        # Handle content from /api/generate endpoint
        if "response" in data:
            chunk.content = data["response"]

        # Handle content from /api/chat endpoint
        if "message" in data:
            message = data["message"]
            if "content" in message:
                chunk.content = message["content"]

            # Handle tool calls from /api/chat endpoint
            if "tool_calls" in message and message["tool_calls"]:
                tool_call_data = message["tool_calls"][0]  # Handle first tool call
                if "function" in tool_call_data:
                    function = tool_call_data["function"]
                    arguments = function.get("arguments", {})

                    # Handle both string and dict formats
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError as e:
                            # Log the error for debugging and try to extract basic parameters  # noqa: E501
                            print(f"Warning: Failed to parse tool arguments JSON: {e}")
                            print(f"Raw arguments: {arguments}")
                            arguments = {}
                    elif not isinstance(arguments, dict):
                        arguments = {}

                    chunk.tool_call = ToolCall(
                        name=function.get("name", ""),
                        arguments=arguments,
                        id=tool_call_data.get("id"),
                    )

        return chunk

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model information dicts
        """
        await self._ensure_session()

        url = f"{self.base_url}/api/tags"

        try:
            await self._ensure_session()
            if not self.session:
                raise RuntimeError("Failed to create session")
            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                result = data.get("models", [])
                return result if isinstance(result, list) else []

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Failed to list models: {e}")

    async def pull_model(self, model: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Pull/download a model with streaming progress.

        Args:
            model: Model name to pull

        Yields:
            Progress updates
        """
        await self._ensure_session()

        url = f"{self.base_url}/api/pull"
        data = {"name": model}

        try:
            await self._ensure_session()
            if not self.session:
                raise RuntimeError("Failed to create session")
            async with self.session.post(url, json=data) as response:
                response.raise_for_status()

                async for line in response.content:
                    if not line.strip():
                        continue

                    try:
                        progress = json.loads(line.decode("utf-8"))
                        yield progress

                        if progress.get("status") == "success":
                            break

                    except json.JSONDecodeError:
                        continue

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Failed to pull model: {e}")

    async def check_health(self) -> bool:
        """
        Check if Ollama server is healthy.

        Returns:
            True if server is responding
        """
        await self._ensure_session()

        try:
            await self._ensure_session()
            if not self.session:
                return False
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                result = response.status == 200
                return bool(result)
        except Exception:
            return False

    async def generate_embeddings(self, model: str, text: str) -> List[float]:
        """
        Generate embeddings for text.

        Args:
            model: Model name for embeddings
            text: Text to embed

        Returns:
            Embedding vector
        """
        await self._ensure_session()

        url = f"{self.base_url}/api/embeddings"
        data = {"model": model, "prompt": text}

        try:
            await self._ensure_session()
            if not self.session:
                raise RuntimeError("Failed to create session")
            async with self.session.post(url, json=data) as response:
                response.raise_for_status()
                result = await response.json()
                embedding = result.get("embedding", [])
                return embedding if isinstance(embedding, list) else []

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Failed to generate embeddings: {e}")

    def close(self) -> None:
        """Close the session (for non-async usage).

        Creates an async task to close the session. This method
        allows non-async code to trigger session cleanup.
        """
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())


async def main() -> None:
    """Example usage of OllamaAPIClient."""
    async with OllamaAPIClient() as client:
        # Check health
        if not await client.check_health():
            print("Ollama server is not running!")
            return

        # List models
        models = await client.list_models()
        print(f"Available models: {[m['name'] for m in models]}")

        # Stream chat
        request = CompletionRequest(
            model="llama3:8b",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
        )

        print("Response: ", end="", flush=True)
        async for chunk in client.stream_chat(request):
            if chunk.content:
                print(chunk.content, end="", flush=True)
        print()


if __name__ == "__main__":
    asyncio.run(main())
