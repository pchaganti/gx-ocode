#!/usr/bin/env python3
"""
Comprehensive Deep Testing Suite for Error Recovery System

This suite provides exhaustive testing of the Self-Improving Agent Architecture's
error recovery capabilities, including edge cases, stress testing, and real-world scenarios.
"""

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
import sys
import os

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('error_recovery_test.log')
    ]
)

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
from ocode_python.tools.bash_tool import BashTool
from ocode_python.tools.file_tools import FileReadTool, FileWriteTool


class TestResults:
    """Tracks comprehensive test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.performance_metrics = {}
        self.recovery_success_rates = {}
    
    def add_test_result(self, test_name: str, passed: bool, details: str = "", metrics: Dict = None):
        """Record a test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            self.tests_failed += 1
            self.failures.append(f"{test_name}: {details}")
            print(f"❌ {test_name}: FAILED - {details}")
        
        if metrics:
            self.performance_metrics[test_name] = metrics
        
        logging.info(f"Test {test_name}: {'PASSED' if passed else 'FAILED'} - {details}")
    
    def print_summary(self):
        """Print comprehensive test summary."""
        print(f"\n{'='*60}")
        print(f"COMPREHENSIVE ERROR RECOVERY TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failures:
            print(f"\n❌ FAILURES:")
            for failure in self.failures:
                print(f"  - {failure}")
        
        if self.performance_metrics:
            print(f"\n📊 PERFORMANCE METRICS:")
            for test, metrics in self.performance_metrics.items():
                print(f"  {test}:")
                for key, value in metrics.items():
                    print(f"    {key}: {value}")


class AdvancedFailingTool(Tool):
    """Tool that simulates different types of realistic failures."""
    
    def __init__(self, failure_type: str = "permission"):
        self.failure_type = failure_type
        self.call_count = 0
        self.metadata = {}
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="advanced_failing_tool",
            description="Tool that simulates realistic failure scenarios",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        
        if self.failure_type == "permission":
            return ToolResult(
                success=False,
                output="",
                error="Permission denied: /var/log/system.log",
                metadata={
                    "error_type": "PERMISSION_ERROR",
                    "file_path": "/var/log/system.log",
                    "user": "non_root",
                    "call_count": self.call_count
                }
            )
        elif self.failure_type == "network":
            return ToolResult(
                success=False,
                output="",
                error="Connection timeout: Unable to reach api.example.com:443",
                metadata={
                    "error_type": "NETWORK_ERROR", 
                    "host": "api.example.com",
                    "port": 443,
                    "timeout": 30,
                    "call_count": self.call_count
                }
            )
        elif self.failure_type == "dependency":
            return ToolResult(
                success=False,
                output="",
                error="ModuleNotFoundError: No module named 'missing_package'",
                metadata={
                    "error_type": "DEPENDENCY_ERROR",
                    "missing_module": "missing_package",
                    "python_version": "3.9.7",
                    "call_count": self.call_count
                }
            )
        elif self.failure_type == "resource":
            return ToolResult(
                success=False,
                output="",
                error="OSError: [Errno 28] No space left on device",
                metadata={
                    "error_type": "RESOURCE_ERROR",
                    "errno": 28,
                    "device": "/dev/disk1s1",
                    "available_space": 0,
                    "call_count": self.call_count
                }
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown failure type: {self.failure_type}",
                metadata={"error_type": "UNKNOWN_ERROR", "call_count": self.call_count}
            )


class PartiallyFixableTool(Tool):
    """Tool that can be fixed with specific parameter combinations."""
    
    def __init__(self):
        self.call_count = 0
        self.successful_params = {"retry": True, "use_fallback": True, "timeout": 60}
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="partially_fixable_tool",
            description="Tool that requires specific parameters to work",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        
        # Check if all required parameters are present
        has_all_params = all(
            kwargs.get(key) == value 
            for key, value in self.successful_params.items()
        )
        
        if has_all_params:
            return ToolResult(
                success=True,
                output=f"Success after {self.call_count} attempts with correct parameters",
                metadata={
                    "call_count": self.call_count,
                    "fixed": True,
                    "required_params": self.successful_params
                }
            )
        else:
            missing_params = {
                key: value for key, value in self.successful_params.items()
                if kwargs.get(key) != value
            }
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid configuration (attempt {self.call_count})",
                metadata={
                    "error_type": "CONFIGURATION_ERROR",
                    "call_count": self.call_count,
                    "missing_params": missing_params,
                    "hint": "Check retry, use_fallback, and timeout parameters"
                }
            )


