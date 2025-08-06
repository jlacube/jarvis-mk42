# agents/supervisor_agent.py
"""
Supervisor Agent for Multi-Agent Orchestration
==============================================

This module implements the core supervisor agent that coordinates multiple specialized 
agents to handle complex, multi-step tasks. The supervisor agent:

1. Analyzes incoming user requests and determines complexity
2. Decomposes complex tasks into agent-specific subtasks  
3. Selects and invokes appropriate specialized agents
4. Coordinates workflows between multiple agents
5. Aggregates results into coherent, unified responses
6. Handles errors and implements fallback strategies

The supervisor agent uses LangGraph's orchestrator-worker pattern with dynamic
agent selection and state management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass
from enum import Enum

import chainlit as cl
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver

# Import existing agents and models
from models.models import get_google_model, get_openai_model
from config.settings import get_settings
from utils.logging_config import get_logger
from utils.exceptions import AgentError, ValidationError

logger = get_logger(__name__)


class TaskComplexity(Enum):
    """Enumeration of task complexity levels for agent selection."""
    SIMPLE = "simple"      # Single agent, single step
    MODERATE = "moderate"  # Single agent, multiple steps
    COMPLEX = "complex"    # Multiple agents, coordinated workflow
    ADVANCED = "advanced"  # Multiple agents, iterative refinement


class AgentType(Enum):
    """Enumeration of available specialized agents."""
    REASONING = "reasoning"
    RESEARCH = "research" 
    CODING = "coding"
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    MULTIMODAL = "multimodal"


@dataclass
class AgentCapability:
    """Definition of an agent's capabilities and characteristics."""
    agent_type: AgentType
    name: str
    description: str
    strengths: List[str]
    tools: List[str]
    keywords: List[str]  # Keywords that suggest this agent should be used
    

class TaskAnalysis(BaseModel):
    """Structured analysis of a user task for agent orchestration."""
    complexity: TaskComplexity = Field(description="Overall complexity level of the task")
    primary_domain: str = Field(description="Main domain or subject area of the task")
    required_agents: List[AgentType] = Field(description="List of agents needed to complete the task")
    subtasks: List[str] = Field(description="Breakdown of the task into specific subtasks")
    dependencies: Dict[str, List[str]] = Field(
        description="Dependencies between subtasks (subtask -> list of prerequisite subtasks)"
    )
    estimated_steps: int = Field(description="Estimated number of steps to complete")
    confidence: float = Field(description="Confidence in this analysis (0.0 to 1.0)")


class WorkflowState(BaseModel):
    """State management for multi-agent workflows."""
    user_request: str
    user_name: str
    session_context: Dict[str, Any]
    task_analysis: Optional[TaskAnalysis] = None
    active_agents: List[AgentType] = Field(default_factory=list)
    completed_subtasks: List[str] = Field(default_factory=list)
    agent_results: Dict[str, Any] = Field(default_factory=dict)
    workflow_status: Literal["planning", "executing", "aggregating", "complete", "error"] = "planning"
    error_messages: List[str] = Field(default_factory=list)
    final_response: Optional[str] = None


