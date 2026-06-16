"""Model layer — LangChain ChatOpenAI, the ONLY module that calls the model.

Lazily constructs the chat model so importing the package never requires a key
(mock mode imports this module but never calls chat()). The `chat()` signature is
unchanged from the raw-SDK version, so agents/actions.py is provider-agnostic.
"""
from ..config import config

_models: dict[bool, object] = {}


def _model(json_mode: bool):
    if json_mode not in _models:
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": config.openai_model,
            "api_key": config.openai_api_key,
            # Bound every request so a stalled call can never freeze the game.
            "timeout": 20,
            "max_retries": 1,
        }
        if json_mode:
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        _models[json_mode] = ChatOpenAI(**kwargs)
    return _models[json_mode]


def chat(prompt: str, max_tokens: int = 220, json_mode: bool = False) -> str:
    from langchain_core.messages import HumanMessage

    model = _model(json_mode).bind(max_tokens=max_tokens)
    resp = model.invoke([HumanMessage(content=prompt)])
    content = resp.content
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(str(c) for c in content)
    return (content or "").strip()