class RecoveryTestTool(Tool):
    """Tool that becomes successful after recovery strategies are applied."""
    
    def __init__(self):
        self.call_count = 0
        self.recovery_applied = False
        super().__init__()
        
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="recovery_test_tool",
            description="Tool for testing recovery strategy application",
            parameters=[]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        
        # Succeed if recovery parameters are present
        if kwargs.get("recovery_strategy") == "adjusted_params":
            self.recovery_applied = True
            return ToolResult(
                success=True,
                output="Recovery successful with adjusted parameters",
                metadata={
                    "call_count": self.call_count,
                    "recovery_applied": True,
                    "strategy": "adjusted_params"
                }
            )
        
        return ToolResult(
            success=False,
            output="",
            error="Tool requires recovery strategy to be applied",
            metadata={
                "error_type": "RECOVERY_REQUIRED",
                "call_count": self.call_count,
                "hint": "Apply recovery_strategy=adjusted_params"
            }
        )


async def test_debugger_persona_analysis(results: TestResults):
    """Test the DebuggerPersona's failure analysis capabilities."""
    print(f"\n{'='*50}")
    print("TESTING DEBUGGER PERSONA ANALYSIS")
    print(f"{'='*50}")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    
    # Test different failure types
    failure_types = [
        ("permission", "Permission denied errors"),
        ("network", "Network connectivity issues"), 
        ("dependency", "Missing dependency errors"),
        ("resource", "Resource exhaustion errors")
    ]
    
    for failure_type, description in failure_types:
        start_time = time.time()
        
        try:
            # Create realistic failure context
            failed_command = CommandTask(
                task_id=f"test-{failure_type}",
                tool_name="advanced_failing_tool",
                arguments={"failure_type": failure_type},
                priority=Priority.NORMAL
            )
            
            tool_result = ToolResult(
                success=False,
                output="",
                error=f"Simulated {failure_type} error for testing",
                metadata={"error_type": f"{failure_type.upper()}_ERROR"}
            )
            
            failure_context = FailureContext(
                original_goal=f"Test {description.lower()}",
                failed_tool="advanced_failing_tool",
                failed_command=failed_command,
                tool_result=tool_result,
                execution_context={"test_scenario": failure_type}
            )
            
            # Test strategy analysis (will use fallback if no LLM available)
            strategies = await debugger.analyze_failure(failure_context)
            
            analysis_time = time.time() - start_time
            
            # Validate results
            if strategies and len(strategies) > 0:
                strategy_types = [s.strategy_type.value for s in strategies]
                results.add_test_result(
                    f"Analyze {failure_type} failure",
                    True,
                    f"Generated {len(strategies)} strategies: {strategy_types}",
                    {"analysis_time": analysis_time, "strategy_count": len(strategies)}
                )
            else:
                results.add_test_result(
                    f"Analyze {failure_type} failure",
                    False,
                    "No recovery strategies generated"
                )
                
        except Exception as e:
            results.add_test_result(
                f"Analyze {failure_type} failure",
                False,
                f"Exception: {str(e)}"
            )


