"""
Model Context Protocol (MCP) JSON-RPC 2.0 implementation.
"""

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class MCPCapability(Enum):
    """MCP server capabilities."""

    RESOURCES = "resources"
    TOOLS = "tools"
    PROMPTS = "prompts"
    LOGGING = "logging"


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""

    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        response: Dict[str, Any] = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            response["id"] = self.id
        if self.error is not None:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


@dataclass
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPPrompt:
    """MCP prompt template definition."""

    name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MCPProtocol:
    """
    Model Context Protocol implementation.

    Handles JSON-RPC 2.0 communication for MCP servers and clients.
    """

    VERSION = "0.1.0"

    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Initialize MCP protocol handler.

        Args:
            name: Server/client name
            version: Server/client version
        """
        self.name = name
        self.version = version
        self.capabilities: List[MCPCapability] = []

        # Method handlers
        self.request_handlers: Dict[str, Callable] = {}
        self.notification_handlers: Dict[str, Callable] = {}

        # State
        self.initialized = False
        self.resources: Dict[str, MCPResource] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.prompts: Dict[str, MCPPrompt] = {}

        # Register core handlers
        self._register_core_handlers()

    def _register_core_handlers(self):
        """Register core MCP method handlers."""
        self.register_request_handler("initialize", self._handle_initialize)
        self.register_request_handler("initialized", self._handle_initialized)
        self.register_request_handler("resources/list", self._handle_list_resources)
        self.register_request_handler("resources/read", self._handle_read_resource)
        self.register_request_handler("tools/list", self._handle_list_tools)
        self.register_request_handler("tools/call", self._handle_call_tool)
        self.register_request_handler("prompts/list", self._handle_list_prompts)
        self.register_request_handler("prompts/get", self._handle_get_prompt)
        self.register_request_handler("logging/setLevel", self._handle_set_log_level)

    def add_capability(self, capability: MCPCapability):
        """Add a capability to this MCP instance."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def register_request_handler(self, method: str, handler: Callable):
        """Register a request handler for a method."""
        self.request_handlers[method] = handler

    def register_notification_handler(self, method: str, handler: Callable):
        """Register a notification handler for a method."""
        self.notification_handlers[method] = handler

    def register_resource(self, resource: MCPResource):
        """Register a resource."""
        self.resources[resource.uri] = resource
        self.add_capability(MCPCapability.RESOURCES)

    def register_tool(self, tool: MCPTool):
        """Register a tool."""
        self.tools[tool.name] = tool
        self.add_capability(MCPCapability.TOOLS)

    def register_prompt(self, prompt: MCPPrompt):
        """Register a prompt template."""
        self.prompts[prompt.name] = prompt
        self.add_capability(MCPCapability.PROMPTS)

    async def handle_message(self, message: str) -> Optional[str]:
        """
        Handle incoming JSON-RPC message.

        Args:
            message: JSON-RPC message string

        Returns:
            Response message string (None for notifications)
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            error_response = JSONRPCResponse(
                error={"code": -32700, "message": "Parse error", "data": str(e)}
            )
            return json.dumps(error_response.to_dict())

        # Handle batch requests
        if isinstance(data, list):
            responses = []
            for item in data:
                response = await self._handle_single_message(item)
                if response:
                    responses.append(response.to_dict())
            return json.dumps(responses) if responses else None
        else:
            response = await self._handle_single_message(data)
            return json.dumps(response.to_dict()) if response else None

    async def _handle_single_message(
        self, data: Dict[str, Any]
    ) -> Optional[JSONRPCResponse]:
        """Handle a single JSON-RPC message."""
        # Validate JSON-RPC format
        if data.get("jsonrpc") != "2.0":
            return JSONRPCResponse(
                id=data.get("id"),
                error={
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "jsonrpc must be '2.0'",
                },
            )

        method = data.get("method")
        if not method:
            return JSONRPCResponse(
                id=data.get("id"),
                error={
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "method is required",
                },
            )

        params = data.get("params", {})
        request_id = data.get("id")

        # Determine if this is a request or notification
        is_notification = request_id is None

        try:
            if is_notification:
                # Handle notification
                handler = self.notification_handlers.get(method)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(params)
                    else:
                        handler(params)
                return None
            else:
                # Handle request
                handler = self.request_handlers.get(method)
                if not handler:
                    return JSONRPCResponse(
                        id=request_id,
                        error={
                            "code": -32601,
                            "message": "Method not found",
                            "data": f"Unknown method: {method}",
                        },
                    )

                if asyncio.iscoroutinefunction(handler):
                    result = await handler(params)
                else:
                    result = handler(params)

                return JSONRPCResponse(id=request_id, result=result)

        except Exception as e:
            return JSONRPCResponse(
                id=request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    # Core MCP method handlers

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        # Client info is available but not used in current implementation
        # _client_info = params.get("clientInfo", {})
        protocol_version = params.get("protocolVersion", self.VERSION)

        # Validate protocol version
        if protocol_version != self.VERSION:
            raise ValueError(f"Unsupported protocol version: {protocol_version}")

        self.initialized = True

        return {
            "protocolVersion": self.VERSION,
            "capabilities": {capability.value: {} for capability in self.capabilities},
            "serverInfo": {"name": self.name, "version": self.version},
        }

    def _handle_initialized(self, params: Dict[str, Any]):
        """Handle initialized notification."""
        # Server is now ready to receive requests
        pass

    async def _handle_list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        # Cursor for pagination - not implemented in this version
        # _cursor = params.get("cursor")

        # Simple implementation without pagination
        resources = [resource.to_dict() for resource in self.resources.values()]

        return {"resources": resources}

    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("uri parameter is required")

        resource = self.resources.get(uri)
        if not resource:
            raise ValueError(f"Resource not found: {uri}")

        # This is a placeholder - actual implementation would read resource content
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mime_type or "text/plain",
                    "text": f"Content of resource: {uri}",
                }
            ]
        }

    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        # Cursor for pagination - not implemented in this version
        # _cursor = params.get("cursor")

        tools = [tool.to_dict() for tool in self.tools.values()]

        return {"tools": tools}

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("name parameter is required")

        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        # This is a placeholder - actual implementation would execute the tool
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Executed tool {name} with arguments {arguments}",
                }
            ]
        }

    async def _handle_list_prompts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request."""
        # Cursor for pagination - not implemented in this version
        # _cursor = params.get("cursor")

        prompts = [prompt.to_dict() for prompt in self.prompts.values()]

        return {"prompts": prompts}

    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("name parameter is required")

        prompt = self.prompts.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        # This is a placeholder - actual implementation would render the prompt
        return {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Rendered prompt: {name} with arguments {arguments}",
                    },
                }
            ],
        }

    def _handle_set_log_level(self, params: Dict[str, Any]):
        """Handle logging/setLevel notification."""
        level = params.get("level", "info")
        # Set logging level - placeholder implementation
        print(f"Log level set to: {level}")

    def create_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a JSON-RPC request message."""
        request = JSONRPCRequest(method=method, params=params, id=str(uuid.uuid4()))
        return json.dumps(request.to_dict())

    def create_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a JSON-RPC notification message."""
        request = JSONRPCRequest(
            method=method,
            params=params,
            # No id for notifications
        )
        return json.dumps(request.to_dict())


