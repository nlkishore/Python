import os
from langchain_openai import ChatOpenAI

# Mock Configuration
# In a real app, these would come from env vars
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-mock-key-for-demo")
MODEL_NAME = "gpt-4o"

def get_llm():
    """Returns the configured LLM instance."""
    # For the purpose of this demo without a real key, we might need a mock LLM 
    # or assume the user has a key.
    # If no key is present, we can fallback to a dummy for the structure 
    # but the agents depend on LLM logic.
    
    if "mock" in OPENAI_API_KEY:
        print("WARNING: Using Mock LLM key. Calls will fail if not using a simulation mode or real key.")
        
    return ChatOpenAI(model=MODEL_NAME, temperature=0)
