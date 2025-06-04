def summarize(query: str, **kwargs) -> str:
    """
    You are an expert in writing comprehensive summaries.
    """
    return f"<CONTEXT>{query}</CONTEXT>\nBased on the context, you should now focus on writing a comprehensive summary of the results."

def finalize(query: str, **kwargs) ->str:
    """
    You are a helpful assistant in summarizing the information and answer user's query..
    """
    return f"Please finalize the information you have gathered so far. <CONTEXT>{kwargs['knowledge']}</CONTEXT><QUERY>{query}</QUERY>. Summarize the context and answer the query in a concise, comprehensive manner."