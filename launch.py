import argparse
import ast
import operator
import re
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SKILLS = ("track_face", "track_person", "detect_objects", "nod_yes", "shake_no")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Chat with your robot.")
    parser.add_argument("skill", nargs="?", help="A skill name or a quoted prompt")
    return parser.parse_args(argv)


def say(name, message):
    colors = {"Robot": "36", "Skills": "35", "Done": "32", "Error": "31"}
    label = f"\033[{colors.get(name, '36')}m{name}\033[0m" if sys.stdout.isatty() else name
    print(f"\n  {label} > {message}", flush=True)


def start_model():
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
            return
    except URLError:
        pass
    project_dir = Path(__file__).resolve().parent
    ollama = project_dir / "deps" / "ollama" / "ollama.exe"
    if not ollama.is_file():
        raise ValueError("Ollama is missing. Install Ollama and run: ollama pull llama3.2:1b")
    environment = os.environ.copy()
    environment["USERPROFILE"] = str(project_dir / "deps" / "ollama")
    environment["OLLAMA_MODELS"] = str(project_dir / "models" / "ollama")
    environment["OLLAMA_HOST"] = "127.0.0.1:11434"
    environment["OLLAMA_NO_CLOUD"] = "1"
    subprocess.Popen([str(ollama), "serve"], env=environment,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(30):
        time.sleep(0.5)
        try:
            with urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
                return
        except URLError:
            pass
    raise ValueError("Ollama did not start. Try launching ollama serve manually.")


def get_math(prompt):
    expression = prompt.lower().strip().rstrip("?.!")
    expression = re.sub(r"^(is it true that|is|does)\s+", "", expression)
    for word, symbol in (("multiplied by", "*"), ("divided by", "/"),
                         ("greater than", ">"), ("less than", "<"),
                         ("equal to", "=="), ("equals", "=="), ("equal", "=="),
                         ("plus", "+"), ("minus", "-"), ("times", "*")):
        expression = expression.replace(word, symbol)
    expression = expression.replace("\u00d7", "*").replace("\u00f7", "/")
    expression = re.sub(r"(?<![<>=!])=(?!=)", "==", expression)
    if len(expression) > 150 or not re.fullmatch(r"[\d\s.+*/%()<>=!-]+", expression):
        return None
    operations = {ast.Add: operator.add, ast.Sub: operator.sub,
                  ast.Mult: operator.mul, ast.Div: operator.truediv,
                  ast.Mod: operator.mod, ast.Eq: operator.eq,
                  ast.NotEq: operator.ne, ast.Lt: operator.lt,
                  ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}

    def calculate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = calculate(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](calculate(node.left), calculate(node.right))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in operations:
            return operations[type(node.ops[0])](calculate(node.left), calculate(node.comparators[0]))
        raise ValueError("Unsupported calculation")

    try:
        node = ast.parse(expression, mode="eval").body
        if not isinstance(node, ast.Compare):
            return None
        answer = calculate(node)
        return {"response": "Yes." if answer else "No.",
                "skills": ["nod_yes" if answer else "shake_no"]}
    except (SyntaxError, ValueError, ArithmeticError, RecursionError):
        return {"response": "I cannot verify that calculation.", "skills": []}


def get_response(prompt, history=None):
    if prompt in SKILLS:
        return {"response": f"I'll run {prompt.replace('_', ' ')}.", "skills": [prompt]}

    result = get_math(prompt)
    if result is not None:
        return result
    command = re.sub(r"[^a-z ]", "", prompt.lower()).strip()
    command = re.sub(r"^(please |can you |could you )+", "", command)
    command = re.sub(r" please$", "", command)
    if command in ("look at me", "look at my face"):
        skill = "track_face" if "face" in command else "track_person"
        return {"response": "I'll look at your face." if "face" in command else "I'll look at you.",
                "skills": [skill]}

    start_model()
    instructions = (
        "You are a sarcastic but direct robot assistant. Return JSON: response (short reply), "
        "skills (list). For yes/no questions, answer Yes or No and use nod_yes for Yes, "
        "shake_no for No. This includes factual and math questions. If uncertain, say so "
        "and return no skills. Open-ended questions and greetings need no skills. "
        "Only act on the latest message. Look at me means track_person. "
        "Look at my face means track_face. "
        "Allowed skills: track_face, track_person, detect_objects, nod_yes, shake_no. "
        "For object identification requests use detect_objects; do not guess the object. "
        "Repeat actions when requested, preserving order. Explain unsupported requests "
        "with skills []. You cannot wave, run timed actions, or run actions simultaneously. "
        "Tracking stops when the user presses Q. Describe plans, not completed actions."
    )
    examples = [
        {'role': 'user', 'content': 'Hello!'},
        {'role': 'assistant', 'content': '{"response": "Sup man!", "skills": []}'},
        {'role': 'user', 'content': 'Nod twice then shake your head'},
        {'role': 'assistant', 'content': '{"response": "Two nods and a shake. Coming up.", "skills": ["nod_yes", "nod_yes", "shake_no"]}'},
        {'role': 'user', 'content': 'What can you do?'},
        {'role': 'assistant', 'content': '{"response": "Track faces or people, detect objects, nod, and shake my head.", "skills": []}'},
        {'role': 'user', 'content': 'Track my face'},
        {'role': 'assistant', 'content': '{"response": "I will follow your face. Press Q to stop.", "skills": ["track_face"]}'},
        {'role': 'user', 'content': 'Follow that person'},
        {'role': 'assistant', 'content': '{"response": "I will track the person. Press Q to stop.", "skills": ["track_person"]}'},
        {'role': 'user', 'content': 'What is this object?'},
        {'role': 'assistant', 'content': '{"response": "I will check what the camera detects.", "skills": ["detect_objects"]}'},
        {'role': 'user', 'content': 'Please nod'},
        {'role': 'assistant', 'content': '{"response": "One nod, coming up.", "skills": ["nod_yes"]}'},
        {'role': 'user', 'content': 'Shake your head'},
        {'role': 'assistant', 'content': '{"response": "One head shake, coming up.", "skills": ["shake_no"]}'},
        {'role': 'user', 'content': 'Wave your left hand'},
        {'role': 'assistant', 'content': '{"response": "Waving is not available. My talents are limited.", "skills": []}'},
        {'role': 'user', 'content': 'Track me for five seconds'},
        {'role': 'assistant', 'content': '{"response": "Timed tracking is unsupported. You can stop tracking with Q.", "skills": []}'},
    ]
    for question, response, skills in (
        ("Is 2 + 2 = 4?", "Yes.", ["nod_yes"]),
        ("Is 3 times 3 equal to 8?", "No.", ["shake_no"]),
        ("Is Paris the capital of France?", "Yes.", ["nod_yes"]),
        ("Are cats reptiles?", "No.", ["shake_no"]),
        ("Look at me", "I will look at you.", ["track_person"]),
        ("Look at my face", "I will look at your face.", ["track_face"]),
    ):
        examples.extend([{"role": "user", "content": question},
                         {"role": "assistant", "content": json.dumps({"response": response, "skills": skills})}])
    data = {
        "model": "llama3.2:1b",
        "messages": [{"role": "system", "content": instructions}, *examples,
                     *(history or [])[-10:], {"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": "5m",
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 256},
        "format": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "skills": {"type": "array", "maxItems": 20,
                           "items": {"type": "string", "enum": list(SKILLS)}},
            },
            "required": ["response", "skills"],
            "additionalProperties": False,
        },
    }
    request = Request("http://127.0.0.1:11434/api/chat",
                      data=json.dumps(data).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=180) as response:
            answer = json.load(response)
    except HTTPError as exc:
        raise ValueError(f"Ollama: {exc.read().decode()}") from exc
    except URLError as exc:
        raise ValueError("Cannot reach the local Ollama server.") from exc
    if answer.get("done_reason") == "length":
        raise ValueError("The reply was too long. Try a shorter request.")
    result = json.loads(answer["message"]["content"])
    if (not isinstance(result, dict) or not isinstance(result.get("response"), str)
            or not isinstance(result.get("skills"), list)
            or len(result["skills"]) > 20
            or any(skill not in SKILLS for skill in result["skills"])):
        raise ValueError("The model returned an invalid skill sequence. Please rephrase.")
    if re.match(r"^(what|why|how|when|where|who)\b", prompt.strip(), re.IGNORECASE) and all(
            skill in ("nod_yes", "shake_no") for skill in result["skills"]):
        result["skills"] = []
    answer = re.match(r"^(yes|no)\b", result["response"].strip(), re.IGNORECASE)
    if answer and all(skill in ("nod_yes", "shake_no") for skill in result["skills"]):
        result["skills"] = ["nod_yes" if answer[1].lower() == "yes" else "shake_no"]
    return result


