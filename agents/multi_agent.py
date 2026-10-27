import json
from agents.single_agent import client, MODEL, TOOLS, TOOL_FUNCTIONS
from tools import list_files

# 🗺️ Planner: makes the plan, does not solve
PLANNER_PROMPT = ("You are a planner. Do NOT solve the task and do NOT give the answer. "
                  "Look at the task and the list of available files. "
                  "Write a short numbered plan (3 to 5 steps) saying which files to read and what to calculate. "
                  "If you are not sure which file has the information, plan to read every file.")

# 👷 Worker: follows the plan using tools
WORKER_PROMPT = ("You are a careful office worker. Follow the plan step by step using the tools. "
                 "Always use the calculator for math. Give a short final answer.")

# 🔍 Checker: reviews the worker's work, cannot open files
CHECKER_PROMPT = ("You are a reviewer. You cannot open files, but you can see what the worker's tools returned. "
                  "Use those tool results to check if the worker's answer is correct and complete. "
                  "If the worker said information is missing but did not read all the files, that is a mistake. "
                  "If the tool results support the answer, reply with exactly: OK. "
                  "Otherwise, explain the problem in one or two sentences.")


def call_model(system, user, use_tools=False, max_steps=8, verbose=True):
    """Call GPT with a job description. If use_tools=True, it can use tools in a loop."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    tokens, trace = 0, []
    for step in range(max_steps):
        if use_tools:
            response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        else:
            response = client.chat.completions.create(model=MODEL, messages=messages)
        tokens += response.usage.total_tokens
        msg = response.choices[0].message
        if not msg.tool_calls:
            return msg.content, tokens, trace, step + 1
        messages.append(msg)
        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            result = TOOL_FUNCTIONS[name](**args)
            trace.append(f"{name}({args}) returned:\n{result}")
            if verbose:
                print(f"     🔧 {name}({args})")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return "Stopped: too many steps", tokens, trace, max_steps


def run_multi_agent(task, max_retries=3, verbose=True):
    total_tokens, total_steps = 0, 0

    # 1. Planner makes the plan
    plan, t, _, s = call_model(PLANNER_PROMPT, f"Task: {task}\nAvailable files: {list_files()}")
    total_tokens += t; total_steps += s
    if verbose:
        print(f"  🗺️ Plan:\n{plan}\n")

    feedback = ""
    for attempt in range(max_retries + 1):
        # 2. Worker follows the plan with tools
        answer, t, trace, s = call_model(WORKER_PROMPT, f"Task: {task}\nPlan:\n{plan}\n{feedback}",
                                         use_tools=True, verbose=verbose)
        total_tokens += t; total_steps += s
        if verbose:
            print(f"  👷 Worker answer: {answer}")

        # 3. Checker reviews the answer
        check_input = (f"Task: {task}\nAvailable files: {list_files()}\n"
                       f"Tools the worker used:\n" + "\n\n".join(trace) +
                       f"\n\nWorker's answer: {answer}")
        verdict, t, _, s = call_model(CHECKER_PROMPT, check_input)
        total_tokens += t; total_steps += s
        if verbose:
            print(f"  🔍 Checker: {verdict}\n")

        clean_verdict = verdict.strip().rstrip(".").upper()
        if clean_verdict.startswith("OK") or clean_verdict.endswith("OK"):
            break
        feedback = f"A reviewer found a problem with your last answer: {verdict}\nPlease fix it."

    return {"answer": answer, "steps": total_steps, "tokens": total_tokens}
