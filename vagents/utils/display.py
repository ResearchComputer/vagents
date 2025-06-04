from rich.console import Console
from rich.markdown import Markdown

def pprint_markdown(text: str):
    console = Console()
    md = Markdown(text)
    console.print(md, soft_wrap=True, markup=True, highlight=False)