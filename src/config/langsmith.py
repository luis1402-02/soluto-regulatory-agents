"""LangSmith integration for complete observability."""

import os
from typing import Optional

from langsmith import Client
from langsmith.run_helpers import traceable


def configure_langsmith():
    """Configure LangSmith for tracing and monitoring."""
    # Set environment variables for LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    # Project name for organization
    project_name = os.getenv("LANGCHAIN_PROJECT", "soluto-regulatory-agents")
    os.environ["LANGCHAIN_PROJECT"] = project_name
    
    # Ensure API key is set
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("⚠️  Warning: LANGCHAIN_API_KEY not set. Tracing disabled.")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return None
    
    try:
        # Initialize LangSmith client
        client = Client()
        
        # Test connection
        client.list_projects(limit=1)
        
        print(f"✅ LangSmith connected to project: {project_name}")
        return client
        
    except Exception as e:
        print(f"❌ LangSmith connection failed: {e}")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return None


def get_langsmith_url(run_id: str) -> str:
    """Get LangSmith trace URL for a run."""
    project = os.getenv("LANGCHAIN_PROJECT", "soluto-regulatory-agents")
    return f"https://smith.langchain.com/public/{project}/r/{run_id}"


# Decorator for tracing functions
def trace_function(name: Optional[str] = None, **kwargs):
    """Decorator to trace function execution in LangSmith."""
    return traceable(name=name, **kwargs)


# Configure on import
langsmith_client = configure_langsmith()