class SupervisorAgent:
    """
    Main supervisor agent that orchestrates multi-agent workflows.
    
    This class implements the core orchestration logic using LangGraph's
    orchestrator-worker pattern. It provides:
    
    - Intelligent task analysis and decomposition
    - Dynamic agent selection based on task requirements
    - Workflow state management and coordination
    - Error handling and recovery mechanisms
    - Result aggregation and response synthesis
    """
    
    def __init__(self):
        """Initialize the supervisor agent with agent capabilities and models."""
        self.settings = get_settings()
        self.model = get_google_model()
        
        # Define agent capabilities
        self.agent_capabilities = {
            AgentType.REASONING: AgentCapability(
                agent_type=AgentType.REASONING,
                name="Reasoning Agent",
                description="Advanced logical reasoning, problem decomposition, and strategic analysis",
                strengths=[
                    "Complex problem solving",
                    "Step-by-step analysis", 
                    "Logical inference",
                    "Strategic planning",
                    "Decision making"
                ],
                tools=["sequential_thinking_tool", "reasoning_model_tool"],
                keywords=[
                    "analyze", "reason", "think", "logic", "problem", "solve", 
                    "strategy", "decision", "plan", "evaluate", "assess"
                ]
            ),
            AgentType.RESEARCH: AgentCapability(
                agent_type=AgentType.RESEARCH,
                name="Research Agent", 
                description="Comprehensive information gathering, fact-checking, and knowledge synthesis",
                strengths=[
                    "Internet research",
                    "Fact verification", 
                    "Information synthesis",
                    "Current events",
                    "Academic research"
                ],
                tools=["advanced_research_tool", "google_search_tool", "webpage_research_tool"],
                keywords=[
                    "research", "search", "find", "information", "facts", "current",
                    "news", "academic", "study", "investigate", "explore"
                ]
            ),
            AgentType.CODING: AgentCapability(
                agent_type=AgentType.CODING,
                name="Coding Agent",
                description="Software development, debugging, code review, and technical implementation",
                strengths=[
                    "Code generation",
                    "Debugging",
                    "Code review",
                    "Architecture design", 
                    "Technical documentation"
                ],
                tools=["coding_tool"],
                keywords=[
                    "code", "program", "script", "develop", "debug", "implement",
                    "software", "function", "class", "algorithm", "technical"
                ]
            ),
            AgentType.DOCUMENT_INTELLIGENCE: AgentCapability(
                agent_type=AgentType.DOCUMENT_INTELLIGENCE,
                name="Document Intelligence Agent",
                description="Document analysis, processing, and content extraction from various formats",
                strengths=[
                    "Document analysis",
                    "Content extraction",
                    "Format conversion",
                    "Text processing",
                    "Information extraction"
                ],
                tools=["analyze_document_tool", "compare_documents_tool"],
                keywords=[
                    "document", "pdf", "file", "extract", "analyze", "content",
                    "text", "format", "convert", "process", "read"
                ]
            ),
            AgentType.MULTIMODAL: AgentCapability(
                agent_type=AgentType.MULTIMODAL,
                name="Multimodal Agent",
                description="Image, video, and audio processing with cross-modal understanding",
                strengths=[
                    "Image analysis",
                    "Video processing",
                    "Audio generation",
                    "Visual content creation",
                    "Cross-modal reasoning"
                ],
                tools=["image_vision_tool", "images_search_tool", "imager_tool", "video_tool"],
                keywords=[
                    "image", "video", "audio", "visual", "generate", "create",
                    "picture", "photo", "media", "multimedia", "vision"
                ]
            )
        }
        
        # Create task analyzer (use regular model instead of structured output)
        # self.task_analyzer = self.model.with_structured_output(TaskAnalysis)
        self.task_analyzer = self.model
        
        logger.info("Supervisor agent initialized with %d specialized agents", len(self.agent_capabilities))
    
    def analyze_task(self, user_request: str, context: Dict[str, Any]) -> TaskAnalysis:
        """
        Analyze a user request to determine complexity and required agents.
        
        Args:
            user_request: The user's request or question
            context: Additional context including user info, session data, etc.
            
        Returns:
            TaskAnalysis: Structured analysis of the task requirements
        """
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze the following user request to determine how it should be handled by our multi-agent system.
            
            User Request: "{user_request}"
            
            Context:
            - User: {context.get('user_name', 'Unknown')}
            - Session: {context.get('session_id', 'Unknown')}
            
            Available Agents and Their Capabilities:
            {self._format_agent_capabilities()}
            
            Provide a structured analysis that includes:
            1. Task complexity level (simple/moderate/complex/advanced)
            2. Primary domain or subject area
            3. Which agents are needed and why
            4. Breakdown into specific subtasks
            5. Dependencies between subtasks
            6. Estimated number of steps
            7. Confidence in this analysis
            
            Guidelines:
            - SIMPLE: Single agent, direct response (e.g., basic questions, simple calculations)
            - MODERATE: Single agent, multi-step process (e.g., research with analysis)  
            - COMPLEX: Multiple agents, coordinated workflow (e.g., research + coding + analysis)
            - ADVANCED: Multiple agents, iterative refinement (e.g., complex problem solving with validation)
            """
            
            result = self.task_analyzer.invoke([
                SystemMessage(content="You are an expert task analyst for a multi-agent system. Respond with valid JSON only."),
                HumanMessage(content=f"""
                Analyze the following user request for task complexity and agent requirements:
                
                User Request: {user_request}
                
                Context: {context}
                
                Please provide your analysis in the following JSON format:
                {{
                    "complexity": "simple|moderate|complex|advanced",
                    "primary_domain": "general|research|coding|analysis|multimodal|reasoning",
                    "required_agents": ["reasoning|research|coding|multimodal"],
                    "subtasks": ["list of specific subtasks"],
                    "dependencies": {{}},
                    "estimated_steps": 1,
                    "confidence": 0.8
                }}
                
                Guidelines:
                - SIMPLE: Single agent, direct response (e.g., basic questions, simple calculations)
                - MODERATE: Single agent, multi-step process (e.g., research with analysis)  
                - COMPLEX: Multiple agents, coordinated workflow (e.g., research + coding + analysis)
                - ADVANCED: Multiple agents, iterative refinement (e.g., complex problem solving with validation)
                
                Respond with ONLY the JSON, no other text.
                """)
            ])
            
            # Parse the response
            import json
            response_text = result.content if hasattr(result, 'content') else str(result)
            
            try:
                parsed_data = json.loads(response_text.strip())
                
                # Convert to TaskAnalysis object
                analysis = TaskAnalysis(
                    complexity=TaskComplexity(parsed_data.get("complexity", "simple")),
                    primary_domain=parsed_data.get("primary_domain", "general"),
                    required_agents=[AgentType(agent) for agent in parsed_data.get("required_agents", ["reasoning"])],
                    subtasks=parsed_data.get("subtasks", [user_request]),
                    dependencies=parsed_data.get("dependencies", {}),
                    estimated_steps=parsed_data.get("estimated_steps", 1),
                    confidence=parsed_data.get("confidence", 0.5)
                )
                
            except (json.JSONDecodeError, KeyError, ValueError) as parse_error:
                logger.warning("Failed to parse LLM response, using fallback analysis: %s", parse_error)
                # Fallback analysis based on keywords
                analysis = self._fallback_analysis(user_request, context)
            
            logger.info(
                "Task analysis complete: complexity=%s, agents=%s, confidence=%.2f",
                analysis.complexity.value,
                [agent.value for agent in analysis.required_agents],
                analysis.confidence
            )
            
            return analysis
            
        except Exception as e:
            logger.error("Error in task analysis: %s", str(e))
            # Fallback to simple analysis
            return TaskAnalysis(
                complexity=TaskComplexity.SIMPLE,
                primary_domain="general",
                required_agents=[AgentType.REASONING],
                subtasks=[user_request],
                dependencies={},
                estimated_steps=1,
                confidence=0.5
            )
    
    def _fallback_analysis(self, user_request: str, context: Dict[str, Any]) -> TaskAnalysis:
        """Provide fallback analysis based on keyword matching."""
        request_lower = user_request.lower()
        
        # Determine complexity based on keywords
        if any(word in request_lower for word in ['research', 'analyze', 'create', 'build', 'develop']):
            if any(word in request_lower for word in ['and', 'then', 'also', 'visualize', 'plot', 'code']):
                complexity = TaskComplexity.COMPLEX
                required_agents = [AgentType.REASONING, AgentType.RESEARCH, AgentType.CODING]
            else:
                complexity = TaskComplexity.MODERATE
                required_agents = [AgentType.REASONING, AgentType.RESEARCH]
        else:
            complexity = TaskComplexity.SIMPLE
            required_agents = [AgentType.REASONING]
        
        return TaskAnalysis(
            complexity=complexity,
            primary_domain="general",
            required_agents=required_agents,
            subtasks=[user_request],
            dependencies={},
            estimated_steps=len(required_agents),
            confidence=0.5
        )
    
    def _format_agent_capabilities(self) -> str:
        """Format agent capabilities for the analysis prompt."""
        formatted = []
        for agent_type, capability in self.agent_capabilities.items():
            formatted.append(f"""
            {capability.name} ({agent_type.value}):
            - Description: {capability.description}
            - Strengths: {', '.join(capability.strengths)}
            - Key Tools: {', '.join(capability.tools)}
            - Keywords: {', '.join(capability.keywords)}
            """)
        return "\n".join(formatted)
    
    def select_agents(self, task_analysis: TaskAnalysis) -> List[AgentType]:
        """
        Select appropriate agents based on task analysis.
        
        Args:
            task_analysis: The structured task analysis
            
        Returns:
            List of agent types to use for this task
        """
        selected_agents = []
        
        # Use the agents identified in the analysis
        selected_agents.extend(task_analysis.required_agents)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_agents = []
        for agent in selected_agents:
            if agent not in seen:
                seen.add(agent)
                unique_agents.append(agent)
        
        logger.info("Selected agents: %s", [agent.value for agent in unique_agents])
        return unique_agents
    
    async def create_workflow(self, initial_state: WorkflowState) -> Any:
        """
        Create a LangGraph workflow for the given task.
        
        Args:
            initial_state: The initial workflow state
            
        Returns:
            Compiled LangGraph workflow
        """
        try:
            # Create state schema
            from typing_extensions import TypedDict
            
            class GraphState(TypedDict):
                user_request: str
                user_name: str
                session_context: dict
                task_analysis: dict
                active_agents: list
                completed_subtasks: list
                agent_results: dict
                workflow_status: str
                error_messages: list
                final_response: str
            
            # Create workflow graph
            workflow = StateGraph(GraphState)
            
            # Add orchestrator node
            workflow.add_node("orchestrator", self._orchestrator_node)
            
            # Add agent nodes (will be created dynamically)
            workflow.add_node("reasoning_agent", self._reasoning_agent_node)
            workflow.add_node("research_agent", self._research_agent_node)
            workflow.add_node("coding_agent", self._coding_agent_node)
            workflow.add_node("document_agent", self._document_agent_node)
            workflow.add_node("multimodal_agent", self._multimodal_agent_node)
            
            # Add synthesizer node
            workflow.add_node("synthesizer", self._synthesizer_node)
            
            # Add edges
            workflow.add_edge(START, "orchestrator")
            workflow.add_conditional_edges(
                "orchestrator",
                self._route_to_agents,
                {
                    "reasoning_agent": "reasoning_agent",
                    "research_agent": "research_agent", 
                    "coding_agent": "coding_agent",
                    "document_agent": "document_agent",
                    "multimodal_agent": "multimodal_agent",
                    "synthesizer": "synthesizer",
                    END: END
                }
            )
            
            # Agent nodes route to synthesizer or back to orchestrator
            for agent_node in ["reasoning_agent", "research_agent", "coding_agent", "document_agent", "multimodal_agent"]:
                workflow.add_conditional_edges(
                    agent_node,
                    self._check_workflow_complete,
                    {
                        "continue": "orchestrator",
                        "synthesize": "synthesizer"
                    }
                )
            
            workflow.add_edge("synthesizer", END)
            
            # Compile with memory
            compiled_workflow = workflow.compile(checkpointer=MemorySaver())
            
            logger.info("Workflow created successfully")
            return compiled_workflow
            
        except Exception as e:
            logger.error("Error creating workflow: %s", str(e))
            raise AgentError(f"Failed to create workflow: {str(e)}")
    
    def _orchestrator_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrator node that manages workflow coordination."""
        try:
            logger.info("Orchestrator node processing state")
            
            # Track orchestrator calls to prevent infinite loops
            orchestrator_calls = state.get('orchestrator_calls', 0) + 1
            if orchestrator_calls > 10:  # Prevent infinite loops
                logger.warning("Orchestrator called too many times, moving to synthesis")
                return {
                    **state,
                    "workflow_status": "synthesis",
                    "error_messages": state.get("error_messages", []) + ["Workflow exceeded maximum iterations"]
                }
            
            # Convert state to WorkflowState if needed
            if isinstance(state.get('task_analysis'), dict):
                # State came from graph, convert back to objects
                workflow_state = WorkflowState(**state)
            else:
                workflow_state = WorkflowState(
                    user_request=state['user_request'],
                    user_name=state['user_name'],
                    session_context=state['session_context'],
                    task_analysis=state.get('task_analysis'),
                    active_agents=state.get('active_agents', []),
                    completed_subtasks=state.get('completed_subtasks', []),
                    agent_results=state.get('agent_results', {}),
                    workflow_status=state.get('workflow_status', 'planning'),
                    error_messages=state.get('error_messages', []),
                    final_response=state.get('final_response')
                )
            
            # Perform task analysis if not done
            if workflow_state.task_analysis is None:
                workflow_state.task_analysis = self.analyze_task(
                    workflow_state.user_request,
                    workflow_state.session_context
                )
                workflow_state.workflow_status = "executing"
            
            # Update active agents only if not already set
            if not workflow_state.active_agents:
                workflow_state.active_agents = self.select_agents(workflow_state.task_analysis)
            
            # Convert back to dict for graph state
            return {
                "user_request": workflow_state.user_request,
                "user_name": workflow_state.user_name,
                "session_context": workflow_state.session_context,
                "task_analysis": workflow_state.task_analysis.dict() if workflow_state.task_analysis else None,
                "active_agents": [agent.value for agent in workflow_state.active_agents],
                "completed_subtasks": workflow_state.completed_subtasks,
                "agent_results": workflow_state.agent_results,
                "workflow_status": workflow_state.workflow_status,
                "error_messages": workflow_state.error_messages,
                "final_response": workflow_state.final_response or "",
                "orchestrator_calls": orchestrator_calls
            }
            
        except Exception as e:
            logger.error("Error in orchestrator node: %s", str(e))
            return {
                **state,
                "workflow_status": "error",
                "error_messages": state.get("error_messages", []) + [str(e)]
            }
    
    def _route_to_agents(self, state: Dict[str, Any]) -> str:
        """Route to the next agent or synthesizer based on workflow state."""
        try:
            active_agents = state.get('active_agents', [])
            completed_subtasks = state.get('completed_subtasks', [])
            agent_results = state.get('agent_results', {})
            orchestrator_calls = state.get('orchestrator_calls', 0)
            
            # If we've called orchestrator too many times, go to synthesizer
            if orchestrator_calls > 10:
                logger.warning("Too many orchestrator calls, going to synthesizer")
                return "synthesizer"
            
            # If no active agents, go to synthesizer
            if not active_agents:
                logger.info("No active agents, routing to synthesizer")
                return "synthesizer"
            
            # If we have results and errors, go to synthesizer
            error_messages = state.get('error_messages', [])
            if len(agent_results) > 0 and len(error_messages) > 0:
                logger.info("Have results and errors, routing to synthesizer")
                return "synthesizer"
            
            # Route to first active agent
            first_agent = active_agents[0]
            logger.info(f"Routing to agent: {first_agent}")
            
            agent_routing = {
                "reasoning": "reasoning_agent",
                "research": "research_agent",
                "coding": "coding_agent", 
                "document_intelligence": "document_agent",
                "multimodal": "multimodal_agent"
            }
            
            return agent_routing.get(first_agent, "synthesizer")
            
        except Exception as e:
            logger.error("Error in routing: %s", str(e))
            return "synthesizer"
    
    def _check_workflow_complete(self, state: Dict[str, Any]) -> str:
        """Check if workflow is complete or needs more agent work."""
        try:
            active_agents = state.get('active_agents', [])
            workflow_status = state.get('workflow_status', 'planning')
            agent_results = state.get('agent_results', {})
            error_messages = state.get('error_messages', [])
            
            # If there's a critical error, synthesize
            if workflow_status == "error":
                return "synthesize"
            
            # If we have too many errors, synthesize 
            if len(error_messages) >= 3:
                return "synthesize"
            
            # If no more active agents or only one left, synthesize
            if len(active_agents) <= 1:
                return "synthesize"
            
            # If we have some results and some agents failed, synthesize what we have
            if len(agent_results) > 0 and len(error_messages) > 0:
                return "synthesize"
            
            # Continue with remaining agents
            return "continue"
                
        except Exception as e:
            logger.error("Error checking workflow completion: %s", str(e))
            return "synthesize"
    
    # Agent node implementations with real agent integration
    async def _reasoning_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Reasoning agent node implementation with real agent integration."""
        logger.info("Reasoning agent node called")
        
        try:
            # Import the enhanced reasoning agent
            from agents.enhanced_reasoning_agent import EnhancedReasoningAgent
            from communication.protocols import AgentType
            from communication.context_manager import ContextScope
            from communication.conflict_resolver import ResolutionStrategy
            from agents.base_enhanced_agent import AgentCapabilities, CommunicationMode
            
            # Create agent capabilities
            capabilities = AgentCapabilities(
                primary_functions=["logical_reasoning", "problem_solving", "analysis"],
                supported_languages=["en", "fr", "es", "de"],
                communication_modes=[CommunicationMode.COLLABORATIVE],
                conflict_resolution_strategies=[ResolutionStrategy.CONSENSUS_BUILDING],
                context_scopes=[ContextScope.TASK, ContextScope.WORKFLOW]
            )
            
            # Create reasoning agent instance
            reasoning_agent = EnhancedReasoningAgent(
                agent_id=f"reasoning_{datetime.now().timestamp()}"
            )
            
            # Initialize the agent
            await reasoning_agent.initialize()
            
            # Process the request
            user_request = state.get('user_request', '')
            session_context = state.get('session_context', {})
            
            result = await reasoning_agent.process_request(
                request=user_request,
                context=session_context
            )
            
            # Extract the response
            agent_response = result.get('response', 'Reasoning completed successfully.')
            
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "reasoning": agent_response
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "reasoning"]
            }
            
        except Exception as e:
            logger.error(f"Error in reasoning agent node: {e}")
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "reasoning": f"I encountered an error during reasoning: {str(e)}"
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "reasoning"],
                "error_messages": state.get("error_messages", []) + [f"Reasoning agent error: {str(e)}"]
            }
    
    async def _research_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Research agent node implementation with real agent integration."""
        logger.info("Research agent node called")
        
        try:
            # Import the enhanced research agent
            from agents.enhanced_research_agent import EnhancedResearchAgent
            from communication.protocols import AgentType
            from communication.context_manager import ContextScope
            from communication.conflict_resolver import ResolutionStrategy
            from agents.base_enhanced_agent import AgentCapabilities, CommunicationMode
            
            # Create agent capabilities
            capabilities = AgentCapabilities(
                primary_functions=["web_research", "fact_verification", "information_synthesis"],
                supported_languages=["en", "fr", "es", "de", "ja", "zh"],
                communication_modes=[CommunicationMode.COLLABORATIVE],
                conflict_resolution_strategies=[ResolutionStrategy.EXPERT_OVERRIDE],
                context_scopes=[ContextScope.TASK, ContextScope.WORKFLOW]
            )
            
            # Create research agent instance
            research_agent = EnhancedResearchAgent(
                agent_id=f"research_{datetime.now().timestamp()}"
            )
            
            # Initialize the agent
            await research_agent.initialize()
            
            # Process the request
            user_request = state.get('user_request', '')
            session_context = state.get('session_context', {})
            
            result = await research_agent.process_request(
                request=user_request,
                context=session_context
            )
            
            # Extract the response
            agent_response = result.get('response', 'Research completed successfully.')
            
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "research": agent_response
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "research"]
            }
            
        except Exception as e:
            logger.error(f"Error in research agent node: {e}")
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "research": f"I encountered an error during research: {str(e)}"
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "research"],
                "error_messages": state.get("error_messages", []) + [f"Research agent error: {str(e)}"]
            }
    
    
    async def _coding_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Coding agent node implementation with real agent integration."""
        logger.info("Coding agent node called")
        
        try:
            # Import the enhanced coding agent
            from agents.enhanced_coding_agent import EnhancedCodingAgent
            from communication.protocols import AgentType
            from communication.context_manager import ContextScope
            from communication.conflict_resolver import ResolutionStrategy
            from agents.base_enhanced_agent import AgentCapabilities, CommunicationMode
            
            # Create agent capabilities
            capabilities = AgentCapabilities(
                primary_functions=["code_generation", "debugging", "code_review", "architecture_design"],
                supported_languages=["en", "fr", "es", "de"],
                communication_modes=[CommunicationMode.COLLABORATIVE],
                conflict_resolution_strategies=[ResolutionStrategy.EXPERT_OVERRIDE],
                context_scopes=[ContextScope.TASK, ContextScope.WORKFLOW]
            )
            
            # Create coding agent instance
            coding_agent = EnhancedCodingAgent(
                agent_id=f"coding_{datetime.now().timestamp()}",
                agent_type=AgentType.CODING,
                agent_name="Enhanced Coding Agent",
                capabilities=capabilities
            )
            
            # Initialize the agent
            await coding_agent.initialize()
            
            # Process the request
            user_request = state.get('user_request', '')
            session_context = state.get('session_context', {})
            
            result = await coding_agent.process_request(
                request=user_request,
                context=session_context
            )
            
            # Extract the response
            agent_response = result.get('response', 'Coding task completed successfully.')
            
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "coding": agent_response
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "coding"]
            }
            
        except Exception as e:
            logger.error(f"Error in coding agent node: {e}")
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "coding": f"I encountered an error during coding: {str(e)}"
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "coding"],
                "error_messages": state.get("error_messages", []) + [f"Coding agent error: {str(e)}"]
            }
    
    async def _document_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Document intelligence agent node implementation with real agent integration."""
        logger.info("Document intelligence agent node called")
        
        try:
            # Import the enhanced document intelligence agent
            from agents.enhanced_document_intelligence_agent import EnhancedDocumentIntelligenceAgent
            from communication.protocols import AgentType
            from communication.context_manager import ContextScope
            from communication.conflict_resolver import ResolutionStrategy
            from agents.base_enhanced_agent import AgentCapabilities, CommunicationMode
            
            # Create agent capabilities
            capabilities = AgentCapabilities(
                primary_functions=["document_analysis", "content_extraction", "document_comparison"],
                supported_languages=["en", "fr", "es", "de", "ja", "zh"],
                communication_modes=[CommunicationMode.COLLABORATIVE],
                conflict_resolution_strategies=[ResolutionStrategy.MERGE_COMPATIBLE],
                context_scopes=[ContextScope.TASK, ContextScope.WORKFLOW]
            )
            
            # Create document intelligence agent instance
            doc_agent = EnhancedDocumentIntelligenceAgent(
                agent_id=f"document_{datetime.now().timestamp()}",
                agent_type=AgentType.DOCUMENT_INTELLIGENCE,
                agent_name="Enhanced Document Intelligence Agent",
                capabilities=capabilities
            )
            
            # Initialize the agent
            await doc_agent.initialize()
            
            # Process the request
            user_request = state.get('user_request', '')
            session_context = state.get('session_context', {})
            
            result = await doc_agent.process_request(
                request=user_request,
                context=session_context
            )
            
            # Extract the response
            agent_response = result.get('response', 'Document analysis completed successfully.')
            
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "document_intelligence": agent_response
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "document_intelligence"]
            }
            
        except Exception as e:
            logger.error(f"Error in document intelligence agent node: {e}")
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "document_intelligence": f"I encountered an error during document analysis: {str(e)}"
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "document_intelligence"],
                "error_messages": state.get("error_messages", []) + [f"Document agent error: {str(e)}"]
            }
    
    async def _multimodal_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Multimodal agent node implementation using multimodal tools."""
        logger.info("Multimodal agent node called")
        
        try:
            # Import multimodal tools directly since there's no dedicated multimodal agent
            from tools.multimodal_tools import (
                imager_tool, image_vision_tool, images_search_tool, video_tool
            )
            from ai.multimodal_engine import MultimodalEngine
            from models.models import get_google_model
            
            # Create a basic multimodal processor
            model = get_google_model()
            multimodal_engine = MultimodalEngine()
            
            # Process the request
            user_request = state.get('user_request', '')
            session_context = state.get('session_context', {})
            
            # Determine what type of multimodal processing is needed
            request_lower = user_request.lower()
            
            if any(word in request_lower for word in ['image', 'picture', 'photo', 'visual', 'see']):
                # Image-related request
                if 'analyze' in request_lower or 'describe' in request_lower:
                    # Use vision tool (requires image input)
                    response = f"I can analyze images when provided. Please share an image to analyze: {user_request}"
                elif 'search' in request_lower or 'find' in request_lower:
                    # Use image search
                    try:
                        search_result = await images_search_tool.ainvoke({"query": user_request})
                        response = f"Found images related to your request: {search_result}"
                    except:
                        response = f"I searched for images related to '{user_request}' but encountered an issue."
                elif 'create' in request_lower or 'generate' in request_lower:
                    # Use image generation
                    try:
                        generation_result = await imager_tool.ainvoke({"query": user_request})
                        response = f"Generated image based on your request: {generation_result}"
                    except:
                        response = f"I attempted to generate an image for '{user_request}' but encountered an issue."
                else:
                    response = f"I can help with image analysis, search, and generation. {user_request}"
            
            elif any(word in request_lower for word in ['video', 'movie', 'film']):
                # Video-related request
                try:
                    video_result = await video_tool.ainvoke({"query": user_request})
                    response = f"Processed video request: {video_result}"
                except:
                    response = f"I processed your video request '{user_request}' but encountered an issue."
            
            else:
                # General multimodal request
                response = f"I can help with image analysis, generation, search, and video processing. For '{user_request}', please specify what type of multimodal assistance you need."
            
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "multimodal": response
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "multimodal"]
            }
            
        except Exception as e:
            logger.error(f"Error in multimodal agent node: {e}")
            return {
                **state,
                "agent_results": {
                    **state.get("agent_results", {}),
                    "multimodal": f"I encountered an error during multimodal processing: {str(e)}"
                },
                "active_agents": [agent for agent in state.get("active_agents", []) if agent != "multimodal"],
                "error_messages": state.get("error_messages", []) + [f"Multimodal agent error: {str(e)}"]
            }
    
    def _synthesizer_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizer node that aggregates results into final response."""
        try:
            logger.info("Synthesizer node processing results")
            
            user_request = state.get('user_request', '')
            agent_results = state.get('agent_results', {})
            
            # Create synthesis prompt
            synthesis_prompt = f"""
            Synthesize the following agent results into a coherent, comprehensive response to the user's request.
            
            User Request: "{user_request}"
            
            Agent Results:
            {self._format_agent_results(agent_results)}
            
            Instructions:
            1. Create a unified, coherent response that addresses the user's request
            2. Integrate information from all agents seamlessly
            3. Maintain the persona and tone of Jarvis from the MCU
            4. Ensure the response is clear, helpful, and complete
            5. Do not mention the individual agents or the orchestration process
            """
            
            # Generate synthesis using the model
            response = self.model.invoke([
                SystemMessage(content="You are Jarvis, synthesizing multi-agent results into a unified response."),
                HumanMessage(content=synthesis_prompt)
            ])
            
            final_response = response.content if hasattr(response, 'content') else str(response)
            
            return {
                **state,
                "final_response": final_response,
                "workflow_status": "complete"
            }
            
        except Exception as e:
            logger.error("Error in synthesizer node: %s", str(e))
            return {
                **state,
                "final_response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "workflow_status": "error",
                "error_messages": state.get("error_messages", []) + [str(e)]
            }
    
    def _format_agent_results(self, agent_results: Dict[str, Any]) -> str:
        """Format agent results for synthesis prompt."""
        if not agent_results:
            return "No agent results available."
        
        formatted = []
        for agent_name, result in agent_results.items():
            formatted.append(f"{agent_name.title()} Agent Result:\n{result}\n")
        
        return "\n".join(formatted)


async def create_supervisor_agent() -> SupervisorAgent:
    """
    Factory function to create and initialize a supervisor agent.
    
    Returns:
        Initialized SupervisorAgent instance
    """
    try:
        supervisor = SupervisorAgent()
        logger.info("Supervisor agent created successfully")
        return supervisor
        
    except Exception as e:
        logger.error("Error creating supervisor agent: %s", str(e))
        raise AgentError(f"Failed to create supervisor agent: {str(e)}")


# Export the main class and factory function
__all__ = [
    "SupervisorAgent", 
    "create_supervisor_agent",
    "TaskComplexity",
    "AgentType", 
    "TaskAnalysis",
    "WorkflowState"
]
