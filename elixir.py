import difflib
import fire
import json
import os
import shutil
import subprocess
import sys

import openai
from termcolor import cprint

import logging
logging.basicConfig(filename='logger.log', encoding='utf-8', level=logging.DEBUG)

# OpenAI key
with open("openai_key.txt") as f:
    openai.api_key = f.read().strip()
    #logging.debug(f"open-ai key: {openai.api_key}")

def runner(name, args):
    args = [str(args) for args in args]
    try:
        result = subprocess.check_output(
            [sys.executable, name, *args], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8"), e.returncode    
    return result.decode("utf-8"), 0

def error_sender(path, args, e_msg, model):
    with open(path, "r") as f:
        lines = f.readlines()

    file_lined = []
    for i, line in enumerate(lines):
        file_lined.append(str(i + 1) + ": " + line)
    file_lined = "".join(file_lined)

    with open("base_prompt.txt", "r") as f:
        initial_text = f.read()
    
    prompt = (
        initial_text +
        "\n\n"
        "This is the script you need to fix:\n\n"
        f"{file_lined}\n\n"
        "This are the arguments you need to pass:\n\n"
        f"{args}\n\n"
        "This is the error message:\n\n"
        f"{e_msg}\n\n"
        "Provide a fix for the script and strictly stick to the exact format written above\n\n"
    )

    logging.debug(f"Initial prompt \n {prompt}")

    response = openai.ChatCompletion.create(
        model=model,
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.9,
    )

    logging.debug(f"model response {response}")

    return response.choices[0].message.content.strip()

def fixer(path, changes):
    with open(path, "r") as f:
        original_file_lines = f.readlines()

    changes = json.loads(changes)

    logging.debug(f"suggested change {changes}")

    # Filter out explanation elements
    operation_changes = [change for change in changes if "operation" in change]
    explanations = [
        change["explanation"] for change in changes if "explanation" in change
    ]

    # Sort the changes in reverse line order
    operation_changes.sort(key=lambda x: x["line"], reverse=True)

    file_lines = original_file_lines.copy()
    for change in operation_changes:
        operation = change["operation"]
        line = change["line"]
        content = change["content"]

        if operation == "Replace":
            file_lines[line - 1] = content + "\n"
        elif operation == "Delete":
            del file_lines[line - 1]
        elif operation == "InsertAfter":
            file_lines.insert(line, content + "\n")

    with open(path, "w") as f:
        f.writelines(file_lines)

    # Print explanations
    cprint("Explanations:", "blue")
    for explanation in explanations:
        cprint(f"- {explanation}", "blue")

    # Show the diff
    print("\nChanges:")
    diff = difflib.unified_diff(original_file_lines, file_lines, lineterm="")
    for line in diff:
        if line.startswith("+"):
            cprint(line, "green", end="")
        elif line.startswith("-"):
            cprint(line, "red", end="")
        else:
            print(line, end="")


def main(script_name, *script_args, revert=False, model="gpt-4"):
    if revert:
        backup_file = script_name + ".bak"
        if os.path.exists(backup_file):
            shutil.copy(backup_file, script_name)
            print(f"Reverted to {script_name}")
            logging.debug("reverted to backup file")
            sys.exit(0)
        else:
            print(f"No backup file for {script_name}")
            logging.debug("No backup found")
            sys.exit(1)

    # Make a backup of the original script
    shutil.copy(script_name, script_name + ".bak")

    while True:
        output, returncode = runner(script_name, script_args)

        if returncode == 0:
            cprint("Script ran successfully.", "blue")
            print("Output:", output)
            break
        else:
            cprint("Script crashed. Trying to fix...", "blue")
            print("Output:", output)

            json_response = error_sender(
                    path=script_name,
                    args=script_args,
                    e_msg=output,
                    model=model,
            )
            fixer(script_name, json_response)
            cprint("Changes applied. Re-running...", "blue")


if __name__ == "__main__":
    fire.Fire(main)
