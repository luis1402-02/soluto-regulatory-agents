"""Base agent class and types."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..config import get_settings
from ..memory import Memory
from ..tools import BaseTool
from ..utils import AgentLogger


class AgentState(TypedDict):
    """State shared between agents."""

    messages: List[BaseMessage]
    current_agent: str
    task: str
    context: Dict[str, Any]
    memory_entries: List[str]
    iteration: int
    max_iterations: int
    final_output: Optional[str]
    error: Optional[str]


class AgentConfig(BaseModel):
    """Agent configuration."""

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    model: str = Field(default="gpt-4.1", description="Model to use")
    temperature: float = Field(default=0.1, description="Model temperature")
    max_tokens: Optional[int] = Field(None, description="Max tokens")
    tools: List[BaseTool] = Field(default_factory=list, description="Available tools")
    system_prompt: str = Field(..., description="System prompt")


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(
        self,
        config: AgentConfig,
        memory: Memory,
        logger: Optional[AgentLogger] = None,
    ):
        """Initialize base agent."""
        self.config = config
        self.memory = memory
        self.logger = logger or AgentLogger(config.name)
        self.settings = get_settings()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=self.settings.openai_api_key.get_secret_value(),
        )

    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """Process the current state and return updated state."""
        pass

    async def think(self, state: AgentState) -> str:
        """Generate thoughts about the current state."""
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": self._format_state_for_thinking(state)},
        ]
        
        response = await self.llm.ainvoke(messages)
        thought = response.content
        
        self.logger.log_thought(thought)
        return thought

    async def act(self, state: AgentState, action: str) -> Any:
        """Execute an action based on the current state."""
        self.logger.log_action(action, {"state": state})
        
        # Store action in memory
        await self.memory.remember(
            content=f"Action: {action}",
            agent_id=self.config.name,
            thread_id=state.get("thread_id"),
        )
        
        return action

    async def use_tool(self, tool: BaseTool, **kwargs) -> Any:
        """Use a tool and log the interaction."""
        result = await tool.execute(**kwargs)
        
        self.logger.log_tool_use(
            tool=tool.name,
            input_data=kwargs,
            output=result.output if result.success else result.error,
        )
        
        # Store tool usage in memory
        await self.memory.remember(
            content=f"Used tool {tool.name}: {result.output if result.success else result.error}",
            agent_id=self.config.name,
        )
        
        return result

    def _format_state_for_thinking(self, state: AgentState) -> str:
        """Format state for thinking process."""
        recent_messages = state["messages"][-5:]  # Last 5 messages
        
        formatted = f"""
Current Task: {state['task']}
Current Agent: {state['current_agent']}
Iteration: {state['iteration']}/{state['max_iterations']}

Recent Messages:
"""
        for msg in recent_messages:
            role = "Human" if isinstance(msg, HumanMessage) else "AI"
            formatted += f"\n{role}: {msg.content[:200]}..."
        
        if state.get("context"):
            formatted += f"\n\nContext: {state['context']}"
        
        return formatted

    async def retrieve_memories(
        self,
        query: str,
        thread_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[str]:
        """Retrieve relevant memories."""
        memories = await self.memory.search_memories(
            query=query,
            agent_id=self.config.name,
            thread_id=thread_id,
            limit=limit,
        )
        
        return [m.content for m in memories]

    async def summarize_conversation(self, state: AgentState) -> str:
        """Summarize the conversation so far."""
        messages = state["messages"]
        
        summary_prompt = f"""
Please summarize the following conversation concisely:

{self._format_messages_for_summary(messages)}

Summary:
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
            {"role": "user", "content": summary_prompt},
        ])
        
        return response.content

    def _format_messages_for_summary(self, messages: List[BaseMessage]) -> str:
        """Format messages for summary."""
        formatted = ""
        for msg in messages:
            role = "Human" if isinstance(msg, HumanMessage) else "AI"
            formatted += f"{role}: {msg.content}\n\n"
        return formatted