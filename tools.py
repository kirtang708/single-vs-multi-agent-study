import os
import ast
import operator

DATA_DIR = "data"

def read_file(filename: str) -> str:
    """Return the contents of a file in the data folder."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return f"Error: file '{filename}' not found."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def list_files() -> str:
    """List all files in the data folder."""
    return ", ".join(os.listdir(DATA_DIR))

# Safe calculator: only allows numbers and + - * / ( )
OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
       ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.USub: operator.neg}

def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")

def calculator(expression: str) -> str:
    """Calculate a math expression like '(40000-32000)/32000*100'."""
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as e:
        return f"Error: {e}"
