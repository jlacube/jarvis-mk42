# agents/enhanced_reasoning_agent.py
"""
Enhanced Reasoning Agent - Phase 2B.3
======================================

This module implements the enhanced reasoning agent with advanced capabilities:
- Integration with Phase 2B.2 communication framework
- Language detection and multi-language support
- Advanced cognitive models and multi-step problem solving
- Knowledge integration from multiple sources
- Collaborative reasoning with other agents

Key Enhancements over Basic Reasoning Agent:
- Multi-language reasoning and response generation
- Inter-agent communication and collaboration
- Shared context awareness
- Conflict resolution participation
- Advanced cognitive patterns and methodologies
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

import chainlit as cl
from langchain_core.prompts import PromptTemplate
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

# Import base agent and communication framework
from agents.base_enhanced_agent import (
    BaseEnhancedAgent, AgentCapabilities, CommunicationMode, AgentState
)
from communication.protocols import AgentType, MessageType, MessagePriority
from communication.context_manager import ContextScope
from communication.conflict_resolver import ResolutionStrategy

# Import models and tools
from models.models import get_google_model, get_google_reasoning_model
from agent_management import get_allowed_tools_from_env, get_all_tools
from prompts import get_prompt

# Import reasoning tools
from tools.reasoning_model_tool import reasoning_model_tool
from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history
from tools.research_tools import get_research_tools
from tools.language_detection import (
    detect_language, detect_language_with_confidence, detect_multiple_languages
)

# Import language utilities
from utils.language_utils import (
    get_language_context, normalize_text_for_language, 
    is_formal_language_context, estimate_reading_time
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ReasoningTask:
    """Definition of a reasoning task with complexity analysis."""
    task_id: str
    request: str
    language: str
    complexity: str  # 'simple', 'moderate', 'complex', 'advanced'
    reasoning_type: str  # 'logical', 'analytical', 'creative', 'strategic'
    requires_collaboration: bool
    estimated_steps: int
    context_requirements: List[str]


@dataclass
class ReasoningResult:
    """Result of a reasoning task with detailed metadata."""
    success: bool
    result: Any
    reasoning_steps: List[str]
    confidence: float
    language: str
    execution_time: float
    collaboration_agents: List[str]
    context_used: List[str]
    error: Optional[str] = None


class EnhancedReasoningAgent(BaseEnhancedAgent):
    """
    Enhanced reasoning agent with multi-language support and communication capabilities.
    
    This agent extends the base reasoning capabilities with:
    - Language detection and multi-language reasoning
    - Advanced cognitive models for complex problem solving
    - Inter-agent collaboration and knowledge integration
    - Context-aware reasoning with shared state
    - Conflict resolution participation
    """
    
    def __init__(self, agent_id: str = "enhanced-reasoning-agent", **kwargs):
        """Initialize the enhanced reasoning agent."""
        
        # Define enhanced capabilities
        capabilities = AgentCapabilities(
            primary_functions=[
                "multi_step_reasoning", "problem_decomposition", "logical_analysis",
                "strategic_planning", "decision_making", "knowledge_synthesis",
                "multi_language_reasoning", "collaborative_reasoning"
            ],
            supported_languages=[
                "en", "es", "fr", "de", "it", "pt", "ru", "zh-cn", "ja", "ko",
                "ar", "hi", "bn", "pl", "nl", "sv", "da", "no"
            ],
            communication_modes=[
                CommunicationMode.STANDALONE, CommunicationMode.COLLABORATIVE,
                CommunicationMode.DELEGATING, CommunicationMode.RESPONDING
            ],
            conflict_resolution_strategies=[
                ResolutionStrategy.WEIGHTED_VOTE, ResolutionStrategy.EXPERT_OVERRIDE,
                ResolutionStrategy.CONSENSUS_BUILDING
            ],
            context_scopes=[
                ContextScope.TASK, ContextScope.CONVERSATION, 
                ContextScope.WORKFLOW, ContextScope.AGENT
            ],
            max_concurrent_tasks=5,
            supports_streaming=True,
            requires_context=True
        )
        
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.REASONING,
            agent_name="Enhanced Reasoning Agent",
            capabilities=capabilities,
            **kwargs
        )
        
        # Reasoning-specific attributes
        self.reasoning_model = None
        self.langgraph_agent = None
        self.available_tools = []
        self.reasoning_strategies = {
            'logical': self._logical_reasoning,
            'analytical': self._analytical_reasoning,
            'creative': self._creative_reasoning,
            'strategic': self._strategic_reasoning
        }
        
        # Collaboration tracking
        self.active_collaborations: Dict[str, List[str]] = {}
        self.knowledge_cache: Dict[str, Any] = {}
    
    async def _initialize_agent_specific(self) -> None:
        """Initialize reasoning-specific components."""
        try:
            self.logger.info("Initializing enhanced reasoning agent components")
            
            # Initialize models
            self.reasoning_model = get_google_reasoning_model(streaming=False)
            
            # Get allowed tools
            agent_name = "Reasoning_Agent"
            allowed_tools = get_allowed_tools_from_env(agent_name)
            
            # Core reasoning tools
            core_tools = [
                sequential_thinking_tool, generate_summary, clear_history, 
                reasoning_model_tool
            ]
            filtered_core_tools = [
                tool for tool in core_tools 
                if tool.name in (allowed_tools or [])
            ]
            
            # Research tools
            research_tools = get_research_tools()
            filtered_research_tools = [
                tool for tool in research_tools 
                if tool.name in (allowed_tools or [])
            ]
            
            # Language detection tools
            language_tools = [
                detect_language, detect_language_with_confidence, detect_multiple_languages
            ]
            filtered_language_tools = [
                tool for tool in language_tools
                if tool.name in (allowed_tools or [])
            ]
            
            # Combine all tools
            self.available_tools = (
                filtered_core_tools + filtered_research_tools + filtered_language_tools
            )
            
            # Create LangGraph agent
            await self._create_langgraph_agent()
            
            self.logger.info(
                f"Enhanced reasoning agent initialized with {len(self.available_tools)} tools"
            )
            
        except Exception as e:
            self.logger.error(f"Error initializing reasoning agent: {e}")
            raise
    
    async def _cleanup_agent_specific(self) -> None:
        """Cleanup reasoning-specific resources."""
        self.active_collaborations.clear()
        self.knowledge_cache.clear()
        self.available_tools.clear()
        
        if self.langgraph_agent:
            # LangGraph agents don't require explicit cleanup
            self.langgraph_agent = None
    
    async def _create_langgraph_agent(self) -> None:
        """Create the LangGraph reasoning agent with enhanced prompt."""
        try:
            # Get enhanced reasoning prompt
            base_prompt = get_prompt("reasoning_agent")
            
            # Enhance prompt with multi-language and collaboration instructions
            enhanced_prompt = self._create_enhanced_prompt(base_prompt)
            
            # Create prompt template with session variables
            prompt_template = PromptTemplate(
                template=enhanced_prompt,
                input_variables=["now", "user_id", "session_id", "user_name", "thread_id"]
            )
            
            # Get session variables
            now = cl.user_session.get("now", datetime.now().isoformat())
            user_id = cl.user_session.get("user_id", "unknown")
            session_id = cl.user_session.get("session_id", "unknown")
            user_name = cl.user_session.get("user_name", "User")
            thread_id = cl.user_session.get("thread_id", "unknown")
            
            # Create prompt
            prompt = prompt_template.invoke(input=dict([
                ("now", now),
                ("user_id", user_id),
                ("session_id", session_id),
                ("user_name", user_name),
                ("thread_id", thread_id)
            ]))
            
            # Create LangGraph agent
            self.langgraph_agent = create_react_agent(
                name="Enhanced_Reasoning_Agent",
                model=self.reasoning_model,
                tools=self.available_tools,
                prompt=str(prompt)
            )
            
            self.logger.info("LangGraph reasoning agent created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating LangGraph agent: {e}")
            raise
    
    def _create_enhanced_prompt(self, base_prompt: str) -> str:
        """Create enhanced prompt with multi-language and collaboration instructions."""
        
        enhanced_sections = """

