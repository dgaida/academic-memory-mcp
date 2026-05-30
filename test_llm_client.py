try:
    from llm_client import LLMClient
    print("LLMClient imported successfully")
except ImportError as e:
    print(f"Failed to import LLMClient: {e}")
