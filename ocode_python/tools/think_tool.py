"""
Structured reasoning and analysis tool for OCode.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class ThinkTool(Tool):
    """Tool for structured reasoning, analysis, and decision-making workflows."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the think tool specification.

        Returns:
            ToolDefinition with parameters for structured reasoning including
            analysis types, topic, context, options, and output format.
        """
        return ToolDefinition(
            name="think",
            description="Perform structured reasoning, analysis, and decision-making with various thinking frameworks",  # noqa: E501
            parameters=[
                ToolParameter(
                    name="thinking_type",
                    type="string",
                    description="Type of thinking: 'analyze', 'compare', 'pros_cons', 'root_cause', 'decision', 'brainstorm', 'breakdown', 'risk_assessment'",  # noqa: E501
                    required=True,
                ),
                ToolParameter(
                    name="topic",
                    type="string",
                    description="The main topic, problem, or question to think about",
                    required=True,
                ),
                ToolParameter(
                    name="context",
                    type="string",
                    description="Additional context, background information, or constraints",  # noqa: E501
                    required=False,
                ),
                ToolParameter(
                    name="options",
                    type="array",
                    description="List of options, alternatives, or solutions to evaluate (for comparison/decision types)",  # noqa: E501
                    required=False,
                ),
                ToolParameter(
                    name="criteria",
                    type="array",
                    description="Evaluation criteria or factors to consider",
                    required=False,
                ),
                ToolParameter(
                    name="save_to_memory",
                    type="boolean",
                    description="Save the thinking process to memory for later reference",  # noqa: E501
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="output_format",
                    type="string",
                    description="Output format: 'structured', 'markdown', 'json'",
                    required=False,
                    default="structured",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Perform structured thinking and analysis."""
        try:
            # Extract parameters
            thinking_type = kwargs.get("thinking_type")
            topic = kwargs.get("topic")
            context = kwargs.get("context")
            options = kwargs.get("options")
            criteria = kwargs.get("criteria")
            save_to_memory = kwargs.get("save_to_memory", False)
            output_format = kwargs.get("output_format", "structured")

            if not thinking_type or not topic:
                return ToolResult(
                    success=False,
                    output="",
                    error="thinking_type and topic are required parameters",
                )

            # Initialize thinking session
            thinking_session: Dict[str, Any] = {
                "type": thinking_type,
                "topic": topic,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "results": {},
            }

            # Perform the requested thinking type
            if thinking_type == "analyze":
                results = await self._perform_analysis(topic, context, criteria)
            elif thinking_type == "compare":
                results = await self._perform_comparison(
                    topic, options, criteria, context
                )
            elif thinking_type == "pros_cons":
                results = await self._perform_pros_cons_analysis(topic, context)
            elif thinking_type == "root_cause":
                results = await self._perform_root_cause_analysis(topic, context)
            elif thinking_type == "decision":
                results = await self._perform_decision_making(
                    topic, options, criteria, context
                )
            elif thinking_type == "brainstorm":
                results = await self._perform_brainstorming(topic, context)
            elif thinking_type == "breakdown":
                results = await self._perform_breakdown(topic, context)
            elif thinking_type == "risk_assessment":
                results = await self._perform_risk_assessment(topic, context)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown thinking type: {thinking_type}",
                )

            thinking_session["results"] = results

            # Save to memory if requested
            if save_to_memory:
                await self._save_to_memory(thinking_session)

            # Format output
            if output_format == "json":
                output = json.dumps(thinking_session, indent=2)
            elif output_format == "markdown":
                output = self._format_markdown_output(thinking_session)
            else:  # structured
                output = self._format_structured_output(thinking_session)

            return ToolResult(success=True, output=output, metadata=thinking_session)

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error in thinking process: {str(e)}"
            )

    async def _perform_analysis(
        self,
        topic: str,
        context: Optional[str] = None,
        criteria: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform structured analysis of a topic."""
        analysis: Dict[str, Any] = {
            "summary": f"Analysis of: {topic}",
            "key_aspects": [],
            "observations": [],
            "implications": [],
            "recommendations": [],
        }

        # Generate key aspects to analyze
        default_aspects = [
            "Current State",
            "Strengths",
            "Weaknesses",
            "Opportunities",
            "Constraints",
            "Dependencies",
        ]

        aspects = criteria if criteria else default_aspects

        for aspect in aspects:
            analysis["key_aspects"].append(
                {
                    "aspect": aspect,
                    "description": f"Consider {aspect.lower()} related to {topic}",
                    "importance": "medium",
                }
            )

        # Add context-based observations
        if context:
            analysis["observations"].append(f"Context: {context}")

        analysis["framework"] = "Structured Analysis Framework"
        return analysis

    async def _perform_comparison(
        self,
        topic: str,
        options: Optional[List[str]] = None,
        criteria: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare multiple options or alternatives."""
        comparison: Dict[str, Any] = {
            "summary": f"Comparison for: {topic}",
            "options": options or [],
            "criteria": criteria
            or ["Cost", "Complexity", "Benefits", "Risks", "Timeline"],
            "matrix": {},
            "rankings": [],
            "recommendation": "",
        }

        if not options:
            comparison["note"] = (
                "No specific options provided. Consider defining alternatives to compare."  # noqa: E501
            )
            return comparison

        # Create comparison matrix
        for option in options:
            comparison["matrix"][option] = {}
            for criterion in comparison["criteria"]:
                comparison["matrix"][option][criterion] = {
                    "score": 0,  # Placeholder for scoring
                    "notes": f"Evaluate {option} against {criterion.lower()}",
                }

        comparison["framework"] = "Multi-Criteria Decision Analysis"
        return comparison

    async def _perform_pros_cons_analysis(
        self, topic: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze pros and cons of a decision or approach."""
        pros_cons: Dict[str, Any] = {
            "summary": f"Pros and Cons of: {topic}",
            "pros": [],
            "cons": [],
            "neutral_factors": [],
            "overall_assessment": "",
            "recommendation": "",
        }

        # Template structure for systematic analysis
        pros_cons["pros"] = [
            "Benefits: List potential benefits and advantages",
            "Opportunities: Identify opportunities this creates",
            "Strengths: Highlight strengths or positive aspects",
        ]

        pros_cons["cons"] = [
            "Costs: Consider financial and resource costs",
            "Risks: Identify potential risks and downsides",
            "Challenges: Note implementation challenges",
        ]

        if context:
            pros_cons["context_considerations"] = context

        pros_cons["framework"] = "Pros and Cons Analysis"
        return pros_cons

    async def _perform_root_cause_analysis(
        self, topic: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform root cause analysis to identify underlying issues."""
        root_cause: Dict[str, Any] = {
            "summary": f"Root Cause Analysis of: {topic}",
            "problem_statement": topic,
            "symptoms": [],
            "immediate_causes": [],
            "root_causes": [],
            "contributing_factors": [],
            "action_items": [],
        }

        # 5 Whys framework template
        root_cause["five_whys"] = [
            "Why did this happen?",
            "Why did that happen?",
            "Why did that happen?",
            "Why did that happen?",
            "Why did that happen?",
        ]

        # Categories for systematic analysis
        root_cause["categories"] = {
            "People": "Human factors, skills, training",
            "Process": "Procedures, workflows, methods",
            "Technology": "Tools, systems, equipment",
            "Environment": "External factors, conditions",
        }

        if context:
            root_cause["additional_context"] = context

        root_cause["framework"] = "Root Cause Analysis (5 Whys + Categorical)"
        return root_cause

    async def _perform_decision_making(
        self,
        topic: str,
        options: Optional[List[str]] = None,
        criteria: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Structured decision-making process."""
        decision: Dict[str, Any] = {
            "summary": f"Decision Framework for: {topic}",
            "decision_statement": topic,
            "options": options or [],
            "criteria": criteria
            or ["Impact", "Feasibility", "Cost", "Risk", "Alignment"],
            "evaluation": {},
            "trade_offs": [],
            "recommendation": "",
            "implementation_plan": [],
            "success_metrics": [],
        }

        # Decision matrix
        if options and criteria:
            for option in options:
                decision["evaluation"][option] = {}
                for criterion in decision["criteria"]:
                    decision["evaluation"][option][criterion] = {
                        "weight": 1.0,  # Can be adjusted
                        "score": 0,  # To be filled
                        "reasoning": f"Evaluate {option} on {criterion.lower()}",
                    }

        # Decision quality factors
        decision["quality_factors"] = {
            "completeness": "Are all viable options considered?",
            "information": "Is sufficient information available?",
            "bias_check": "Are there cognitive biases affecting this decision?",
            "stakeholders": "Are all stakeholders considered?",
            "reversibility": "How easily can this decision be reversed?",
        }

        if context:
            decision["constraints"] = context

        decision["framework"] = "Structured Decision Making"
        return decision

    async def _perform_brainstorming(
        self, topic: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate ideas and creative solutions."""
        brainstorm = {
            "summary": f"Brainstorming Session: {topic}",
            "objective": topic,
            "ideas": [],
            "categories": {},
            "promising_ideas": [],
            "next_steps": [],
        }

        # Brainstorming prompts
        brainstorm["prompts"] = [
            f"What are all possible ways to {topic}?",
            f"How might we improve {topic}?",
            f"What would happen if we completely changed {topic}?",
            f"What are unconventional approaches to {topic}?",
            f"How do others solve similar problems related to {topic}?",
        ]

        # Idea categories
        brainstorm["categories"] = {
            "Quick Wins": "Low effort, high impact solutions",
            "Long-term": "Strategic, transformational ideas",
            "Creative": "Unconventional, innovative approaches",
            "Practical": "Realistic, implementable solutions",
        }

        if context:
            brainstorm["constraints"] = context
            prompts_list = list(brainstorm["prompts"])
            prompts_list.append(
                f"Given the context '{context}', what other options exist?"
            )
            brainstorm["prompts"] = prompts_list

        brainstorm["framework"] = "Structured Brainstorming"
        return brainstorm

    async def _perform_breakdown(
        self, topic: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Break down complex problems or tasks into manageable parts."""
        breakdown = {
            "summary": f"Breakdown of: {topic}",
            "main_objective": topic,
            "components": [],
            "hierarchy": {},
            "dependencies": [],
            "critical_path": [],
            "resource_requirements": [],
        }

        # Work Breakdown Structure template
        breakdown["levels"] = {
            "Level 1": "Major phases or categories",
            "Level 2": "Key components or work packages",
            "Level 3": "Specific tasks or activities",
            "Level 4": "Detailed action items",
        }

        # Analysis dimensions
        breakdown["dimensions"] = {
            "functional": "Break down by function or capability",
            "temporal": "Break down by time phases",
            "organizational": "Break down by team or responsibility",
            "technical": "Break down by technical components",
        }

        if context:
            breakdown["scope"] = context

        breakdown["framework"] = "Work Breakdown Structure"
        return breakdown

    async def _perform_risk_assessment(
        self, topic: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assess risks and develop mitigation strategies."""
        risk_assessment = {
            "summary": f"Risk Assessment for: {topic}",
            "scope": topic,
            "risks": [],
            "risk_matrix": {},
            "mitigation_strategies": [],
            "contingency_plans": [],
            "monitoring_plan": [],
        }

        # Risk categories
        risk_assessment["categories"] = {
            "Technical": "Technology, system, or implementation risks",
            "Financial": "Budget, cost, or resource risks",
            "Schedule": "Timeline, delay, or deadline risks",
            "Operational": "Process, workflow, or execution risks",
            "Strategic": "Business, market, or competitive risks",
            "External": "Regulatory, environmental, or third-party risks",
        }

        # Risk assessment framework
        risk_assessment["assessment_criteria"] = {
            "probability": "Likelihood of occurrence (1 - 5 scale)",
            "impact": "Severity of consequences (1 - 5 scale)",
            "detectability": "Ease of early detection (1 - 5 scale)",
        }

        # Risk levels
        risk_assessment["risk_levels"] = {
            "Critical": "Immediate action required",
            "High": "Significant attention needed",
            "Medium": "Monitor and plan",
            "Low": "Accept or monitor",
        }

        if context:
            risk_assessment["context"] = context

        risk_assessment["framework"] = "Risk Assessment Matrix"
        return risk_assessment

    async def _save_to_memory(self, thinking_session: Dict[str, Any]) -> None:
        """Save thinking session to memory for later reference."""
        try:
            # This would integrate with the MemoryWriteTool
            memory_key = f"thinking_{thinking_session['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # noqa: E501

            # Save to local file in .ocode directory
            memory_dir = Path.cwd() / ".ocode" / "thinking"
            memory_dir.mkdir(parents=True, exist_ok=True)

            memory_file = memory_dir / f"{memory_key}.json"
            with open(memory_file, "w") as f:
                json.dump(thinking_session, f, indent=2)

        except Exception:  # nosec
            # Silently continue if memory save fails
            pass

    def _format_structured_output(self, thinking_session: Dict[str, Any]) -> str:
        """Format thinking session as structured text output."""
        output = f"🧠 Thinking Session: {thinking_session['type'].title()}\n"
        output += f"Topic: {thinking_session['topic']}\n"
        output += f"Time: {thinking_session['timestamp']}\n"
        output += "=" * 60 + "\n\n"

        results = thinking_session["results"]

        # Add framework info
        if "framework" in results:
            output += f"Framework: {results['framework']}\n\n"

        # Add summary
        if "summary" in results:
            output += f"Summary:\n{results['summary']}\n\n"

        # Format based on thinking type
        thinking_type = thinking_session["type"]

        if thinking_type == "analyze":
            output += self._format_analysis(results)
        elif thinking_type == "compare":
            output += self._format_comparison(results)
        elif thinking_type == "pros_cons":
            output += self._format_pros_cons(results)
        elif thinking_type == "root_cause":
            output += self._format_root_cause(results)
        elif thinking_type == "decision":
            output += self._format_decision(results)
        elif thinking_type == "brainstorm":
            output += self._format_brainstorm(results)
        elif thinking_type == "breakdown":
            output += self._format_breakdown(results)
        elif thinking_type == "risk_assessment":
            output += self._format_risk_assessment(results)

        return output

    def _format_analysis(self, results: Dict[str, Any]) -> str:
        """Format analysis results."""
        output = "Key Aspects to Analyze:\n"
        for aspect in results.get("key_aspects", []):
            output += f"• {aspect['aspect']}: {aspect['description']}\n"

        output += "\nObservations:\n"
        for obs in results.get("observations", []):
            output += f"• {obs}\n"

        return output + "\n"

    def _format_comparison(self, results: Dict[str, Any]) -> str:
        """Format comparison results."""
        output = "Options to Compare:\n"
        for option in results.get("options", []):
            output += f"• {option}\n"

        output += "\nEvaluation Criteria:\n"
        for criterion in results.get("criteria", []):
            output += f"• {criterion}\n"

        return output + "\n"

    def _format_pros_cons(self, results: Dict[str, Any]) -> str:
        """Format pros and cons results."""
        output = "Pros (Advantages):\n"
        for pro in results.get("pros", []):
            output += f"✓ {pro['factor']}: {pro['description']}\n"

        output += "\nCons (Disadvantages):\n"
        for con in results.get("cons", []):
            output += f"✗ {con['factor']}: {con['description']}\n"

        return output + "\n"

    def _format_root_cause(self, results: Dict[str, Any]) -> str:
        """Format root cause analysis results."""
        output = f"Problem: {results.get('problem_statement', '')}\n\n"

        output += "Categories to Investigate:\n"
        for category, description in results.get("categories", {}).items():
            output += f"• {category}: {description}\n"

        output += "\n5 Whys Framework:\n"
        for i, why in enumerate(results.get("five_whys", []), 1):
            output += f"{i}. {why['question']} {why['answer']}\n"

        return output + "\n"

    def _format_decision(self, results: Dict[str, Any]) -> str:
        """Format decision-making results."""
        output = f"Decision: {results.get('decision_statement', '')}\n\n"

        output += "Options:\n"
        for option in results.get("options", []):
            output += f"• {option}\n"

        output += "\nEvaluation Criteria:\n"
        for criterion in results.get("criteria", []):
            output += f"• {criterion}\n"

        output += "\nQuality Checks:\n"
        for factor, question in results.get("quality_factors", {}).items():
            output += f"• {factor.title()}: {question}\n"

        return output + "\n"

    def _format_brainstorm(self, results: Dict[str, Any]) -> str:
        """Format brainstorming results."""
        output = f"Objective: {results.get('objective', '')}\n\n"

        output += "Brainstorming Prompts:\n"
        for prompt in results.get("prompts", []):
            output += f"• {prompt}\n"

        output += "\nIdea Categories:\n"
        for category, description in results.get("categories", {}).items():
            output += f"• {category}: {description}\n"

        return output + "\n"

    def _format_breakdown(self, results: Dict[str, Any]) -> str:
        """Format breakdown results."""
        output = f"Main Objective: {results.get('main_objective', '')}\n\n"

        output += "Breakdown Levels:\n"
        for level, description in results.get("levels", {}).items():
            output += f"• {level}: {description}\n"

        output += "\nBreakdown Dimensions:\n"
        for dimension, description in results.get("dimensions", {}).items():
            output += f"• {dimension.title()}: {description}\n"

        return output + "\n"

    def _format_risk_assessment(self, results: Dict[str, Any]) -> str:
        """Format risk assessment results."""
        output = f"Scope: {results.get('scope', '')}\n\n"

        output += "Risk Categories:\n"
        for category, description in results.get("categories", {}).items():
            output += f"• {category}: {description}\n"

        output += "\nAssessment Criteria:\n"
        for criterion, description in results.get("assessment_criteria", {}).items():
            output += f"• {criterion.title()}: {description}\n"

        output += "\nRisk Levels:\n"
        for level, description in results.get("risk_levels", {}).items():
            output += f"• {level}: {description}\n"

        return output + "\n"

    def _format_markdown_output(self, thinking_session: Dict[str, Any]) -> str:
        """Format thinking session as markdown."""
        output = f"# 🧠 {thinking_session['type'].title()} Session\n\n"
        output += f"**Topic:** {thinking_session['topic']}\n\n"
        output += f"**Time:** {thinking_session['timestamp']}\n\n"

        results = thinking_session["results"]

        if "framework" in results:
            output += f"**Framework:** {results['framework']}\n\n"

        if "summary" in results:
            output += f"## Summary\n\n{results['summary']}\n\n"

        # Add structured content based on type
        # This would include markdown formatting for each thinking type
        output += "## Results\n\n"
        output += "```json\n"
        output += json.dumps(results, indent=2)
        output += "\n```\n"

        return output
