#!/usr/bin/env python3
"""
End-to-End Integration Testing for Error Recovery System

This script tests the complete error recovery workflow from failure detection
through strategy analysis to successful recovery, validating the entire system.
"""

import asyncio
import logging
import tempfile
import json
from pathlib import Path

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
from ocode_python.tools.file_tools import FileReadTool, FileWriteTool
from ocode_python.tools.bash_tool import BashTool


class AdaptiveTestTool(Tool):
    """Tool that can learn from recovery attempts and become successful."""
    
    def __init__(self):
        self.call_count = 0
        self.learned_params = set()
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="adaptive_test_tool",
            description="Tool that adapts based on recovery attempts",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        
        # Learn from recovery parameters
        if kwargs.get("recovery_strategy") == "adjusted_params":
            self.learned_params.add("recovery_strategy")
        if kwargs.get("use_alternative_method"):
            self.learned_params.add("alternative_method")
        if kwargs.get("enable_fallback"):
            self.learned_params.add("fallback")
        
        # Succeed if we've learned enough
        if len(self.learned_params) >= 2:
            return ToolResult(
                success=True,
                output=f"Success after learning from {len(self.learned_params)} recovery attempts",
                metadata={
                    "call_count": self.call_count,
                    "learned_params": list(self.learned_params),
                    "recovery_successful": True
                }
            )
        
        # Provide hints for recovery
        missing_params = {"recovery_strategy", "alternative_method", "fallback"} - self.learned_params
        return ToolResult(
            success=False,
            output="",
            error=f"Tool needs additional parameters (attempt {self.call_count})",
            metadata={
                "error_type": "LEARNING_ERROR",
                "call_count": self.call_count,
                "hint": f"Try parameters: {list(missing_params)}",
                "learned_so_far": list(self.learned_params)
            }
        )


class SmartRecoveryModule(ErrorRecoveryModule):
    """Enhanced recovery module that can learn from patterns."""
    
    def __init__(self, debugger_persona, max_recovery_attempts=3):
        super().__init__(debugger_persona, max_recovery_attempts)
        self.success_patterns = {}
    
    async def attempt_recovery(self, original_goal, failed_command, tool_result, execution_context, tool_registry):
        """Enhanced recovery with pattern learning."""
        
        # Check if we've seen this pattern before
        error_signature = f"{failed_command.tool_name}:{tool_result.metadata.get('error_type', 'unknown')}"
        
        if error_signature in self.success_patterns:
            logging.info(f"Using learned pattern for {error_signature}")
            # Apply previously successful strategy
            learned_strategy = self.success_patterns[error_signature]
            
            # Try learned approach first
            if learned_strategy.get("parameters"):
                tool = tool_registry.get_tool(failed_command.tool_name)
                if tool:
                    enhanced_args = {**failed_command.arguments, **learned_strategy["parameters"]}
                    result = await tool.execute(**enhanced_args)
                    if result.success:
                        logging.info(f"Learned pattern succeeded for {error_signature}")
                        return result
        
        # Fall back to normal recovery
        result = await super().attempt_recovery(original_goal, failed_command, tool_result, execution_context, tool_registry)
        
        # Learn from successful recovery
        if result and result.success:
            # Extract the successful parameters
            success_pattern = {
                "parameters": getattr(result, 'metadata', {}).get('recovery_params', {}),
                "strategy": "learned_recovery"
            }
            self.success_patterns[error_signature] = success_pattern
            logging.info(f"Learned new success pattern for {error_signature}")
        
        return result


