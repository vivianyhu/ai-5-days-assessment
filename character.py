# character.py
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types
from google.adk.tools import google_search

root_agent = LlmAgent(
    model='gemini-3.5-flash',
    name='companion_agent',
    instruction="""
    You are an automated Blog Writer Assistant. 
    Use the google_search tool to look up current trends when asked.
    Always respond clearly and answer in under 4 sentences.
    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=5, initial_delay=1.0)
        )
    )
)

