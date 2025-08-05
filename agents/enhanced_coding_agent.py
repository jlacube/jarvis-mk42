"""
Enhanced Coding Agent for Advanced Development Capabilities

This agent extends the BaseEnhancedAgent to provide sophisticated coding capabilities
including collaborative development workflows, multi-language programming support,
code review and analysis, and development lifecycle integration. It integrates with
the communication framework from Phase 2B.2 and language detection from Phase 2B.3.

The agent implements advanced development workflows and collaborative patterns to
provide high-quality code development with comprehensive analysis and review.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import json
import os
import ast
import subprocess

from agents.base_enhanced_agent import BaseEnhancedAgent, AgentCapabilities, AgentMetrics
from communication.protocols import AgentType
from tools.file_tools import get_file_tools
from tools.reasoning_tools import get_reasoning_tools
from tools.language_detection import detect_language_with_confidence, detect_multiple_languages
from models.models import get_openai_model, get_google_model
from utils.exceptions import JarvisValidationError, JarvisToolError
from utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

class DevelopmentWorkflow:
    """Represents a development workflow with stages and quality gates."""
    
    def __init__(self, name: str, stages: List[str], quality_gates: List[str]):
        self.name = name
        self.stages = stages
        self.quality_gates = quality_gates
        self.current_stage = 0
        self.completed_gates = []

class CodeAnalysisResult:
    """Results from code analysis operations."""
    
    def __init__(
        self,
        file_path: str,
        language: str,
        complexity_score: float,
        quality_score: float,
        issues: List[Dict[str, Any]],
        suggestions: List[str],
        metrics: Dict[str, Any]
    ):
        self.file_path = file_path
        self.language = language
        self.complexity_score = complexity_score
        self.quality_score = quality_score
        self.issues = issues
        self.suggestions = suggestions
        self.metrics = metrics
        self.timestamp = datetime.now()

class CollaborativeSession:
    """Manages collaborative coding sessions between agents."""
    
    def __init__(self, session_id: str, participants: List[str], focus_area: str):
        self.session_id = session_id
        self.participants = participants
        self.focus_area = focus_area
        self.start_time = datetime.now()
        self.contributions = []
        self.shared_context = {}

class EnhancedCodingAgent(BaseEnhancedAgent):
    """
    Enhanced Coding Agent with advanced development capabilities.
    
    Features:
    - Multi-language programming support (Python, JavaScript, TypeScript, Java, C#, Go, Rust, etc.)
    - Development workflow integration with quality gates
    - Collaborative coding capabilities with other agents
    - Advanced code analysis and review
    - Automated testing and quality assurance
    - Code refactoring and optimization
    - Documentation generation and maintenance
    - Version control integration
    - Continuous integration/deployment support
    """
    
    def __init__(
        self,
        agent_id: str = "enhanced_coding_agent",
        name: str = "Enhanced Coding Agent",
        model_config: Dict[str, Any] = None,
        communication_config: Dict[str, Any] = None
    ):
        # Import necessary enums for capabilities
        from communication.context_manager import ContextScope
        from communication.conflict_resolver import ResolutionStrategy
        from agents.base_enhanced_agent import CommunicationMode
        
        # Define capabilities
        capabilities = AgentCapabilities(
            primary_functions=[
                "code_development", "code_analysis", "code_review", "refactoring",
                "testing", "documentation", "collaborative_coding", "workflow_integration"
            ],
            supported_languages=["python", "javascript", "typescript", "java", "csharp", "go", "rust", "cpp", "html", "css"],
            communication_modes=[CommunicationMode.STANDALONE, CommunicationMode.COLLABORATIVE, CommunicationMode.RESPONDING],
            conflict_resolution_strategies=[ResolutionStrategy.MAJORITY_VOTE, ResolutionStrategy.EXPERT_OVERRIDE, ResolutionStrategy.MERGE_COMPATIBLE],
            context_scopes=[ContextScope.TASK, ContextScope.CONVERSATION, ContextScope.GLOBAL],
            max_concurrent_tasks=5,  # Higher for development tasks
            supports_streaming=True,
            requires_context=True
        )
        
        # Initialize base agent
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.CODING,
            agent_name=name,
            capabilities=capabilities,
            message_bus=None,  # Will be set up during initialization if needed
            context_manager=None,  # Will be set up during initialization if needed
            conflict_resolver=None  # Will be set up during initialization if needed
        )
        
        # Store configuration for later use
        self.model_config = model_config or {"provider": "openai", "model": "gpt-4", "temperature": 0.2}
        self.communication_config = communication_config
        
        # Initialize communication manager reference (set during base class initialization)
        self.communication_manager = None
        
        # Initialize coding-specific components
        self.supported_languages = [
            "python", "javascript", "typescript", "java", "csharp", "go", "rust", 
            "cpp", "c", "html", "css", "sql", "bash", "powershell", "yaml", "json"
        ]
        self.development_workflows = self._initialize_workflows()
        # Initialize coding tools
        self.coding_tools = get_file_tools() + get_reasoning_tools()
        self.tool_registry = {}  # Initialize tool registry for tracking tools
        self.analysis_history: List[CodeAnalysisResult] = []
        self.collaborative_sessions: Dict[str, CollaborativeSession] = {}
        self.active_projects = {}
        
        logger.info(f"Enhanced Coding Agent initialized with {len(self.development_workflows)} workflows and {len(self.coding_tools)} tools")
    
    def _initialize_workflows(self) -> Dict[str, DevelopmentWorkflow]:
        """Initialize standard development workflows."""
        workflows = {}
        
        # Agile Development Workflow
        workflows["agile"] = DevelopmentWorkflow(
            name="Agile Development",
            stages=["planning", "development", "testing", "review", "deployment"],
            quality_gates=["code_review", "unit_tests", "integration_tests", "security_scan"]
        )
        
        # TDD Workflow
        workflows["tdd"] = DevelopmentWorkflow(
            name="Test-Driven Development",
            stages=["test_design", "test_implementation", "code_implementation", "refactoring"],
            quality_gates=["test_coverage", "code_quality", "performance_check"]
        )
        
        # Code Review Workflow
        workflows["code_review"] = DevelopmentWorkflow(
            name="Code Review Process",
            stages=["static_analysis", "manual_review", "approval", "merge"],
            quality_gates=["syntax_check", "style_compliance", "security_check", "performance_review"]
        )
        
        # Refactoring Workflow
        workflows["refactoring"] = DevelopmentWorkflow(
            name="Code Refactoring",
            stages=["analysis", "planning", "implementation", "validation"],
            quality_gates=["functionality_preservation", "performance_improvement", "maintainability_check"]
        )
        
        return workflows
    
    async def initialize(self) -> bool:
        """Initialize the enhanced coding agent."""
        try:
            # Initialize base agent components
            if not await super().initialize():
                return False
            
            # Register coding tools
            for tool in self.coding_tools:
                self.tool_registry[tool.name] = tool
            
            # Test language detection integration
            test_code = "def hello_world():\n    print('Hello, World!')"
            language_info = detect_language_with_confidence(test_code)
            logger.info(f"Language detection integration verified: {language_info}")
            
            logger.info("Enhanced Coding Agent initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Enhanced Coding Agent initialization failed: {e}")
            return False
    
    async def analyze_code(
        self,
        code: str,
        file_path: str = "",
        language: str = "auto"
    ) -> CodeAnalysisResult:
        """
        Analyze code for quality, complexity, and potential issues.
        
        Args:
            code: The code to analyze
            file_path: Path to the code file (optional)
            language: Programming language (auto-detect if not specified)
            
        Returns:
            CodeAnalysisResult with analysis details
        """
        try:
            # Detect language if not specified
            if language == "auto":
                if file_path:
                    language = self._detect_language_from_extension(file_path)
                else:
                    # Use a simple heuristic or default to Python
                    language = self._detect_language_from_code(code)
            
            # Initialize analysis results
            issues = []
            suggestions = []
            metrics = {
                "lines_of_code": len(code.split('\n')),
                "characters": len(code),
                "estimated_reading_time": len(code.split()) / 200  # words per minute
            }
            
            # Language-specific analysis
            if language.lower() == "python":
                complexity_score, quality_score, py_issues, py_suggestions = await self._analyze_python_code(code)
                issues.extend(py_issues)
                suggestions.extend(py_suggestions)
            elif language.lower() in ["javascript", "typescript"]:
                complexity_score, quality_score, js_issues, js_suggestions = await self._analyze_javascript_code(code)
                issues.extend(js_issues)
                suggestions.extend(js_suggestions)
            else:
                # Generic analysis for other languages
                complexity_score, quality_score = await self._generic_code_analysis(code)
                suggestions.append(f"Consider using language-specific analysis for {language}")
            
            # Create analysis result
            result = CodeAnalysisResult(
                file_path=file_path,
                language=language,
                complexity_score=complexity_score,
                quality_score=quality_score,
                issues=issues,
                suggestions=suggestions,
                metrics=metrics
            )
            
            # Store in history
            self.analysis_history.append(result)
            
            logger.info(f"Code analysis completed for {language}: quality={quality_score:.2f}, complexity={complexity_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            raise JarvisToolError(f"Failed to analyze code: {str(e)}")
    
    async def _analyze_python_code(self, code: str) -> Tuple[float, float, List[Dict], List[str]]:
        """Analyze Python code specifically."""
        issues = []
        suggestions = []
        
        try:
            # Parse the code to check for syntax errors
            ast.parse(code)
            
            # Basic complexity analysis
            complexity_score = min(100, len(code.split('\n')) * 2)  # Simple metric
            
            # Quality checks
            quality_factors = []
            
            # Check for docstrings
            if '"""' in code or "'''" in code:
                quality_factors.append(10)
                suggestions.append("Good: Code includes docstrings")
            else:
                issues.append({"type": "documentation", "message": "Missing docstrings"})
                suggestions.append("Add docstrings to functions and classes")
            
            # Check for imports
            if 'import ' in code:
                quality_factors.append(5)
            
            # Check for functions
            if 'def ' in code:
                quality_factors.append(15)
                suggestions.append("Good: Code is organized into functions")
            
            # Check for classes
            if 'class ' in code:
                quality_factors.append(10)
                suggestions.append("Good: Object-oriented design detected")
            
            # Calculate quality score
            quality_score = min(100, sum(quality_factors))
            
            return complexity_score, quality_score, issues, suggestions
            
        except SyntaxError as e:
            issues.append({"type": "syntax", "message": f"Syntax error: {str(e)}"})
            return 100, 0, issues, ["Fix syntax errors before proceeding"]
    
    async def _analyze_javascript_code(self, code: str) -> Tuple[float, float, List[Dict], List[str]]:
        """Analyze JavaScript/TypeScript code specifically."""
        issues = []
        suggestions = []
        
        # Basic complexity analysis
        complexity_score = min(100, len(code.split('\n')) * 2)
        
        # Quality checks
        quality_factors = []
        
        # Check for modern JavaScript features
        if 'const ' in code or 'let ' in code:
            quality_factors.append(10)
            suggestions.append("Good: Using modern variable declarations")
        elif 'var ' in code:
            issues.append({"type": "style", "message": "Consider using const/let instead of var"})
        
        # Check for functions
        if 'function ' in code or '=>' in code:
            quality_factors.append(15)
            suggestions.append("Good: Code includes functions")
        
        # Check for comments
        if '//' in code or '/*' in code:
            quality_factors.append(5)
            suggestions.append("Good: Code includes comments")
        
        # Calculate quality score
        quality_score = min(100, sum(quality_factors))
        
        return complexity_score, quality_score, issues, suggestions
    
    async def _generic_code_analysis(self, code: str) -> Tuple[float, float]:
        """Generic code analysis for unsupported languages."""
        # Basic metrics
        lines = len(code.split('\n'))
        complexity_score = min(100, lines * 2)
        
        # Simple quality heuristics
        quality_factors = []
        if lines > 10:
            quality_factors.append(10)
        if any(char in code for char in ['{', '}', '(', ')']):
            quality_factors.append(10)
        
        quality_score = min(100, sum(quality_factors))
        
        return complexity_score, quality_score
    
    def _detect_language_from_extension(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'bash',
            '.ps1': 'powershell',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json'
        }
        
        _, ext = os.path.splitext(file_path.lower())
        return extension_map.get(ext, 'unknown')
    
    def _detect_language_from_code(self, code: str) -> str:
        """Detect programming language from code content using heuristics."""
        code_lower = code.lower()
        
        # Python indicators
        if any(keyword in code_lower for keyword in ['def ', 'import ', 'from ', 'print(', 'if __name__']):
            return 'python'
        
        # JavaScript indicators
        if any(keyword in code_lower for keyword in ['function ', 'var ', 'let ', 'const ', 'console.log']):
            return 'javascript'
        
        # Java indicators
        if any(keyword in code_lower for keyword in ['public class', 'public static void main', 'system.out.println']):
            return 'java'
        
        # Default to Python if unsure
        return 'python'
    
    async def start_collaborative_session(
        self,
        participants: List[str],
        focus_area: str,
        project_context: Dict[str, Any] = None
    ) -> str:
        """
        Start a collaborative coding session with other agents.
        
        Args:
            participants: List of agent IDs to include
            focus_area: What to focus on (e.g., "refactoring", "testing", "feature_development")
            project_context: Additional context about the project
            
        Returns:
            Session ID for the collaborative session
        """
        try:
            session_id = f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.collaborative_sessions)}"
            
            session = CollaborativeSession(
                session_id=session_id,
                participants=participants,
                focus_area=focus_area
            )
            
            if project_context:
                session.shared_context.update(project_context)
            
            self.collaborative_sessions[session_id] = session
            
            # Send collaboration invitation messages if communication manager is available
            if self.communication_manager:
                for participant in participants:
                    await self.communication_manager.send_message({
                        "type": "collaboration_invitation",
                        "session_id": session_id,
                        "focus_area": focus_area,
                        "context": project_context,
                        "from": self.agent_id,
                        "to": participant
                    })
            
            logger.info(f"Started collaborative session {session_id} with {len(participants)} participants")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start collaborative session: {e}")
            raise JarvisToolError(f"Failed to start collaborative session: {str(e)}")
    
    async def review_code(
        self,
        code: str,
        review_criteria: List[str] = None,
        file_path: str = ""
    ) -> Dict[str, Any]:
        """
        Perform comprehensive code review.
        
        Args:
            code: Code to review
            review_criteria: Specific aspects to focus on
            file_path: Path to the file being reviewed
            
        Returns:
            Comprehensive review results
        """
        try:
            # Default review criteria
            if review_criteria is None:
                review_criteria = [
                    "functionality", "readability", "maintainability", 
                    "performance", "security", "best_practices"
                ]
            
            # Perform code analysis first
            analysis = await self.analyze_code(code, file_path)
            
            # Initialize review results
            review_results = {
                "overall_score": 0,
                "criteria_scores": {},
                "recommendations": [],
                "critical_issues": [],
                "approved": False,
                "analysis": analysis.__dict__
            }
            
            # Evaluate each criterion
            total_score = 0
            for criterion in review_criteria:
                score = await self._evaluate_criterion(code, criterion, analysis)
                review_results["criteria_scores"][criterion] = score
                total_score += score
            
            # Calculate overall score
            review_results["overall_score"] = total_score / len(review_criteria) if review_criteria else 0
            
            # Determine approval status (threshold: 70%)
            review_results["approved"] = review_results["overall_score"] >= 70
            
            # Add general recommendations
            if review_results["overall_score"] < 70:
                review_results["recommendations"].append("Consider addressing the identified issues before merging")
            
            if not review_results["approved"]:
                review_results["critical_issues"].append("Code review score below approval threshold")
            
            logger.info(f"Code review completed: score={review_results['overall_score']:.1f}%, approved={review_results['approved']}")
            return review_results
            
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            raise JarvisToolError(f"Failed to review code: {str(e)}")
    
    async def _evaluate_criterion(self, code: str, criterion: str, analysis: CodeAnalysisResult) -> float:
        """Evaluate code against a specific criterion."""
        score = 50  # Base score
        
        if criterion == "functionality":
            # Check if code appears functional based on analysis
            if len(analysis.issues) == 0:
                score += 30
            else:
                score -= len(analysis.issues) * 10
        
        elif criterion == "readability":
            # Assess readability based on metrics
            lines = analysis.metrics.get("lines_of_code", 0)
            if lines > 0 and lines < 50:  # Not too long
                score += 20
            if '"' in code or "'" in code:  # Has string literals (likely readable)
                score += 10
        
        elif criterion == "maintainability":
            # Check for maintainability indicators
            if analysis.language == "python" and ('def ' in code or 'class ' in code):
                score += 25
            if len(analysis.suggestions) > 0:
                score += 15
        
        elif criterion == "performance":
            # Basic performance assessment
            if analysis.complexity_score < 50:
                score += 30
            elif analysis.complexity_score > 80:
                score -= 20
        
        elif criterion == "security":
            # Basic security checks (very simplified)
            if "eval(" not in code and "exec(" not in code:
                score += 20
            if "password" not in code.lower() or "secret" not in code.lower():
                score += 10
        
        elif criterion == "best_practices":
            # Check for best practices
            score += min(30, analysis.quality_score * 0.3)
        
        return max(0, min(100, score))
    
    async def get_coding_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent coding analysis history."""
        try:
            recent_history = self.analysis_history[-limit:] if limit > 0 else self.analysis_history
            return [
                {
                    "file_path": result.file_path,
                    "language": result.language,
                    "quality_score": result.quality_score,
                    "complexity_score": result.complexity_score,
                    "issues_count": len(result.issues),
                    "timestamp": result.timestamp.isoformat()
                }
                for result in recent_history
            ]
        except Exception as e:
            logger.error(f"Failed to get coding history: {e}")
            return []
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status including coding-specific information."""
        base_status = self.get_status()
        
        # Add coding-specific status
        coding_status = {
            "development_workflows_available": len(self.development_workflows),
            "coding_tools_available": len(self.coding_tools),
            "supported_languages": len(self.supported_languages),
            "total_analysis_performed": len(self.analysis_history),
            "active_collaborative_sessions": len(self.collaborative_sessions),
            "supported_languages_list": self.supported_languages,
            "recent_analysis_quality": self._calculate_recent_quality(),
            "workflow_names": list(self.development_workflows.keys())
        }
        
        base_status.update(coding_status)
        return base_status
    
    def _calculate_recent_quality(self) -> float:
        """Calculate average quality score from recent analyses."""
        if not self.analysis_history:
            return 0.0
        
        recent_analyses = self.analysis_history[-10:]  # Last 10 analyses
        total_quality = sum(analysis.quality_score for analysis in recent_analyses)
        return total_quality / len(recent_analyses)
    
    async def handle_collaboration_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle messages from other agents in collaborative scenarios."""
        try:
            message_type = message.get("type", "")
            content = message.get("content", "")
            metadata = message.get("metadata", {})
            
            if message_type == "code_review_request":
                # Handle code review requests from other agents
                code = metadata.get("code", "")
                criteria = metadata.get("criteria", [])
                
                if code:
                    review_result = await self.review_code(code, criteria)
                    
                    return {
                        "message_type": "code_review_response",
                        "content": f"Code review completed with score: {review_result['overall_score']:.1f}%",
                        "metadata": {
                            "review_result": review_result,
                            "original_request_id": metadata.get("request_id")
                        }
                    }
            
            elif message_type == "code_analysis_request":
                # Handle code analysis requests
                code = metadata.get("code", "")
                language = metadata.get("language", "auto")
                
                if code:
                    analysis_result = await self.analyze_code(code, language=language)
                    
                    return {
                        "message_type": "code_analysis_response",
                        "content": f"Code analysis completed: {analysis_result.language} code with quality score {analysis_result.quality_score:.1f}",
                        "metadata": {
                            "analysis_result": analysis_result.__dict__,
                            "original_request_id": metadata.get("request_id")
                        }
                    }
            
            elif message_type == "collaboration_invitation":
                # Handle collaboration invitations
                session_id = metadata.get("session_id", "")
                focus_area = metadata.get("focus_area", "")
                
                return {
                    "message_type": "collaboration_response",
                    "content": f"Accepted collaboration invitation for {focus_area}",
                    "metadata": {
                        "session_id": session_id,
                        "accepted": True,
                        "capabilities": self.supported_languages
                    }
                }
        
        except Exception as e:
            logger.error(f"Failed to handle collaboration message: {e}")
            return {
                "message_type": "error_response", 
                "content": f"Failed to process request: {str(e)}",
                "metadata": {"error": str(e)}
            }
        
        return None
    
    # Abstract method implementations required by BaseEnhancedAgent
    async def _initialize_agent_specific(self) -> None:
        """Initialize coding agent specific components."""
        # Initialize any coding-specific resources here
        # For now, just log initialization
        logger.info(f"Enhanced Coding Agent {self.agent_id} initialized successfully")
    
    async def _cleanup_agent_specific(self) -> None:
        """Cleanup coding agent specific resources."""
        # Cleanup any coding-specific resources here
        # For now, just log cleanup
        logger.info(f"Enhanced Coding Agent {self.agent_id} cleaned up successfully")
    
    async def _process_request_internal(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
        language_context: Any,
        task_id: str
    ) -> Dict[str, Any]:
        """Process coding request internally using appropriate workflow."""
        try:
            # Determine if this is a code analysis, review, or development request
            request_lower = request.lower()
            
            if "analyze" in request_lower and "code" in request_lower:
                # Code analysis request
                code = context.get("code", "") if context else ""
                if code:
                    analysis_result = await self.analyze_code(
                        code=code,
                        file_path=context.get("file_path", "") if context else "",
                        language=getattr(language_context, 'language', 'auto') if language_context else 'auto'
                    )
                    
                    return {
                        'success': True,
                        'task_id': task_id,
                        'result': analysis_result.__dict__,
                        'agent_id': self.agent_id,
                        'timestamp': datetime.now().isoformat()
                    }
            
            elif "review" in request_lower and "code" in request_lower:
                # Code review request
                code = context.get("code", "") if context else ""
                if code:
                    review_result = await self.review_code(
                        code=code,
                        review_criteria=context.get("criteria", []) if context else [],
                        file_path=context.get("file_path", "") if context else ""
                    )
                    
                    return {
                        'success': True,
                        'task_id': task_id,
                        'result': review_result,
                        'agent_id': self.agent_id,
                        'timestamp': datetime.now().isoformat()
                    }
            
            else:
                # General coding assistance
                return {
                    'success': True,
                    'task_id': task_id,
                    'result': {
                        'message': 'Enhanced Coding Agent ready to assist with development tasks',
                        'capabilities': self.supported_languages,
                        'workflows': list(self.development_workflows.keys())
                    },
                    'agent_id': self.agent_id,
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error in _process_request_internal: {e}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat()
            }

async def create_enhanced_coding_agent(
    agent_id: str = "enhanced_coding_agent",
    model_config: Dict[str, Any] = None,
    communication_config: Dict[str, Any] = None
) -> EnhancedCodingAgent:
    """
    Factory function to create and initialize an Enhanced Coding Agent.
    
    Args:
        agent_id: Unique identifier for the agent
        model_config: Model configuration settings
        communication_config: Communication framework configuration
        
    Returns:
        Initialized EnhancedCodingAgent instance
    """
    agent = EnhancedCodingAgent(
        agent_id=agent_id,
        model_config=model_config,
        communication_config=communication_config
    )
    
    await agent.initialize()
    return agent