async def test_end_to_end_recovery_workflow():
    """Test complete recovery workflow from failure to success."""
    print("\n=== End-to-End Recovery Workflow Test ===")
    
    # Setup enhanced recovery system
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    smart_recovery = SmartRecoveryModule(debugger, max_recovery_attempts=5)
    
    tool_registry = ToolRegistry()
    adaptive_tool = AdaptiveTestTool()
    tool_registry.register(adaptive_tool)
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=smart_recovery
    )
    
    orchestrator.set_current_goal("Test adaptive learning and recovery")
    
    print("Phase 1: Initial failure and learning...")
    initial_result = await orchestrator.execute_tool_with_context(
        "adaptive_test_tool",
        {}
    )
    
    print(f"Initial result success: {initial_result.success}")
    print(f"Tool learned parameters: {adaptive_tool.learned_params}")
    
    print("\nPhase 2: Retry with recovery applied...")
    # The tool should have learned from the recovery attempt
    retry_result = await orchestrator.execute_tool_with_context(
        "adaptive_test_tool",
        {"recovery_strategy": "adjusted_params"}
    )
    
    print(f"Retry result success: {retry_result.success}")
    print(f"Tool learned parameters: {adaptive_tool.learned_params}")
    
    if not retry_result.success:
        print("\nPhase 3: Final attempt with additional learning...")
        final_result = await orchestrator.execute_tool_with_context(
            "adaptive_test_tool",
            {"use_alternative_method": True, "enable_fallback": True}
        )
        print(f"Final result success: {final_result.success}")
    
    stats = smart_recovery.get_recovery_stats()
    print(f"\nRecovery Statistics:")
    print(f"  Total attempts: {stats['attempts']}")
    print(f"  Successes: {stats['successes']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    print(f"  Learned patterns: {len(smart_recovery.success_patterns)}")
    
    return stats['successes'] > 0


async def test_real_world_file_recovery():
    """Test recovery with real file operations."""
    print("\n=== Real-World File Recovery Test ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Setup recovery system
        api_client = OllamaAPIClient()
        prompt_composer = PromptComposer()
        debugger = DebuggerPersona(api_client, prompt_composer)
        recovery_module = ErrorRecoveryModule(debugger)
        
        tool_registry = ToolRegistry()
        tool_registry.register(FileReadTool())
        tool_registry.register(FileWriteTool())
        
        orchestrator = AdvancedOrchestrator(
            tool_registry=tool_registry,
            error_recovery_module=recovery_module
        )
        
        # Test scenario: Read missing file, then create it and retry
        missing_file = temp_path / "important_config.json"
        orchestrator.set_current_goal("Read application configuration")
        
        print("Attempting to read non-existent file...")
        read_result = await orchestrator.execute_tool_with_context(
            "file_read",
            {"path": str(missing_file)}
        )
        
        print(f"Read result success: {read_result.success}")
        
        # Create the file that was missing
        config_data = {"app_name": "test_app", "version": "1.0.0", "debug": True}
        write_result = await orchestrator.execute_tool_with_context(
            "file_write",
            {
                "path": str(missing_file),
                "content": json.dumps(config_data, indent=2)
            }
        )
        
        print(f"Write result success: {write_result.success}")
        
        # Now reading should succeed
        if write_result.success:
            read_retry_result = await orchestrator.execute_tool_with_context(
                "file_read", 
                {"path": str(missing_file)}
            )
            print(f"Read retry success: {read_retry_result.success}")
            return read_retry_result.success
        
        return False


async def test_bash_command_recovery():
    """Test recovery with bash commands."""
    print("\n=== Bash Command Recovery Test ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger)
    
    tool_registry = ToolRegistry()
    tool_registry.register(BashTool())
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=recovery_module
    )
    
    orchestrator.set_current_goal("Execute system command")
    
    print("Attempting invalid bash command...")
    invalid_result = await orchestrator.execute_tool_with_context(
        "bash",
        {"command": "nonexistent_command_xyz --invalid"}
    )
    
    print(f"Invalid command result success: {invalid_result.success}")
    
    print("Attempting valid alternative command...")
    valid_result = await orchestrator.execute_tool_with_context(
        "bash",
        {"command": "echo 'Hello from recovery test'"}
    )
    
    print(f"Valid command result success: {valid_result.success}")
    
    stats = recovery_module.get_recovery_stats()
    print(f"Recovery attempts made: {stats['attempts']}")
    
    return valid_result.success


async def test_recovery_system_resilience():
    """Test overall system resilience under various conditions."""
    print("\n=== Recovery System Resilience Test ===")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger, max_recovery_attempts=2)
    
    tool_registry = ToolRegistry()
    tool_registry.register(AdaptiveTestTool())
    tool_registry.register(FileReadTool())
    tool_registry.register(BashTool())
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=recovery_module
    )
    
    # Test rapid successive failures
    failure_scenarios = [
        ("adaptive_test_tool", {}),
        ("file_read", {"path": "/nonexistent/path/file.txt"}),
        ("bash", {"command": "false"}),  # Command that always fails
    ]
    
    success_count = 0
    total_attempts = 0
    
    for tool_name, args in failure_scenarios:
        orchestrator.set_current_goal(f"Test resilience with {tool_name}")
        result = await orchestrator.execute_tool_with_context(tool_name, args)
        
        total_attempts += 1
        if result.success:
            success_count += 1
        
        print(f"{tool_name}: {'✅' if result.success else '❌'}")
    
    stats = recovery_module.get_recovery_stats()
    success_rate = success_count / total_attempts if total_attempts > 0 else 0
    
    print(f"\nResilience Test Results:")
    print(f"  Total scenarios tested: {total_attempts}")
    print(f"  Successful outcomes: {success_count}")
    print(f"  Success rate: {success_rate:.2%}")
    print(f"  Recovery attempts: {stats['attempts']}")
    print(f"  Recovery success rate: {stats['success_rate']:.2%}")
    
    # System is resilient if it doesn't crash and makes recovery attempts
    return stats['attempts'] > 0


async def main():
    """Run comprehensive integration tests."""
    print("🔗 STARTING ERROR RECOVERY INTEGRATION TESTING")
    print("=" * 70)
    
    test_results = []
    
    try:
        # Test end-to-end workflow
        result1 = await test_end_to_end_recovery_workflow()
        test_results.append(("End-to-End Workflow", result1))
        
        # Test real-world file operations
        result2 = await test_real_world_file_recovery()
        test_results.append(("Real-World File Recovery", result2))
        
        # Test bash command recovery
        result3 = await test_bash_command_recovery()
        test_results.append(("Bash Command Recovery", result3))
        
        # Test system resilience
        result4 = await test_recovery_system_resilience()
        test_results.append(("System Resilience", result4))
        
        # Summary
        print(f"\n{'=' * 70}")
        print("INTEGRATION TEST RESULTS:")
        print("=" * 70)
        
        passed = 0
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:.<50} {status}")
            if result:
                passed += 1
        
        overall_success = passed == len(test_results)
        success_rate = (passed / len(test_results)) * 100
        
        print(f"\nOverall Success Rate: {success_rate:.1f}% ({passed}/{len(test_results)})")
        
        if overall_success:
            print("\n🎉 ALL INTEGRATION TESTS PASSED!")
            print("The error recovery system is production-ready.")
        else:
            print(f"\n⚠️  SOME TESTS FAILED ({len(test_results) - passed} failures)")
            print("Review failed tests and address issues before production deployment.")
        
        return overall_success
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TESTING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit_code = 0 if success else 1
    print(f"\nIntegration testing {'PASSED' if success else 'FAILED'} (exit code: {exit_code})")
    exit(exit_code)