async def test_error_recovery_module(results: TestResults):
    """Test ErrorRecoveryModule coordination and execution."""
    print(f"\n{'='*50}")
    print("TESTING ERROR RECOVERY MODULE")
    print(f"{'='*50}")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger, max_recovery_attempts=3)
    
    # Create tool registry with test tools
    tool_registry = ToolRegistry()
    
    # Test tools for different scenarios
    fixable_tool = PartiallyFixableTool()
    recovery_tool = RecoveryTestTool()
    
    tool_registry.register(fixable_tool)
    tool_registry.register(recovery_tool)
    tool_registry.register(FileReadTool())
    tool_registry.register(FileWriteTool())
    
    # Test 1: Recovery with parameter adjustment
    try:
        start_time = time.time()
        
        failed_command = CommandTask(
            task_id="recovery-test-1",
            tool_name="partially_fixable_tool",
            arguments={},
            priority=Priority.NORMAL
        )
        
        tool_result = ToolResult(
            success=False,
            output="",
            error="Invalid configuration",
            metadata={"error_type": "CONFIGURATION_ERROR"}
        )
        
        recovery_result = await recovery_module.attempt_recovery(
            original_goal="Test parameter adjustment recovery",
            failed_command=failed_command,
            tool_result=tool_result,
            execution_context={"test_case": "parameter_adjustment"},
            tool_registry=tool_registry
        )
        
        recovery_time = time.time() - start_time
        
        # Check if recovery succeeded or at least attempted
        stats = recovery_module.get_recovery_stats()
        
        results.add_test_result(
            "Parameter adjustment recovery",
            stats["attempts"] > 0,
            f"Recovery attempts: {stats['attempts']}, Successes: {stats['successes']}",
            {"recovery_time": recovery_time, "stats": stats}
        )
        
    except Exception as e:
        results.add_test_result(
            "Parameter adjustment recovery",
            False,
            f"Exception: {str(e)}"
        )


async def test_orchestrator_integration(results: TestResults):
    """Test integration between orchestrator and error recovery."""
    print(f"\n{'='*50}")
    print("TESTING ORCHESTRATOR INTEGRATION")
    print(f"{'='*50}")
    
    # Setup orchestrator with error recovery
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger)
    
    tool_registry = ToolRegistry()
    tool_registry.register(AdvancedFailingTool("permission"))
    tool_registry.register(PartiallyFixableTool())
    tool_registry.register(FileReadTool())
    
    orchestrator = AdvancedOrchestrator(
        tool_registry=tool_registry,
        error_recovery_module=recovery_module
    )
    
    # Test 1: Direct tool execution with recovery
    try:
        start_time = time.time()
        orchestrator.set_current_goal("Test orchestrator error recovery integration")
        
        result = await orchestrator.execute_tool_with_context(
            "advanced_failing_tool",
            {"failure_type": "permission"}
        )
        
        execution_time = time.time() - start_time
        
        # Check recovery stats
        stats = recovery_module.get_recovery_stats()
        
        results.add_test_result(
            "Orchestrator error recovery integration",
            stats["attempts"] > 0,  # Should have attempted recovery
            f"Execution time: {execution_time:.2f}s, Recovery attempts: {stats['attempts']}",
            {"execution_time": execution_time, "recovery_stats": stats}
        )
        
    except Exception as e:
        results.add_test_result(
            "Orchestrator error recovery integration",
            False,
            f"Exception: {str(e)}"
        )


