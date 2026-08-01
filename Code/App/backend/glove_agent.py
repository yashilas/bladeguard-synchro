import asyncio
import os
from pathlib import Path
from agents import function_tool
import chromadb

materials_db_collection = None

try:
    from agents import Agent, Runner, trace
except ImportError:
    Agent = Runner = trace = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from dotenv import load_dotenv


def load_env(env_path: str = ".env") -> dict:
    """
    Read environment variables from a .env file and load them into os.environ.
 
    Returns a dict of the variables that were loaded from the file
    (useful if you want to inspect them without touching os.environ elsewhere).
    """
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f".env file not found at: {path.resolve()}")
 
    load_dotenv(dotenv_path=path)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    print(api_key)

    default_model = os.environ.get("OPENAI_DEFAULT_MODEL", "")
    print(default_model)

    if OpenAI is not None and default_model:
        OpenAI().responses.create(
            model=default_model,
            input="Say: We are up and running!"
        ).output_text
    else:
        print("OpenAI SDK is not available or no default model is configured.")

 
    # Optionally return just the keys defined in the file, resolved from os.environ
    loaded = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, _ = line.partition("=")
            key = key.strip()
            loaded[key] = os.environ.get(key)
 
    return loaded

async def main() -> None:
    env_vars = load_env(".env")
    print(f"Loaded env keys: {list(env_vars.keys())}")

    script_dir = Path(__file__).parent.parent.parent    
    chroma_client = chromadb.PersistentClient(path=script_dir / "chroma")
    global materials_db_collection
    materials_db_collection = chroma_client.get_collection(name="materials_db")

    # results = materials_db_collection.query(query_texts=["Acrylonitrile"], n_results=2)
    # for i, doc in enumerate(results["documents"][0]):
    #     print(sorted(results["metadatas"][0][i].items()))
    #     print(doc)
    #     print("\n")

    # response = material_lookup_tool(
    #     query="What are the best glove materials for synchronized figure skating?",
    #     max_results=3,
    # )
    # print(response)

    if Agent is None or Runner is None or trace is None:
        print("Agents SDK is not installed; skipping agent run.")
        return

    material_agent = Agent(
        name="Synchronized Figure Skating Materials Assistant",
        instructions="""You are a helpful assistant giving out advice on choosing glove materials for synchronized figure skating.
        You give concise answers.    
        If you need to look up material information, use the material_lookup_tool.""",
        tools=[material_lookup_tool],
    )

    with trace("Synchronized Figure Skating Materials Agent"):
        result = await Runner.run(material_agent, "What are the best glove materials for synchronized figure skating?")

    print(result.final_output)


@function_tool
def material_lookup_tool(query: str, max_results: int = 3) -> str:
    """
    Tool function to ask a question about materials.

    Args:
        query: The question to ask
        max_results: The maximum number of results to return.

    Returns:
        A string containing the question and the answer related to the query.
    """

    if materials_db_collection is None:
        return "Materials database is not initialized."

    results = materials_db_collection.query(query_texts=[query], n_results=max_results)

    if not results["documents"][0]:
        return f"No information found for: {query}"

    # Format results for the agent
    formatted_results = []
    for i, doc in enumerate(results["documents"][0]):
        formatted_results.append(doc)

    return "Related answers to your question:\n" + "\n".join(formatted_results)

if __name__ == "__main__":   
    asyncio.run(main())
