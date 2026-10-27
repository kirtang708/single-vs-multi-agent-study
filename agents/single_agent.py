import json
from dotenv import load_dotenv
from openai import OpenAI
from tools import read_file, list_files, calculator

load_dotenv()
client = OpenAI()
MODEL = "gpt-4o-mini"

# 1. Describe the tools so GPT knows what it can use
TOOLS = [
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List all files in the data folder.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read the full contents of a file in the data folder.",
        "parameters": {"type": "object",
                       "properties": {"filename": {"type": "string", "description": "File name, like sales.csv"}},
                       "required": ["filename"]}}},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "Calculate a math expression using + - * / and parentheses, like (40000-32000)/32000*100",
        "parameters": {"type": "object",
                       "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
]

# 2. Connect each tool name to the real Python function
TOOL_FUNCTIONS = {"list_files": list_files, "read_file": read_file, "calculator": calculator}

# 3. Instructions for the agent
SYSTEM = ("You are a careful office assistant. Use the tools to read files and do math. "
          "Before saying information is missing, check every file. "
          "Always use the calculator for math. Give a short final answer.")
# 4. The agent loop
def run_single_agent(task, max_steps=8, verbose=True):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    total_tokens = 0

    for step in range(max_steps):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        total_tokens += response.usage.total_tokens
        msg = response.choices[0].message

        # No tool needed → this is the final answer
        if not msg.tool_calls:
            return {"answer": msg.content, "steps": step + 1, "tokens": total_tokens}

        # GPT wants tools → run them and send results back
        messages.append(msg)
        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            result = TOOL_FUNCTIONS[name](**args)
            if verbose:
                print(f"  🔧 {name}({args}) → {result[:60]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return {"answer": "Stopped: too many steps", "steps": max_steps, "tokens": total_tokens}
