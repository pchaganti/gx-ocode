"""Test file tools timeout functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ocode_python.tools.file_tools import FileReadTool
from ocode_python.utils.timeout_handler import TimeoutError


class TestFileReadToolTimeout:
    """Test FileReadTool timeout handling."""

    @pytest.fixture
    def file_read_tool(self):
        """Create FileReadTool instance."""
        return FileReadTool()

    @pytest.mark.asyncio
    async def test_file_read_with_timeout_success(self, file_read_tool, tmp_path):
        """Test successful file read within timeout."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # Read with explicit timeout
        result = await file_read_tool.execute(path=str(test_file), timeout=5.0)

        assert result.success
        assert result.output == "Hello, World!"
        assert "file_size" in result.metadata

    @pytest.mark.asyncio
    async def test_file_read_adjusts_timeout_for_large_files(
        self, file_read_tool, tmp_path
    ):
        """Test that timeout is adjusted based on file size."""
        # Create a 2MB file
        test_file = tmp_path / "large.txt"
        content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_text(content)

        # Mock the async timeout to capture the timeout value
        with patch("ocode_python.tools.file_tools.async_timeout") as mock_timeout:
            mock_timeout.return_value.__aenter__ = AsyncMock()
            mock_timeout.return_value.__aexit__ = AsyncMock()

            await file_read_tool.execute(
                path=str(test_file), timeout=1.0  # Initial timeout of 1 second
            )

            # Should adjust timeout to at least 2 seconds for 2MB file
            mock_timeout.assert_called()
            args, kwargs = mock_timeout.call_args
            assert args[0] >= 2.0  # Timeout should be at least 2 seconds

    @pytest.mark.asyncio
    async def test_file_read_timeout_error(self, file_read_tool, tmp_path):
        """Test timeout error handling."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # Mock asyncio.get_event_loop().run_in_executor to simulate slow I/O
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_executor = AsyncMock()

            async def slow_read():
                await asyncio.sleep(2.0)  # Simulate slow read
                return b"content"

            mock_executor.run_in_executor = AsyncMock(side_effect=slow_read)
            mock_loop.return_value = mock_executor

            # Also need to mock the async_timeout to actually timeout
            with patch("ocode_python.tools.file_tools.async_timeout") as mock_timeout:
                # Create a context manager that raises TimeoutError
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock()
                mock_cm.__aexit__ = AsyncMock(
                    side_effect=TimeoutError(
                        "File read operation timed out",
                        operation="file_read(test.txt)",
                        duration=0.1,
                    )
                )
                mock_timeout.return_value = mock_cm

                result = await file_read_tool.execute(path=str(test_file), timeout=0.1)

                assert not result.success
                assert "timed out" in result.error
                assert result.metadata.get("error_type") == "timeout_error"

    @pytest.mark.asyncio
    async def test_file_read_streaming_with_timeout(self, file_read_tool, tmp_path):
        """Test streaming read with timeout."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("0123456789" * 10)  # 100 bytes

        # Read with offset and limit
        result = await file_read_tool.execute(
            path=str(test_file), offset=10, limit=20, timeout=5.0
        )

        assert result.success
        assert result.output == "01234567890123456789"  # 20 bytes from offset 10
        assert result.metadata["bytes_read"] == 20
        assert result.metadata["offset"] == 10
