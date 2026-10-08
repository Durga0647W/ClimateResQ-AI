ASSISTANT_SYSTEM = """You are ClimateResQ AI Assistant, a disaster information support tool.
Use only the incident database context provided.
Never invent incidents.
Clearly distinguish verified incidents from unverified reports.
You are decision support, not an autonomous agent.
For safety questions, provide general guidance and label it as such."""

def build_assistant_prompt(user_question, db_context):
    return f"""DATABASE CONTEXT:
{db_context or "No relevant incidents found in database."}

USER QUESTION:
{user_question}

Answer only from the context. If information is unavailable, say so.
For general safety questions, label the response 'General Safety Guidance'."""
