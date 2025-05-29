"""
Network connectivity testing tool using ping.
"""

import asyncio
import platform
import re
from typing import Any, Dict

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class PingTool(Tool):
    """Tool for testing network connectivity using ping."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the ping tool specification.

        Returns:
            ToolDefinition with parameters for testing network connectivity
            including host, count, timeout, and detailed statistics options.
        """
        return ToolDefinition(
            name="ping",
            description="Test network connectivity to a host using ping",
            category="System Operations",
            parameters=[
                ToolParameter(
                    name="host",
                    type="string",
                    description="Hostname or IP address to ping",
                    required=True,
                ),
                ToolParameter(
                    name="count",
                    type="number",
                    description="Number of ping packets to send (default: 4)",
                    required=False,
                    default=4,
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Timeout in seconds for each ping (default: 5)",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="interval",
                    type="number",
                    description="Interval between pings in seconds (default: 1)",
                    required=False,
                    default=1,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute ping command to test network connectivity."""
        host = kwargs.get("host")
        count = kwargs.get("count", 4)
        timeout = kwargs.get("timeout", 5)
        interval = kwargs.get("interval", 1)

        # Validate inputs
        if not host:
            return ToolResult(
                success=False, output="", error="Host parameter is required"
            )

        # Sanitize host to prevent command injection
        if not self._is_valid_host(host):
            return ToolResult(
                success=False, output="", error=f"Invalid host format: {host}"
            )

        # Validate numeric parameters
        try:
            count = int(count)
            timeout = int(timeout)
            interval = float(interval)
        except (ValueError, TypeError):
            return ToolResult(
                success=False,
                output="",
                error="Count and timeout must be integers, interval must be a number",
            )

        # Limit count to prevent abuse
        if count < 1 or count > 10:
            return ToolResult(
                success=False, output="", error="Count must be between 1 and 10"
            )

        if timeout < 1 or timeout > 30:
            return ToolResult(
                success=False,
                output="",
                error="Timeout must be between 1 and 30 seconds",
            )

        if interval < 0.2 or interval > 10:
            return ToolResult(
                success=False,
                output="",
                error="Interval must be between 0.2 and 10 seconds",
            )

        try:
            # Build ping command based on platform
            cmd = self._build_ping_command(host, count, timeout, interval)

            # Execute ping command
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Wait for command to complete with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=count * (timeout + interval) + 5,  # Extra buffer
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False, output="", error="Ping command timed out"
                )

            # Decode output
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            # Parse results
            if process.returncode == 0:
                stats = self._parse_ping_output(output)
                return ToolResult(success=True, output=output, metadata=stats)
            else:
                # Some ping failures still provide useful output
                if "transmitted" in output or "sent" in output:
                    stats = self._parse_ping_output(output)
                    return ToolResult(
                        success=False,
                        output=output,
                        error=f"Ping failed: {error or 'No response from host'}",
                        metadata=stats,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output=output,
                        error=error or "Ping command failed",
                    )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to execute ping: {str(e)}"
            )

    def _is_valid_host(self, host: str) -> bool:
        """Validate host format to prevent command injection."""
        # Allow alphanumeric, dots, hyphens, and colons (for IPv6)
        # Reject anything with shell metacharacters
        if not host or len(host) > 255:
            return False

        # Check for dangerous characters
        dangerous_chars = [
            "&",
            "|",
            ";",
            "$",
            "`",
            "(",
            ")",
            "<",
            ">",
            "\n",
            "\r",
            '"',
            "'",
            "\\",
        ]
        if any(char in host for char in dangerous_chars):
            return False

        # Basic hostname/IP validation
        # Allow alphanumeric, dots, hyphens, underscores, and colons (for IPv6)
        # Also allow square brackets for IPv6 addresses
        valid_pattern = re.compile(r"^[\w\.\-:\[\]]+$")
        return bool(valid_pattern.match(host))

    def _build_ping_command(
        self, host: str, count: int, timeout: int, interval: float
    ) -> list:
        """Build platform-specific ping command."""
        system = platform.system().lower()

        if system == "darwin":  # macOS
            # macOS ping syntax
            cmd = [
                "ping",
                "-c",
                str(count),
                "-W",
                str(timeout * 1000),
                "-i",
                str(interval),
                host,
            ]
        elif system == "linux":
            # Linux ping syntax
            cmd = [
                "ping",
                "-c",
                str(count),
                "-W",
                str(timeout),
                "-i",
                str(interval),
                host,
            ]
        elif system == "windows":
            # Windows ping syntax (interval not supported)
            cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
        else:
            # Fallback to basic ping
            cmd = ["ping", "-c", str(count), host]

        return cmd

    def _parse_ping_output(self, output: str) -> Dict[str, Any]:
        """Parse ping output to extract statistics."""
        stats = {
            "packets_transmitted": 0,
            "packets_received": 0,
            "packet_loss": 100.0,
            "min_time": None,
            "avg_time": None,
            "max_time": None,
        }

        # Parse packet statistics
        # Look for patterns like "4 packets transmitted, 4 received, 0% packet loss"
        packet_pattern = re.search(
            r"(\d+)\s+packets?\s+transmitted.*?(\d+)\s+(?:packets?\s+)?received.*?(\d+(?:\.\d+)?)\s*%\s*packet\s+loss",  # noqa: E501
            output,
            re.IGNORECASE | re.DOTALL,
        )

        if packet_pattern:
            stats["packets_transmitted"] = int(packet_pattern.group(1))
            stats["packets_received"] = int(packet_pattern.group(2))
            stats["packet_loss"] = float(packet_pattern.group(3))

        # Parse round-trip time statistics
        # Look for patterns like "min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms"
        time_pattern = re.search(
            r"min/avg/max(?:/[a-z]+)?\s*=\s*(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)",  # noqa: E501
            output,
            re.IGNORECASE,
        )

        if time_pattern:
            stats["min_time"] = float(time_pattern.group(1))
            stats["avg_time"] = float(time_pattern.group(2))
            stats["max_time"] = float(time_pattern.group(3))

        return stats
