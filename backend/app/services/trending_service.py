"""Trending topic suggestions for batch video generation."""
import logging
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

CURATED_TOPICS = [
    {"slug": "rlvr-verifiable-rewards", "label": "RLVR — Verifiable Rewards", "category": "AI", "hot": True},
    {"slug": "claude-agent-sdk", "label": "Claude Agent SDK", "category": "AI", "hot": True},
    {"slug": "mcp-security-owasp-top-10", "label": "MCP Security OWASP Top 10", "category": "AI", "hot": True},
    {"slug": "aws-bedrock-agentcore", "label": "AWS Bedrock AgentCore", "category": "Cloud", "hot": True},
    {"slug": "gemini-cli-terminal-ai-agent", "label": "Gemini CLI Terminal Agent", "category": "AI", "hot": True},
    {"slug": "kimi-k2-moonshot-ai", "label": "Kimi K2 Moonshot AI", "category": "AI", "hot": False},
    {"slug": "strands-agents-sdk", "label": "Strands Agents SDK", "category": "AI", "hot": False},
    {"slug": "llms-txt-ai-web-standard", "label": "llms.txt Web Standard", "category": "AI", "hot": False},
    {"slug": "turbopuffer-serverless-vector-db", "label": "Turbopuffer Vector DB", "category": "AI", "hot": False},
    {"slug": "agentic-context-engineering", "label": "Agentic Context Engineering", "category": "AI", "hot": False},
    {"slug": "multimodal-rag", "label": "Multimodal RAG", "category": "AI", "hot": False},
    {"slug": "human-in-the-loop-ai-agents", "label": "Human-in-the-Loop Agents", "category": "AI", "hot": False},
    {"slug": "ai-agent-design-patterns", "label": "AI Agent Design Patterns", "category": "AI", "hot": False},
    {"slug": "vector-database-comparison", "label": "Vector DB Comparison", "category": "AI", "hot": False},
    {"slug": "langchain-llm-framework", "label": "LangChain Framework", "category": "AI", "hot": False},
    {"slug": "function-calling-tool-use", "label": "Function Calling & Tool Use", "category": "AI", "hot": False},
    {"slug": "llm-as-a-judge", "label": "LLM as a Judge", "category": "AI", "hot": False},
    {"slug": "deep-agents-long-horizon", "label": "Deep Long-Horizon Agents", "category": "AI", "hot": False},
    {"slug": "structured-outputs-json-mode", "label": "Structured Outputs JSON Mode", "category": "Dev", "hot": False},
    {"slug": "mixture-of-agents", "label": "Mixture of Agents", "category": "AI", "hot": False},
    {"slug": "self-rag-reflective-retrieval", "label": "Self-RAG Reflective Retrieval", "category": "AI", "hot": False},
    {"slug": "agentic-ai-governance", "label": "Agentic AI Governance", "category": "AI", "hot": False},
    {"slug": "context-rot-llm-context", "label": "Context Rot in LLMs", "category": "AI", "hot": False},
    {"slug": "fastapi-genai-apps", "label": "FastAPI for GenAI Apps", "category": "Dev", "hot": False},
    {"slug": "react-reasoning-acting-agents", "label": "ReAct Reasoning Agents", "category": "AI", "hot": False},
    {"slug": "rag-fusion-query-expansion", "label": "RAG Fusion & Query Expansion", "category": "AI", "hot": False},
    {"slug": "ai-red-teaming", "label": "AI Red Teaming", "category": "Security", "hot": False},
    {"slug": "n8n-ai-workflow-automation", "label": "n8n AI Workflow Automation", "category": "Tools", "hot": False},
    {"slug": "devin-ai-software-engineer", "label": "Devin AI Software Engineer", "category": "AI", "hot": False},
    {"slug": "why-ai-agents-fail", "label": "Why AI Agents Fail", "category": "AI", "hot": False},
]

CATEGORY_MAP = {
    "AI": ["AI", "Dev", "Security", "Tools"],
    "Finance": ["Finance"],
    "Health": ["Health"],
    "Business": ["Business", "Tools"],
    "Science": ["Science", "AI"],
}


async def get_trending_suggestions(category: str = "AI") -> list[dict]:
    """Return trending topic suggestions for the given category."""
    allowed = CATEGORY_MAP.get(category, ["AI"])
    filtered = [t for t in CURATED_TOPICS if t["category"] in allowed]

    if not filtered:
        filtered = CURATED_TOPICS[:10]

    # Try to enrich with GPT-4o generated extras
    try:
        from app.config import settings
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
        )
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{
                "role": "user",
                "content": (
                    f"List 3 trending {category} topics in tech/AI as of mid-2026 that educators should cover. "
                    f"Return ONLY a JSON array: [{{\"slug\": \"kebab-case\", \"label\": \"Human Readable\", \"category\": \"{category}\", \"hot\": true}}]. "
                    f"JSON only, no explanation."
                )
            }],
            temperature=0.7,
            max_tokens=200,
        )
        import json, re
        text = response.choices[0].message.content.strip()
        text = re.sub(r"```json|```", "", text).strip()
        extras = json.loads(text)
        filtered = extras + filtered
    except Exception as e:
        logger.debug("GPT trending enrichment skipped: %s", e)

    seen = set()
    result = []
    for t in filtered:
        if t["slug"] not in seen:
            seen.add(t["slug"])
            result.append(t)

    return result[:12]
