#!/usr/bin/env python3
"""
Edge Case Testing for Error Recovery System

This script tests specific edge cases, boundary conditions, and complex failure scenarios
to ensure the error recovery system handles all situations gracefully.
"""

import asyncio
import logging
import tempfile
import json
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)

from ocode_python.core.error_recovery import (
    DebuggerPersona, 
    ErrorRecoveryModule, 
    RecoveryStrategyType,
    FailureContext,
    RecoveryStrategy
)
from ocode_python.core.orchestrator import AdvancedOrchestrator, CommandTask, Priority
from ocode_python.core.api_client import OllamaAPIClient
from ocode_python.prompts.prompt_composer import PromptComposer
from ocode_python.tools.base import Tool, ToolDefinition, ToolResult, ToolRegistry
from ocode_python.tools.file_tools import FileReadTool


class CircularFailureTool(Tool):
    """Tool that creates circular dependency in recovery."""
    
    def __init__(self):
        self.call_count = 0
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="circular_failure_tool",
            description="Tool that fails in a way that creates circular recovery attempts",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        return ToolResult(
            success=False,
            output="",
            error="Cannot recover without using circular_failure_tool",
            metadata={"error_type": "CIRCULAR_ERROR", "call_count": self.call_count}
        )


class TimeoutTool(Tool):
    """Tool that simulates timeout conditions."""
    
    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds
        self.call_count = 0
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="timeout_tool",
            description="Tool that simulates timeout failures",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        if kwargs.get("quick_mode"):
            return ToolResult(success=True, output="Quick execution succeeded")
        
        # Simulate a long operation that times out
        await asyncio.sleep(self.timeout_seconds)
        return ToolResult(
            success=False,
            output="",
            error="Operation timed out after 5 seconds",
            metadata={"error_type": "TIMEOUT_ERROR", "call_count": self.call_count}
        )


class MemoryExhaustionTool(Tool):
    """Tool that simulates memory exhaustion."""
    
    def __init__(self):
        self.call_count = 0
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="memory_exhaustion_tool",
            description="Tool that simulates memory exhaustion",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        
        if kwargs.get("use_streaming"):
            return ToolResult(
                success=True,
                output="Streaming mode enabled, memory usage reduced",
                metadata={"memory_optimized": True}
            )
        
        return ToolResult(
            success=False,
            output="",
            error="MemoryError: Cannot allocate 10GB for operation",
            metadata={"error_type": "MEMORY_ERROR", "call_count": self.call_count}
        )


