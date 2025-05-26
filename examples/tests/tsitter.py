import inspect
import textwrap
import tree_sitter_python as tspython
from vagents.contrib import AgentChat
from tree_sitter import Language, Parser, Tree, Node
from typing import Generator

PY_LANGUAGE: Language = Language(tspython.language())
parser: Parser = Parser(PY_LANGUAGE)

func: str = inspect.getsource(AgentChat.forward)
func: str = textwrap.dedent(func)

tree: Tree = parser.parse(bytes(func, "utf8"))

def traverse_tree(tree: Tree) -> Generator[Node, None, None]:
    cursor = tree.walk()

    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent():
            break

node_names = map(lambda node: node.type, traverse_tree(tree))

print(node_names)