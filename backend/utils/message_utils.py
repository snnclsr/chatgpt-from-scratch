from typing import List, Dict, Any
from itertools import groupby


def fix_gemma_messages(messages: List[Dict[str, Any]]):
    """Fix the Gemma messages to alternate user/assistant/user/assistant/"""
    grouped = []
    for role, group in groupby(messages, key=lambda x: x["role"]):
        contents = [msg["content"] for msg in group]
        merged = "\n".join(contents)
        grouped.append({"role": role, "content": merged})
    return grouped