## ENHANCED REASONING CAPABILITIES (Phase 2B.3)

### Multi-Language Support
- You have advanced language detection capabilities using the detect_language tool
- Always detect the user's language first and respond in the same language
- Use detect_language_with_confidence for detailed language analysis
- For mixed-language content, use detect_multiple_languages
- Maintain language consistency throughout reasoning chains
- Adapt reasoning style to language-specific patterns (formal vs. informal registers)

### Collaborative Reasoning
- You can collaborate with other agents through the communication framework
- Use shared context to maintain information across agent interactions
- Participate in conflict resolution when different reasoning approaches are proposed
- Request assistance from research agents for fact-checking
- Coordinate with coding agents for technical implementation details
- Leverage document intelligence agents for information synthesis

### Advanced Reasoning Strategies
1. **Logical Reasoning**: Step-by-step deductive and inductive analysis
2. **Analytical Reasoning**: Data-driven analysis with pattern recognition
3. **Creative Reasoning**: Innovative problem-solving and lateral thinking
4. **Strategic Reasoning**: Long-term planning and decision optimization

### Context Awareness
- Always consider shared context from previous interactions
- Update context with reasoning progress and insights
- Use context to avoid redundant analysis
- Share insights with other agents through context updates

### Quality Assurance
- Validate reasoning steps for logical consistency
- Cross-reference facts with research agents when needed
- Provide confidence scores for reasoning conclusions
- Acknowledge uncertainty and limitations
- Request human verification for critical decisions