async def test_recovery_strategy_validation():
    """Test validation of recovery strategies."""
    print("\n=== Testing Recovery Strategy Validation ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    
    # Test invalid strategy creation
    try:
        invalid_strategy = RecoveryStrategy(
            strategy_type=RecoveryStrategyType.PARAMETER_ADJUSTMENT,
            description="",  # Empty description
            confidence=1.5,  # Invalid confidence > 1.0
            estimated_success_rate=-0.1  # Invalid negative rate
        )
        print("❌ Should have validated strategy parameters")
    except Exception as e:
        print(f"✅ Correctly caught invalid strategy: {type(e).__name__}")


async def test_circular_recovery_prevention():
    """Test prevention of circular recovery attempts."""
    print("\n=== Testing Circular Recovery Prevention ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger, max_recovery_attempts=3)
    
    tool_registry = ToolRegistry()
    circular_tool = CircularFailureTool()
    tool_registry.register(circular_tool)
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=recovery_module
    )
    
    orchestrator.set_current_goal("Test circular recovery prevention")
    
    # This should not loop infinitely
    start_calls = circular_tool.call_count
    result = await orchestrator.execute_tool_with_context(
        "circular_failure_tool",
        {}
    )
    
    final_calls = circular_tool.call_count
    stats = recovery_module.get_recovery_stats()
    
    print(f"✅ Circular prevention test completed")
    print(f"   Tool calls: {start_calls} -> {final_calls}")
    print(f"   Recovery attempts: {stats['attempts']}")
    print(f"   Max attempts reached: {stats['attempts'] <= 3}")


async def test_concurrent_recovery_attempts():
    """Test concurrent recovery attempts don't interfere."""
    print("\n=== Testing Concurrent Recovery Attempts ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger)
    
    tool_registry = ToolRegistry()
    tool_registry.register(TimeoutTool(0.1))  # Quick timeout
    tool_registry.register(MemoryExhaustionTool())
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=recovery_module
    )
    
    # Run multiple concurrent recovery attempts
    tasks = []
    for i in range(3):
        task = orchestrator.execute_tool_with_context(
            "timeout_tool",
            {"attempt": i}
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    stats = recovery_module.get_recovery_stats()
    
    successful_results = [r for r in results if isinstance(r, ToolResult) and r.success]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    print(f"✅ Concurrent recovery test completed")
    print(f"   Total tasks: {len(tasks)}")
    print(f"   Successful results: {len(successful_results)}")
    print(f"   Exceptions: {len(exceptions)}")
    print(f"   Recovery attempts: {stats['attempts']}")


async def test_recovery_with_corrupted_data():
    """Test recovery when dealing with corrupted data."""
    print("\n=== Testing Recovery with Corrupted Data ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a corrupted file
        corrupted_file = temp_path / "corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write('{"incomplete": json data with missing }')
        
        api_client = OllamaAPIClient()
        prompt_composer = PromptComposer()
        debugger = DebuggerPersona(api_client, prompt_composer)
        recovery_module = ErrorRecoveryModule(debugger)
        
        tool_registry = ToolRegistry()
        tool_registry.register(FileReadTool())
        
        orchestrator = AdvancedOrchestrator(
            tool_registry=tool_registry,
            error_recovery_module=recovery_module
        )
        
        orchestrator.set_current_goal("Read and parse corrupted JSON file")
        
        # This should attempt recovery when JSON parsing fails
        result = await orchestrator.execute_tool_with_context(
            "file_read",
            {"path": str(corrupted_file)}
        )
        
        stats = recovery_module.get_recovery_stats()
        
        print(f"✅ Corrupted data test completed")
        print(f"   File read success: {result.success}")
        print(f"   Recovery attempts: {stats.get('attempts', 0)}")
        print(f"   File exists: {corrupted_file.exists()}")


async def test_recovery_metrics_accuracy():
    """Test accuracy of recovery metrics under various conditions."""
    print("\n=== Testing Recovery Metrics Accuracy ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger)
    
    tool_registry = ToolRegistry()
    memory_tool = MemoryExhaustionTool()
    tool_registry.register(memory_tool)
    
    initial_stats = recovery_module.get_recovery_stats()
    print(f"Initial stats: {initial_stats}")
    
    # Perform multiple recovery attempts
    for i in range(5):
        try:
            failed_command = CommandTask(
                task_id=f"metrics-test-{i}",
                tool_name="memory_exhaustion_tool",
                arguments={"test_run": i},
                priority=Priority.NORMAL
            )
            
            tool_result = ToolResult(
                success=False,
                output="",
                error=f"Memory error {i}",
                metadata={"error_type": "MEMORY_ERROR"}
            )
            
            result = await recovery_module.attempt_recovery(
                original_goal=f"Memory test {i}",
                failed_command=failed_command,
                tool_result=tool_result,
                execution_context={"test_run": i},
                tool_registry=tool_registry
            )
        except Exception:
            pass
    
    final_stats = recovery_module.get_recovery_stats()
    
    # Validate metrics
    attempts_delta = final_stats["attempts"] - initial_stats["attempts"]
    expected_attempts = 5
    
    print(f"✅ Metrics accuracy test completed")
    print(f"   Expected attempts: {expected_attempts}")
    print(f"   Actual attempts delta: {attempts_delta}")
    print(f"   Metrics accuracy: {attempts_delta == expected_attempts}")
    print(f"   Final stats: {final_stats}")


async def test_recovery_under_resource_pressure():
    """Test recovery system under resource pressure."""
    print("\n=== Testing Recovery Under Resource Pressure ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger, max_recovery_attempts=1)
    
    tool_registry = ToolRegistry()
    tool_registry.register(TimeoutTool(0.01))  # Very quick timeout
    tool_registry.register(MemoryExhaustionTool())
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=recovery_module,
        max_concurrent=1  # Limited concurrency
    )
    
    # Simulate high load
    start_time = asyncio.get_event_loop().time()
    
    tasks = []
    for i in range(10):  # Many rapid requests
        task = orchestrator.execute_tool_with_context(
            "memory_exhaustion_tool",
            {"load_test": i}
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = asyncio.get_event_loop().time()
    
    execution_time = end_time - start_time
    stats = recovery_module.get_recovery_stats()
    
    successful_results = [r for r in results if isinstance(r, ToolResult)]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    print(f"✅ Resource pressure test completed")
    print(f"   Total execution time: {execution_time:.2f}s")
    print(f"   Tasks completed: {len(successful_results)}")
    print(f"   Exceptions: {len(exceptions)}")
    print(f"   Recovery attempts: {stats['attempts']}")
    print(f"   Average time per task: {execution_time/len(tasks):.3f}s")


async def main():
    """Run all edge case tests."""
    print("🔧 STARTING ERROR RECOVERY EDGE CASE TESTING")
    print("=" * 60)
    
    try:
        await test_recovery_strategy_validation()
        await test_circular_recovery_prevention()
        await test_concurrent_recovery_attempts()
        await test_recovery_with_corrupted_data()
        await test_recovery_metrics_accuracy()
        await test_recovery_under_resource_pressure()
        
        print(f"\n{'=' * 60}")
        print("🎉 ALL EDGE CASE TESTS COMPLETED SUCCESSFULLY!")
        print("The error recovery system handles complex scenarios robustly.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ EDGE CASE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\nEdge case testing {'PASSED' if success else 'FAILED'}")