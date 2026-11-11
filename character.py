# character.py
"""
Main entry point. Orchestrates Multi-Agent patterns, Model Routing,
History Compaction, and SQLite Persistent Sessions.
"""

import os
import asyncio
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.apps.app import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types

# Import our custom dependencies
from tools import fetch_industry_trends_by_category, publish_article_to_cms
from observability import structured_logger, telemetry_span

# Secure Secret Management: Leverage system environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Strategic Model Routing & Multi-Agent Architecture ---

# Sub-Agent: Fast model routing for data retrieval tasks
research_agent = LlmAgent(
    name="research_agent",
    model="gemini-2.5-flash", 
    instruction="""
    You are a research bot. Use the 'fetch_industry_trends_by_category' tool to look up trends.
    Format them as clear, brief bullet points.
    """,
    tools=[fetch_industry_trends_by_category]
)

# Coordinator Agent: Complex reasoning and supervisor
root_agent = LlmAgent(
    name="editorial_director",
    model="gemini-2.5-pro", # Routing planning & editorial check to Pro
    instruction="""
    You are the Editorial Director Agent. 
    
    ### CONSTITUTION:
    1. Workflow: Delegate vertical trend research to the 'research_agent' sub-agent.
    2. Publishing: Use 'publish_article_to_cms' to publish your finalized drafts.
    3. Respect human supervisor decisions returned by the publication tool.
    """,
    tools=[
        AgentTool(agent=research_agent), # Multi-Agent pattern
        publish_article_to_cms
    ],
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=5, initial_delay=1.0)
        )
    )
)

# --- Context & Memory Compaction Configuration ---
app = App(
    name="enterprise_cms_agent",
    root_agent=root_agent,
    # Automatic compaction summarizing history after 3 turns
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1
    ),
    resumability_config=ResumabilityConfig(is_resumable=True)
)

# --- Persistent SQLite session database ---
try:
    session_database = DatabaseSessionService(db_url="sqlite+aiosqlite:///session_store.db")
except ValueError:
    session_database = DatabaseSessionService(db_url="sqlite:///session_store.db")

async def run_turn(user_query: str, session_id: str = "main_session_01") -> str:
    """Async execution wrapper capturing trace metrics."""
    with telemetry_span("run_turn", intent_description=f"Process: {user_query}") as span:
        runner = Runner(app=app, session_service=session_database)
        
        # Verify database session state container
        session = await session_database.get_session(
            app_name=app.name, user_id="default_user", session_id=session_id
        )
        if session is None:
            await session_database.create_session(
                app_name=app.name, user_id="default_user", session_id=session_id
            )

        new_message = types.Content(
            role="user", parts=[types.Part(text=user_query)]
        )
        response_text = ""
        async for event in runner.run_async(
            user_id="default_user",
            session_id=session_id,
            new_message=new_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
                
        span["response_length"] = len(response_text)
        return response_text

if __name__ == "__main__":
    query = "Research technology trends and publish an article named 'Future of AI'."
    print("Executing workflow...")
    response = asyncio.run(run_turn(query))
    print("\nFinal Response:\n", response)