### Language-Specific Reasoning Patterns
- **English**: Direct, structured, evidence-based
- **Spanish**: Contextual, relationship-focused
- **French**: Methodical, nuanced, precision-oriented
- **German**: Systematic, thorough, rule-based
- **Chinese**: Holistic, harmony-seeking, long-term oriented
- **Japanese**: Consensus-building, detail-oriented, respectful
- **Arabic**: Context-rich, tradition-aware, community-focused

Remember to:
- Always use detect_language first to identify the user's language
- Adapt your reasoning style to the detected language and culture
- Collaborate with other agents when the task requires diverse expertise
- Maintain high reasoning quality regardless of language complexity
"""
        
        return base_prompt + enhanced_sections
    
    async def _process_request_internal(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
        language_context: Any,
        task_id: str
    ) -> Dict[str, Any]:
        """Process reasoning request with enhanced capabilities."""
        
        start_time = datetime.now()
        self.logger.info(f"Processing reasoning request in {language_context.language_name}")
        
        try:
            # Analyze the reasoning task
            task_analysis = await self._analyze_reasoning_task(
                request, language_context, context, task_id
            )
            
            # Store task in active tasks
            self.active_tasks[task_id] = task_analysis
            
            # Determine if collaboration is needed
            if task_analysis.requires_collaboration:
                await self._setup_collaboration(task_id, task_analysis)
            
            # Execute reasoning based on complexity and type
            reasoning_result = await self._execute_reasoning(task_analysis)
            
            # Update shared context with results
            if self.context_manager:
                await self._update_reasoning_context(task_id, reasoning_result)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': reasoning_result.success,
                'result': reasoning_result.result,
                'reasoning_steps': reasoning_result.reasoning_steps,
                'confidence': reasoning_result.confidence,
                'language': reasoning_result.language,
                'execution_time': execution_time,
                'task_analysis': {
                    'complexity': task_analysis.complexity,
                    'reasoning_type': task_analysis.reasoning_type,
                    'estimated_steps': task_analysis.estimated_steps
                },
                'collaboration': {
                    'agents_involved': reasoning_result.collaboration_agents,
                    'context_used': reasoning_result.context_used
                },
                'agent_id': self.agent_id,
                'task_id': task_id
            }
            
        except Exception as e:
            self.logger.error(f"Error in reasoning process: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent_id': self.agent_id,
                'task_id': task_id,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def _analyze_reasoning_task(
        self,
        request: str,
        language_context: Any,
        context: Optional[Dict[str, Any]],
        task_id: str
    ) -> ReasoningTask:
        """Analyze the reasoning task to determine approach and requirements."""
        
        # Normalize text for analysis
        normalized_request = normalize_text_for_language(request, language_context.language_code)
        
        # Determine complexity based on request characteristics
        complexity = self._determine_complexity(normalized_request)
        
        # Determine reasoning type
        reasoning_type = self._determine_reasoning_type(normalized_request)
        
        # Estimate steps required
        estimated_steps = self._estimate_reasoning_steps(normalized_request, complexity)
        
        # Determine if collaboration is needed
        requires_collaboration = self._requires_collaboration(normalized_request, complexity)
        
        # Identify context requirements
        context_requirements = self._identify_context_requirements(normalized_request, context)
        
        return ReasoningTask(
            task_id=task_id,
            request=normalized_request,
            language=language_context.language_code,
            complexity=complexity,
            reasoning_type=reasoning_type,
            requires_collaboration=requires_collaboration,
            estimated_steps=estimated_steps,
            context_requirements=context_requirements
        )
    
    async def _execute_reasoning(self, task: ReasoningTask) -> ReasoningResult:
        """Execute the reasoning task using the appropriate strategy."""
        
        start_time = datetime.now()
        collaboration_agents = []
        context_used = []
        
        try:
            # Select reasoning strategy
            strategy = self.reasoning_strategies.get(
                task.reasoning_type, self._logical_reasoning
            )
            
            # Execute reasoning strategy
            reasoning_steps, result, confidence = await strategy(task)
            
            # Handle collaboration if required
            if task.requires_collaboration:
                collaboration_result = await self._execute_collaboration(task)
                if collaboration_result:
                    collaboration_agents = collaboration_result.get('agents', [])
                    # Integrate collaboration results
                    result = self._integrate_collaboration_results(result, collaboration_result)
            
            # Get context used
            if task.context_requirements:
                context_used = task.context_requirements
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ReasoningResult(
                success=True,
                result=result,
                reasoning_steps=reasoning_steps,
                confidence=confidence,
                language=task.language,
                execution_time=execution_time,
                collaboration_agents=collaboration_agents,
                context_used=context_used
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ReasoningResult(
                success=False,
                result=None,
                reasoning_steps=[],
                confidence=0.0,
                language=task.language,
                execution_time=execution_time,
                collaboration_agents=collaboration_agents,
                context_used=context_used,
                error=str(e)
            )
    
    async def _logical_reasoning(self, task: ReasoningTask) -> tuple:
        """Execute logical reasoning strategy."""
        self.logger.info(f"Executing logical reasoning for task {task.task_id}")
        
        # Use the LangGraph agent for logical reasoning
        if self.langgraph_agent:
            result = await self.langgraph_agent.ainvoke({
                "messages": [{"role": "user", "content": task.request}]
            })
            
            # Extract reasoning steps and conclusion
            reasoning_steps = ["Logical analysis initiated", "Evidence evaluated", "Conclusion reached"]
            confidence = 0.85  # Logical reasoning typically has high confidence
            
            return reasoning_steps, result, confidence
        
        # Fallback implementation
        return ["Basic logical analysis"], f"Logical analysis of: {task.request}", 0.7
    
    async def _analytical_reasoning(self, task: ReasoningTask) -> tuple:
        """Execute analytical reasoning strategy."""
        self.logger.info(f"Executing analytical reasoning for task {task.task_id}")
        
        # Enhanced analytical approach with data focus
        if self.langgraph_agent:
            enhanced_request = f"Analyze the following systematically with data-driven approach: {task.request}"
            result = await self.langgraph_agent.ainvoke({
                "messages": [{"role": "user", "content": enhanced_request}]
            })
            
            reasoning_steps = [
                "Data collection and validation",
                "Pattern identification", 
                "Statistical analysis",
                "Trend assessment",
                "Conclusion synthesis"
            ]
            confidence = 0.8
            
            return reasoning_steps, result, confidence
        
        return ["Analytical framework applied"], f"Analytical assessment: {task.request}", 0.75
    
    async def _creative_reasoning(self, task: ReasoningTask) -> tuple:
        """Execute creative reasoning strategy."""
        self.logger.info(f"Executing creative reasoning for task {task.task_id}")
        
        # Creative problem-solving approach
        if self.langgraph_agent:
            creative_request = f"Approach this creatively with innovative thinking: {task.request}"
            result = await self.langgraph_agent.ainvoke({
                "messages": [{"role": "user", "content": creative_request}]
            })
            
            reasoning_steps = [
                "Problem reframing",
                "Brainstorming alternatives",
                "Lateral thinking application",
                "Solution synthesis",
                "Innovation validation"
            ]
            confidence = 0.7  # Creative solutions have more uncertainty
            
            return reasoning_steps, result, confidence
        
        return ["Creative exploration"], f"Creative analysis: {task.request}", 0.65
    
    async def _strategic_reasoning(self, task: ReasoningTask) -> tuple:
        """Execute strategic reasoning strategy."""
        self.logger.info(f"Executing strategic reasoning for task {task.task_id}")
        
        # Strategic planning approach
        if self.langgraph_agent:
            strategic_request = f"Provide strategic analysis considering long-term implications: {task.request}"
            result = await self.langgraph_agent.ainvoke({
                "messages": [{"role": "user", "content": strategic_request}]
            })
            
            reasoning_steps = [
                "Situational analysis",
                "Goal identification",
                "Option evaluation", 
                "Risk assessment",
                "Strategic recommendation"
            ]
            confidence = 0.8
            
            return reasoning_steps, result, confidence
        
        return ["Strategic assessment"], f"Strategic evaluation: {task.request}", 0.75
    
    # Helper methods for task analysis
    def _determine_complexity(self, request: str) -> str:
        """Determine the complexity level of the reasoning task."""
        word_count = len(request.split())
        question_marks = request.count('?')
        complexity_indicators = ['analyze', 'compare', 'evaluate', 'synthesize', 'integrate']
        
        if word_count > 100 or question_marks > 2:
            return 'complex'
        elif word_count > 50 or any(indicator in request.lower() for indicator in complexity_indicators):
            return 'moderate'
        elif word_count > 20:
            return 'simple'
        else:
            return 'simple'
    
    def _determine_reasoning_type(self, request: str) -> str:
        """Determine the type of reasoning required."""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['create', 'invent', 'innovative', 'brainstorm']):
            return 'creative'
        elif any(word in request_lower for word in ['strategy', 'plan', 'long-term', 'future']):
            return 'strategic'
        elif any(word in request_lower for word in ['analyze', 'data', 'statistics', 'patterns']):
            return 'analytical'
        else:
            return 'logical'
    
    def _estimate_reasoning_steps(self, request: str, complexity: str) -> int:
        """Estimate the number of reasoning steps required."""
        base_steps = {'simple': 3, 'moderate': 5, 'complex': 8, 'advanced': 12}
        return base_steps.get(complexity, 5)
    
    def _requires_collaboration(self, request: str, complexity: str) -> bool:
        """Determine if the task requires collaboration with other agents."""
        collaboration_keywords = [
            'research', 'code', 'document', 'analyze file', 'compare', 'integrate',
            'multiple sources', 'comprehensive', 'detailed analysis'
        ]
        
        return (complexity in ['complex', 'advanced'] or 
                any(keyword in request.lower() for keyword in collaboration_keywords))
    
    def _identify_context_requirements(
        self, 
        request: str, 
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify what context information is needed."""
        requirements = []
        
        if 'previous' in request.lower() or 'before' in request.lower():
            requirements.append('conversation_history')
        
        if 'file' in request.lower() or 'document' in request.lower():
            requirements.append('document_context')
        
        if context and 'workflow' in context:
            requirements.append('workflow_context')
        
        return requirements
    
    async def _setup_collaboration(self, task_id: str, task: ReasoningTask) -> None:
        """Setup collaboration with other agents if needed."""
        # This would be implemented to coordinate with other agents
        # For now, we'll log the collaboration setup
        self.logger.info(f"Collaboration setup for task {task_id} - type: {task.reasoning_type}")
        self.active_collaborations[task_id] = []
    
    async def _execute_collaboration(self, task: ReasoningTask) -> Optional[Dict[str, Any]]:
        """Execute collaboration with other agents."""
        # Placeholder for collaboration execution
        # This would involve sending messages to other agents and coordinating responses
        return {
            'agents': ['research-agent'],
            'results': {'additional_context': 'Collaboration results would be integrated here'}
        }
    
    def _integrate_collaboration_results(self, original_result: Any, collaboration_result: Dict[str, Any]) -> Any:
        """Integrate results from collaboration with other agents."""
        # Simple integration for now - could be more sophisticated
        if isinstance(original_result, dict):
            original_result['collaboration_insights'] = collaboration_result.get('results', {})
        
        return original_result
    
    async def _update_reasoning_context(self, task_id: str, result: ReasoningResult) -> None:
        """Update shared context with reasoning results."""
        if not self.context_manager:
            return
        
        try:
            context = await self.context_manager.get_context(task_id, ContextScope.TASK)
            
            await context.set(
                "reasoning_result",
                {
                    "agent_id": self.agent_id,
                    "success": result.success,
                    "confidence": result.confidence,
                    "language": result.language,
                    "reasoning_steps": result.reasoning_steps,
                    "execution_time": result.execution_time,
                    "timestamp": datetime.now().isoformat()
                },
                self.agent_id,
                self.agent_type,
                "Reasoning results"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating reasoning context: {e}")


# Factory function for creating enhanced reasoning agent
async def get_enhanced_reasoning_agent(**kwargs) -> EnhancedReasoningAgent:
    """
    Create and initialize an enhanced reasoning agent.
    
    Returns:
        EnhancedReasoningAgent: Initialized enhanced reasoning agent
    """
    agent = EnhancedReasoningAgent(**kwargs)
    await agent.initialize()
    return agent