async def test_real_world_scenarios(results: TestResults):
    """Test real-world failure scenarios."""
    print(f"\n{'='*50}")
    print("TESTING REAL-WORLD SCENARIOS")
    print(f"{'='*50}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Setup
        api_client = OllamaAPIClient()
        prompt_composer = PromptComposer()
        debugger = DebuggerPersona(api_client, prompt_composer)
        recovery_module = ErrorRecoveryModule(debugger)
        
        tool_registry = ToolRegistry()
        tool_registry.register(FileReadTool())
        tool_registry.register(FileWriteTool())
        tool_registry.register(BashTool())
        
        orchestrator = AdvancedOrchestrator(
            tool_registry=tool_registry,
            error_recovery_module=recovery_module
        )
        
        # Scenario 1: Read non-existent file
        try:
            start_time = time.time()
            orchestrator.set_current_goal("Read configuration file")
            
            result = await orchestrator.execute_tool_with_context(
                "file_read",
                {"path": str(temp_path / "config.json")}
            )
            
            execution_time = time.time() - start_time
            stats = recovery_module.get_recovery_stats()
            
            results.add_test_result(
                "File not found scenario",
                True,  # Always pass if no exception
                f"File read result: {result.success}, Recovery attempts: {stats['attempts']}",
                {"execution_time": execution_time, "result_success": result.success}
            )
            
        except Exception as e:
            results.add_test_result(
                "File not found scenario",
                False,
                f"Exception: {str(e)}"
            )
        
        # Scenario 2: Invalid bash command
        try:
            start_time = time.time()
            orchestrator.set_current_goal("Execute system command")
            
            result = await orchestrator.execute_tool_with_context(
                "bash",
                {"command": "nonexistent_command --invalid-flag"}
            )
            
            execution_time = time.time() - start_time
            stats = recovery_module.get_recovery_stats()
            
            results.add_test_result(
                "Invalid command scenario",
                True,  # Always pass if no exception
                f"Command result: {result.success}, Recovery attempts: {stats['attempts']}",
                {"execution_time": execution_time, "result_success": result.success}
            )
            
        except Exception as e:
            results.add_test_result(
                "Invalid command scenario",
                False,
                f"Exception: {str(e)}"
            )


async def test_stress_and_edge_cases(results: TestResults):
    """Test stress conditions and edge cases."""
    print(f"\n{'='*50}")
    print("TESTING STRESS CONDITIONS AND EDGE CASES")
    print(f"{'='*50}")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger, max_recovery_attempts=1)
    
    # Test 1: Null/empty inputs
    try:
        failed_command = CommandTask(
            task_id="stress-test-1",
            tool_name="",  # Empty tool name
            arguments={},
            priority=Priority.NORMAL
        )
        
        tool_result = ToolResult(
            success=False,
            output="",
            error="",  # Empty error
            metadata={}
        )
        
        tool_registry = ToolRegistry()
        
        recovery_result = await recovery_module.attempt_recovery(
            original_goal="",  # Empty goal
            failed_command=failed_command,
            tool_result=tool_result,
            execution_context={},
            tool_registry=tool_registry
        )
        
        results.add_test_result(
            "Empty inputs handling",
            True,  # Should handle gracefully
            "Handled empty inputs without crashing"
        )
        
    except Exception as e:
        results.add_test_result(
            "Empty inputs handling",
            False,
            f"Failed to handle empty inputs: {str(e)}"
        )
    
    # Test 2: Very long error messages
    try:
        long_error = "ERROR: " + "X" * 10000  # Very long error message
        
        failed_command = CommandTask(
            task_id="stress-test-2",
            tool_name="test_tool",
            arguments={"data": "Y" * 5000},  # Large arguments
            priority=Priority.NORMAL
        )
        
        tool_result = ToolResult(
            success=False,
            output="",
            error=long_error,
            metadata={"large_data": "Z" * 5000}
        )
        
        failure_context = FailureContext(
            original_goal="Test large data handling",
            failed_tool="test_tool",
            failed_command=failed_command,
            tool_result=tool_result,
            execution_context={"stress_test": True}
        )
        
        strategies = await debugger.analyze_failure(failure_context)
        
        results.add_test_result(
            "Large data handling",
            True,
            f"Handled large data, generated {len(strategies)} strategies"
        )
        
    except Exception as e:
        results.add_test_result(
            "Large data handling",
            False,
            f"Failed to handle large data: {str(e)}"
        )
    
    # Test 3: Rapid successive failures
    try:
        start_time = time.time()
        
        tool_registry = ToolRegistry()
        tool_registry.register(AdvancedFailingTool("network"))
        
        orchestrator = AdvancedOrchestrator(
            tool_registry=tool_registry,
            error_recovery_module=recovery_module
        )
        
        # Execute multiple failing tools rapidly
        tasks = []
        for i in range(5):
            task = orchestrator.execute_tool_with_context(
                "advanced_failing_tool",
                {"failure_type": "network", "attempt": i}
            )
            tasks.append(task)
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        execution_time = time.time() - start_time
        stats = recovery_module.get_recovery_stats()
        
        exceptions = [r for r in results_list if isinstance(r, Exception)]
        
        results.add_test_result(
            "Rapid successive failures",
            len(exceptions) == 0,
            f"Handled {len(tasks)} rapid failures in {execution_time:.2f}s, {len(exceptions)} exceptions",
            {"execution_time": execution_time, "recovery_stats": stats}
        )
        
    except Exception as e:
        results.add_test_result(
            "Rapid successive failures",
            False,
            f"Exception: {str(e)}"
        )