class MCPServer(MCPProtocol):
    """MCP Server implementation."""

    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)

    async def start_stdio(self):
        """Start MCP server using stdio transport."""
        import sys

        while True:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Handle message
                response = await self.handle_message(line)

                # Send response to stdout
                if response:
                    print(response, flush=True)

            except Exception as e:
                error_response = JSONRPCResponse(
                    error={"code": -32603, "message": "Internal error", "data": str(e)}
                )
                print(json.dumps(error_response.to_dict()), flush=True)


class MCPClient(MCPProtocol):
    """MCP Client implementation."""

    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        self.pending_requests: Dict[str, asyncio.Future] = {}

    async def initialize(self, server_transport) -> Dict[str, Any]:
        """Initialize connection with MCP server."""
        request = self.create_request(
            "initialize",
            {
                "protocolVersion": self.VERSION,
                "clientInfo": {"name": self.name, "version": self.version},
                "capabilities": {
                    capability.value: {} for capability in self.capabilities
                },
            },
        )

        response = await self._send_request(server_transport, request)

        # Send initialized notification
        notification = self.create_notification("initialized")
        await server_transport.send(notification)

        return response if isinstance(response, dict) else {}

    async def _send_request(self, transport, request: str) -> Any:
        """Send request and wait for response."""
        # This is a placeholder - actual implementation would depend on transport
        # For now, just return a mock response
        return {"protocolVersion": self.VERSION, "capabilities": {}}


async def main():
    """Example MCP server."""
    server = MCPServer("example-server", "1.0.0")

    # Register a test resource
    server.register_resource(
        MCPResource(
            uri="file:///example.txt",
            name="Example File",
            description="An example text file",
            mime_type="text/plain",
        )
    )

    # Register a test tool
    server.register_tool(
        MCPTool(
            name="echo",
            description="Echo the input text",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to echo"}
                },
                "required": ["text"],
            },
        )
    )

    # Register a test prompt
    server.register_prompt(
        MCPPrompt(
            name="summarize",
            description="Summarize the given text",
            arguments=[
                {"name": "text", "description": "Text to summarize", "required": True}
            ],
        )
    )

    print("MCP Server starting on stdio...")
    await server.start_stdio()


if __name__ == "__main__":
    asyncio.run(main())
