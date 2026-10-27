import json
from agents.single_agent import client, MODEL, TOOLS, TOOL_FUNCTIONS

# Same as the original single agent, plus the Planner's rule (last sentence)
SYSTEM = ("You are a helpful office assistant. Use the tools to read files and do math. "
          "Always use the calculator for math. Give a short final answer. "
          "If you are not sure which file has the information, read every file.")

def run_single_agent_rule(task, max_steps=8, verbose=True):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    total_tokens = 0
    for step in range(max_steps):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        total_tokens += response.usage.total_tokens
        msg = response.choices[0].message
        if not msg.tool_calls:
            return {"answer": msg.content, "steps": step + 1, "tokens": total_tokens}
        messages.append(msg)
        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            result = TOOL_FUNCTIONS[name](**args)
            if verbose:
                print(f"  🔧 {name}({args}) → {result[:60]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return {"answer": "Stopped: too many steps", "steps": max_steps, "tokens": total_tokens}