async def test_recovery_metrics_and_logging(results: TestResults):
    """Test recovery metrics collection and logging."""
    print(f"\n{'='*50}")
    print("TESTING RECOVERY METRICS AND LOGGING")
    print(f"{'='*50}")
    
    api_client = OllamaAPIClient()
    prompt_composer = PromptComposer()
    debugger = DebuggerPersona(api_client, prompt_composer)
    recovery_module = ErrorRecoveryModule(debugger)
    
    # Create multiple recovery attempts to test metrics
    tool_registry = ToolRegistry()
    tool_registry.register(PartiallyFixableTool())
    tool_registry.register(AdvancedFailingTool("permission"))
    
    initial_stats = recovery_module.get_recovery_stats()
    
    # Perform several recovery attempts
    for i in range(3):
        try:
            failed_command = CommandTask(
                task_id=f"metrics-test-{i}",
                tool_name="partially_fixable_tool",
                arguments={},
                priority=Priority.NORMAL
            )
            
            tool_result = ToolResult(
                success=False,
                output="",
                error=f"Test error {i}",
                metadata={"error_type": "TEST_ERROR", "attempt": i}
            )
            
            await recovery_module.attempt_recovery(
                original_goal=f"Metrics test {i}",
                failed_command=failed_command,
                tool_result=tool_result,
                execution_context={"metrics_test": True},
                tool_registry=tool_registry
            )
            
        except Exception:
            pass  # Expected for testing
    
    final_stats = recovery_module.get_recovery_stats()
    
    # Validate metrics
    attempts_increased = final_stats["attempts"] > initial_stats["attempts"]
    has_success_rate = "success_rate" in final_stats
    has_strategy_usage = "strategy_usage" in final_stats
    
    results.add_test_result(
        "Recovery metrics collection",
        attempts_increased and has_success_rate and has_strategy_usage,
        f"Stats: {final_stats}",
        {"final_stats": final_stats}
    )
    
    # Test logging by checking if recovery history is maintained
    history_length = len(debugger.recovery_history)
    
    results.add_test_result(
        "Recovery history logging",
        history_length > 0,
        f"Recovery history contains {history_length} entries"
    )


async def main():
    """Run comprehensive deep testing suite."""
    print("🚀 STARTING COMPREHENSIVE ERROR RECOVERY DEEP TESTING")
    print("="*80)
    
    results = TestResults()
    
    try:
        # Check if Ollama is available
        api_client = OllamaAPIClient()
        health = await api_client.check_health()
        
        if not health:
            print("⚠️  Ollama API not available - running offline tests only")
            print("   Some LLM-based analysis tests will use fallback strategies")
        else:
            print("✅ Ollama API available - running full test suite")
        
        # Run comprehensive test suites
        await test_debugger_persona_analysis(results)
        await test_error_recovery_module(results)
        await test_orchestrator_integration(results)
        await test_real_world_scenarios(results)
        await test_stress_and_edge_cases(results)
        await test_recovery_metrics_and_logging(results)
        
        # Mark test completion
        results.print_summary()
        
        # Write detailed results to file
        with open('error_recovery_test_results.json', 'w') as f:
            json.dump({
                "summary": {
                    "tests_run": results.tests_run,
                    "tests_passed": results.tests_passed,
                    "tests_failed": results.tests_failed,
                    "success_rate": results.tests_passed / results.tests_run * 100
                },
                "performance_metrics": results.performance_metrics,
                "failures": results.failures
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: error_recovery_test_results.json")
        print(f"📄 Detailed logs saved to: error_recovery_test.log")
        
        # Overall assessment
        if results.tests_failed == 0:
            print(f"\n🎉 ALL TESTS PASSED! Error recovery system is robust and ready.")
        elif results.tests_failed < results.tests_run * 0.1:  # Less than 10% failure
            print(f"\n✅ MOSTLY SUCCESSFUL with {results.tests_failed} minor issues.")
        else:
            print(f"\n⚠️  SOME ISSUES FOUND: {results.tests_failed} tests failed.")
        
        return results.tests_failed == 0
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in test suite: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)