def get_skills(prompt):
    return get_response(prompt)["skills"]


def run(skill, history=None):
    result = get_response(skill, history)
    say("Robot", result["response"])
    if history is not None:
        history.extend([
            {"role": "user", "content": skill},
            {"role": "assistant", "content": result["response"]},
        ])
    if not result["skills"]:
        return

    from classes import Robot

    say("Skills", " -> ".join(result["skills"]))
    status = "Execution stopped before all skills finished."
    try:
        robot = Robot()
        for skill in result["skills"]:
            if skill in ("track_face", "track_person"):
                say("Robot", "Press Q in the camera window to finish tracking and continue.")
            value = getattr(robot, skill)()
            say("Done", f"{skill}: {value}" if value is not None else skill)
        status = "All requested skill calls finished."
    finally:
        if history is not None:
            history[-1]["content"] += f"\nExecution status: {status}"


def main():
    args = parse_args()
    project_dir = Path(__file__).resolve().parent
    python = project_dir / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        print(f"Project Python environment not found: {python}", file=sys.stderr)
        return 1
    if Path(sys.executable).resolve() != python.resolve():
        return subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                               cwd=project_dir)
    if sys.platform == "win32" and sys.stdout.isatty():
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 4)
    print("\n  +--------------------------------------+\n"
          "  |              ROBOT CHAT              |\n"
          "  +--------------------------------------+")
    say("Robot", "sup man, what skill shall i run?")
    history = []
    while True:
        try:
            skill = (args.skill if args.skill is not None else input("  You > ")).strip()
            if not skill:
                if args.skill is not None:
                    return 0
                continue
            if skill.lower() in ("/exit", "exit", "quit"):
                say("Robot", "See you next time!")
                return 0
            if skill == "/skills":
                say("Skills", ", ".join(SKILLS))
            elif skill == "/clear":
                history.clear()
                say("Robot", "Conversation cleared. What shall we do?")
            else:
                say("Robot", "Thinking...")
                run(skill, history)
            if args.skill is not None:
                return 0
        except (KeyboardInterrupt, EOFError):
            say("Robot", "Chat stopped.")
            return 0
        except Exception as exc:
            say("Error", str(exc))
            if args.skill is not None:
                return 1


if __name__ == "__main__":
    raise SystemExit(main())




