# tools.py
"""
Custom tools for the Editorial Agent Platform.
Implements explicit schemas, comprehensive docstrings, guided errors, and HIL approvals.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# --- Explicit Input & Output Schemas ---
class TrendAnalysisInput(BaseModel):
    category: str = Field(..., description="The industry category to research (e.g., 'technology', 'finance').")
    max_results: int = Field(default=3, ge=1, le=5, description="Number of results (1-5).")

class TrendAnalysisOutput(BaseModel):
    status: str = Field(..., description="Success or error status.")
    data: List[Dict[str, str]] = Field(default_factory=list)
    recovery_suggestion: Optional[str] = Field(None, description="Actionable recovery guide for the LLM.")

class PublishArticleInput(BaseModel):
    title: str = Field(..., min_length=5, description="The article title.")
    content: str = Field(..., min_length=20, description="The full markdown body draft.")

class PublishArticleOutput(BaseModel):
    status: str = Field(..., description="Status: 'published', 'pending_approval', or 'error'.")
    article_id: Optional[str] = Field(None)
    message: str = Field(...)
    recovery_suggestion: Optional[str] = Field(None)


# --- Custom Tool Implementations ---
def fetch_industry_trends_by_category(category: str, max_results: int = 3) -> Dict[str, Any]:
    """Query the localized database to retrieve trending topics for a specific industry category.

    Args:
        category (str): The industry vertical (e.g., 'technology', 'finance').
        max_results (int, optional): Maximum records to retrieve. Defaults to 3.

    Returns:
        Dict[str, Any]: Dictionary matching TrendAnalysisOutput with results or guided error recovery.
    """
    try:
        # Schema enforcement
        validated = TrendAnalysisInput(category=category, max_results=max_results)
        
        indexed_data = {
            "technology": [
                {"title": "Agentic AI Orchestration", "summary": "Multi-agent systems replacing single model prompts."},
                {"title": "Context Compaction", "summary": "Automatic memory consolidation for long sessions."}
            ],
            "finance": [
                {"title": "Autonomous Financial Compliance", "summary": "AI checking ledger logs against regulations."}
            ]
        }
        
        key = validated.category.lower().strip()
        if key not in indexed_data:
            return TrendAnalysisOutput(
                status="error",
                recovery_suggestion=(
                    f"Category '{category}' is not available. Available categories are: {list(indexed_data.keys())}. "
                    "Please ask the user for a valid category and try again."
                )
            ).model_dump()
            
        return TrendAnalysisOutput(
            status="success",
            data=indexed_data[key][:validated.max_results]
        ).model_dump()
        
    except Exception as exc:
        return TrendAnalysisOutput(
            status="error",
            recovery_suggestion=f"Input validation failed: {str(exc)}. Please check parameter types."
        ).model_dump()


def publish_article_to_cms(title: str, content: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Publish a draft article into production with Human-in-the-Loop safeguards.

    Args:
        title (str): Title of the post (min 5 chars).
        content (str): Content draft (min 20 chars).
        tool_context (ToolContext): Runtime state and approval management context.

    Returns:
        Dict[str, Any]: Dictionary matching PublishArticleOutput.
    """
    try:
        validated = PublishArticleInput(title=title, content=content)
        
        # Human-in-the-Loop Hook: Pause and request human operator confirmation
        if tool_context.tool_confirmation is None:
            tool_context.request_confirmation(
                hint=f"Approve publication of article: '{validated.title}'",
                payload={"title": validated.title}
            )
            return PublishArticleOutput(
                status="pending_approval",
                message="Workflow paused: Awaiting human supervisor approval."
            ).model_dump()
            
        # Evaluation & Outcome after resume
        if tool_context.tool_confirmation.confirmed:
            art_id = f"pub_{abs(hash(validated.title)) % 1000}"
            tool_context.state["user:last_published_id"] = art_id # Persisted in user context
            return PublishArticleOutput(
                status="published",
                article_id=art_id,
                message="Article successfully published to production CMS."
            ).model_dump()
        else:
            return PublishArticleOutput(
                status="error",
                message="Publication rejected by human supervisor.",
                recovery_suggestion="The draft was rejected. Ask the user for specific feedback to refine it."
            ).model_dump()
            
    except Exception as err:
        return PublishArticleOutput(
            status="error",
            message=str(err),
            recovery_suggestion="Ensure title has at least 5 characters and content has at least 20 characters."
        ).model_dump()
