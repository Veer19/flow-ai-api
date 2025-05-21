# app/agents/prompt_engine.py

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import os

# You can also make this dynamic later based on config
TEMPLATE_DIR = Path(__file__).parent.parent / "prompts"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(disabled_extensions=('jinja',))  # disable escaping
)

def render_prompt(template_name: str, context: dict = {}) -> str:
    """
    Renders a Jinja2 template with the given context dictionary.
    
    Args:
        template_name (str): Name of the .jinja template file (e.g. 'intent_analysis_v3.jinja')
        context (dict): Dictionary with keys used in the Jinja template
    
    Returns:
        str: Rendered prompt string
    """
    template = env.get_template(template_name)
    return template.render(**context)
