from flask import Flask, request, render_template_string
import argparse
import shlex
import subprocess
import sys
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The command to be executed.
# We will run script.py with the Python interpreter.
# COMMAND_TO_RUN = [sys.executable, "script.py"]
COMMAND_TO_RUN = ["python3", "script.py"]

# Define the arguments that script.py's argparse parser will accept.
# This structure will be used to dynamically generate input fields.
SCRIPT_ARGUMENTS = [
    {
        "name": "--url",
        "label": "Instagram URL",
        "type": "text",
        "placeholder": "e.g., https://www.instagram.com/p/CODE/",
    },
    {
        "name": "--story",
        "label": "Story Link",
        "type": "text",
        "placeholder": "e.g., https://www.instagram.com/stories/USERNAME/PK/",
    },
    {
        "name": "--input",
        "label": "Input File (URLs)",
        "type": "text",
        "placeholder": "e.g., urls.txt (file with one URL per line)",
    },
    {
        "name": "--output",
        "label": "Output Directory",
        "type": "text",
        "default": "downloads",
        "placeholder": "e.g., downloads",
    },
    {
        "name": "--login",
        "label": "Login Session ID",
        "type": "text",
        "placeholder": "Your Instagram session ID",
    },
    {
        "name": "--collection",
        "label": "Collection Name",
        "type": "text",
        "placeholder": "Name of a saved collection",
    },
    {
        "name": "--unsave",
        "label": "Unsave Media After Download",
        "type": "checkbox",
    },
    {
        "name": "--download_links",
        "label": "Download Links to File",
        "type": "text",
        "placeholder": "e.g., links.txt",
    },
    {
        "name": "--log_level",
        "label": "Logging Level",
        "type": "select",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "default": "INFO",
    },
]

# calc(100% - 20px)
# HTML template string
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Command Runner</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f9f9f9; color: #333;}
        h1 { color: #0056b3; }
        form { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; }
        textarea { width: 500px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 14px; resize: vertical; }
        button { padding: 10px 15px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; transition: background-color 0.2s ease; }
        button:hover { background-color: #218838; }
        pre { background-color: #e9ecef; padding: 15px; border: 1px solid #ddd; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-size: 13px; }
        .output-section { margin-top: 20px; }
        .error { color: #dc3545; font-weight: bold; }
        .command-info { font-size: 0.9em; color: #666; margin-bottom: 15px; }
        .input-group { margin-bottom: 15px; }
        .input-group label { margin-bottom: 5px; }
        .input-group textarea { height: 90px; width: 300px;}
        .user-input{ width: 500px;}
    </style>
</head>
<body>
    <h1>Command Executor</h1>
    <div class="command-info">
        Running command: <code>{{ command }}</code>
    </div>
    <form method="post" action="/run">
        {% for arg in script_arguments %}
            <div class="input-group">
                <label for="{{ arg.name }}">{{ arg.label }}:</label>
                {% if arg.type == 'text' %}
                    <input class="user-input" type="search" id="{{ arg.name }}" name="{{ arg.name }}"
                           value="{{ request.form.get(arg.name, arg.default if arg.default is not none else '') }}" 
                           placeholder="{{ arg.placeholder or '' }}">
                {% elif arg.type == 'checkbox' %}
                    <input type="checkbox" id="{{ arg.name }}" name="{{ arg.name }}" 
                           {% if request.form.get(arg.name) == 'on' or (arg.default and request.form.get(arg.name) is none) %}checked{% endif %}>
                {% elif arg.type == 'select' %}
                    <select id="{{ arg.name }}" name="{{ arg.name }}">
                        {% for option in arg.options %}
                            <option value="{{ option }}" 
                                    {% if request.form.get(arg.name, arg.default) == option %}selected{% endif %}>
                                {{ option }}
                            </option>
                        {% endfor %}
                    </select>
                {% endif %}
            </div>
        {% endfor %}
        <br>
        <button type="submit">Run Command</button>
    </form>

    {% if output %}
        <div class="output-section">
            <h2>Output:</h2>
            <pre>{{ output }}</pre>
        </div>
    {% endif %}
    {% if error %}
        <div class="output-section">
            <h2>Error:</h2>
            <pre class="error">{{ error }}</pre>
        </div>
    {% endif %}
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        command=COMMAND_TO_RUN,
        script_arguments=SCRIPT_ARGUMENTS,
        output=None,
        error=None,
    )


@app.route("/run", methods=["POST"])
def run_command():
    output = None
    error = None
    final_command_args = list(COMMAND_TO_RUN)  # Start with 'python script.py'

    try:
        for arg_def in SCRIPT_ARGUMENTS:
            arg_name = arg_def["name"]
            arg_type = arg_def["type"]
            form_value = request.form.get(arg_name)

            if arg_type == "search":
                if form_value:
                    final_command_args.append(arg_name)
                    final_command_args.append(form_value)
            elif arg_type == "checkbox":
                if form_value == "on":  # Checkboxes send 'on' if checked
                    final_command_args.append(arg_name)
            elif arg_type == "select":
                if form_value and form_value != arg_def.get("default"):
                    final_command_args.append(arg_name)
                    final_command_args.append(form_value)
                elif (
                    form_value and arg_name == "--log_level"
                ):  # Always pass log_level if it has a value
                    final_command_args.append(arg_name)
                    final_command_args.append(form_value)

        result = subprocess.run(
            final_command_args, capture_output=True, text=True, check=False
        )

        if result.stdout:
            output = result.stdout.strip()
        if result.stderr:
            error = result.stderr.strip()

        if result.returncode != 0 and not error:
            error = f"Command failed with exit code {result.returncode}"

    except Exception as e:
        error = f"An unexpected error occurred: {e}"

    return render_template_string(
        HTML_TEMPLATE,
        command=COMMAND_TO_RUN,
        script_arguments=SCRIPT_ARGUMENTS,
        output=output,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
