from flask import Flask, request, render_template
import argparse
import shlex
import subprocess
import sys
import logging
import script

app = Flask(__name__)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The command to be executed.
# We will run script.py with the Python interpreter.
# COMMAND_TO_RUN = [sys.executable, "script.py"]
COMMAND_TO_RUN = ["python3", "script.py"]

# UI Configuration
UI_CONFIG = {
    "input_row_max_width": "500px",
}

# Define the arguments that script.py's argparse parser will accept.
# This structure will be used to dynamically generate input fields.
parser = script.create_parser()
arg_type_map = {
    argparse._StoreAction: "text",
    argparse._StoreTrueAction: "checkbox",
}
SCRIPT_ARGUMENTS = [
    {
        "name": ", ".join(a.option_strings),
        "dest": a.dest,
        "label": a.help,
        "type": arg_type_map.get(type(a)),
        "options": a.choices,
        "placeholder": "" if a.default is None else "e.g., " + f"{a.default}",
        "default": a.default,
    }
    for a in parser._actions
    if not isinstance(a, argparse._HelpAction)
]


@app.route("/")
def index():
    return render_template(
        "index.html",
        command=COMMAND_TO_RUN,
        script_arguments=SCRIPT_ARGUMENTS,
        ui=UI_CONFIG,
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
            arg_dest = arg_def["dest"]
            arg_type = arg_def["type"]
            form_value = request.form.get(arg_dest)
            if form_value == "" or form_value is None:
                continue
            final_command_args.append("--" + arg_dest)
            if arg_type == "text":
                final_command_args.append(form_value)

        logger.error(final_command_args)
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

    return render_template(
        "index.html",
        command=COMMAND_TO_RUN,
        script_arguments=SCRIPT_ARGUMENTS,
        ui=UI_CONFIG,
        output=output,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
