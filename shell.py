import sys
import os
import shlex
import subprocess
import readline
import re

SHELL_BUILTIN = ["echo", "exit", "type", "history", "pwd", "cd"]
PATH = os.getenv("PATH", "")
paths = PATH.split(":")
history_list = []
last_prefix = ""
tab_press_count = 0
current_matches = []
history_last_written_index = 0
HISTFILE = os.getenv("HISTFILE")
if HISTFILE and os.path.isfile(HISTFILE):
    try:
        with open(HISTFILE, "r") as f:
            for line in f:
                history_list.append(line.rstrip("\n"))
        history_last_written_index = len(history_list)
    except Exception:
        pass


def save_history_and_exit(args=None):
    try:
        with open(HISTFILE, "a") as f:
            to_append = history_list[history_last_written_index:]
            for entry in to_append:
                f.write(entry + "\n")
    except Exception:
        pass
    code = int(args[0]) if args else 0
    sys.exit(code)


def parse_redirection(args):
    stdout_file = stderr_file = None
    stdout_append = stderr_append = False
    i = 0
    while i < len(args):
        if args[i] in (">", "1>"):
            stdout_file = args[i + 1]
            del args[i:i+2]
        elif args[i] in (">>", "1>>"):
            stdout_file = args[i + 1]
            stdout_append = True
            del args[i:i+2]
        elif args[i] == "2>":
            stderr_file = args[i + 1]
            del args[i:i+2]
        elif args[i] == "2>>":
            stderr_file = args[i + 1]
            stderr_append = True
            del args[i:i+2]
        else:
            i += 1
    return stdout_file, stdout_append, stderr_file, stderr_append


def find_exec(cmd):
    for path in paths:
        full_path = f"{path}/{cmd}"
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def collapse_spaces(arg):
    return re.sub(r"\s+", " ", arg)


def list_executables(prefix=""):
    executables = set()
    for path in paths:
        if not os.path.isdir(path):
            continue
        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.access(full_path, os.X_OK) and entry.startswith(prefix):
                    executables.add(entry)
        except PermissionError:
            continue
    return sorted(executables)


def auto_complete(text, state):
    global last_prefix, tab_press_count, current_matches
    if text != last_prefix:
        last_prefix = text
        tab_press_count = 0
        current_matches = []
    if state == 0:
        matches = [cmd for cmd in SHELL_BUILTIN if cmd.startswith(text)]
        matches += list_executables(text)
        current_matches = sorted(matches)
        if len(current_matches) > 1:
            tab_press_count += 1
            if tab_press_count == 1:
                print("\a", end="", flush=True)
            elif tab_press_count == 2:
                print("\n" + "  ".join(current_matches))
                sys.stdout.write("$ " + text)
                sys.stdout.flush()
    if state < len(current_matches):
        return current_matches[state] + " "
    return None


def run_builtins(cmd, args):
    global history_last_written_index
    if cmd == "echo":
        return " ".join(args) + "\n"
    elif cmd == "cd":
        if not args:
            return ""
        target_dir = args[0]
        if target_dir == "~":
            target_dir = os.path.expanduser("~")
        try:
            os.chdir(target_dir)
        except FileNotFoundError:
            return f"cd: {target_dir}: No such file or directory\n"
        except NotADirectoryError:
            return f"cd: {target_dir}: Not a directory\n"
        except PermissionError:
            return f"cd: {target_dir}: Permission denied\n"
        return ""

    elif cmd == "type":
        if not args:
            return ""
        target = args[0]
        if target in SHELL_BUILTIN:
            return f"{target} is a shell builtin\n"
        elif find_exec(target):
            return f"{target} is {find_exec(target)}\n"
        else:
            return f"{target}: not found\n"
    elif cmd == "pwd":
        return os.getcwd()+"\n"
    elif cmd == "history":
        output = ""
        if args:
            if args[0] == "-r":
                if len(args) < 2:
                    return "history missing file argument"
                file_path = args[1]
                try:
                    with open(file_path, "r") as f:
                        for line in f:
                            line = line.rstrip("\n")
                            history_list.append(line)
                except FileNotFoundError:
                    return f"history:{file_path}: No such file\n"
                return ""
            elif args[0] == "-w":
                if len(args) < 2:
                    return "history:missing file argument for -w\n"
                file_path = args[1]
                try:
                    with open(file_path, "w") as f:
                        for entry in history_list:
                            f.write(entry+"\n")
                except Exception as e:
                    return f"history: {file_path}: cannot write file({e})\n"
                return ""
            elif args[0] == "-a":
                if len(args) < 2:
                    return f"history:missing file argument for -a\n"
                file_path = args[1]
                try:
                    to_append = history_list[history_last_written_index:]
                    with open(file_path, "a") as f:
                        for entry in to_append:
                            f.write(entry+"\n")
                        history_last_written_index = len(history_list)
                except Exception as e:
                    return f"history:{file_path}: cannot append to file ({e})\n"
                return ""

        n = None
        if args:
            try:
                n = int(args[0])
            except ValueError:
                pass
        history_to_show = history_list[-n:] if n else history_list
        for i, entry in enumerate(history_to_show, start=len(history_list)-len(history_to_show)+1):
            output += f"{i} {entry}\n"
        return output
    return ""


def run_pipeline(commands):
    processes = []
    prev_stdout = None
    num_cmds = len(commands)
    for i, parts in enumerate(commands):
        if not parts:
            continue
        stdout_file = stderr_file = None
        stdout_append = stderr_append = False
        if i == num_cmds - 1:
            stdout_file, stdout_append, stderr_file, stderr_append = parse_redirection(
                parts)
        cmd = parts[0]
        args = parts[1:]
        is_builtin = cmd in SHELL_BUILTIN
        if is_builtin:
            output = run_builtins(cmd, args)
            if i == num_cmds - 1:
                if stdout_file:
                    mode = "a" if stdout_append else "w"
                    with open(stdout_file, mode) as f:
                        f.write(output)
                else:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                if stderr_file:
                    mode = "a" if stderr_append else "w"
                    open(stderr_file, mode).close()
                prev_stdout = None
            else:
                r, w = os.pipe()
                os.write(w, output.encode())
                os.close(w)
                prev_stdout = os.fdopen(r)
            continue
        exe_path = find_exec(cmd)
        if not exe_path:
            print(f"{cmd}: command not found")
            return
        stdout = subprocess.PIPE if i < num_cmds - \
            1 else (open(stdout_file, "a" if stdout_append else "w") if stdout_file else None)
        stderr = open(
            stderr_file, "a" if stderr_append else "w") if stderr_file else None
        p = subprocess.Popen([cmd] + args, stdin=prev_stdout,
                             stdout=stdout, stderr=stderr, text=True)
        if prev_stdout and prev_stdout not in (subprocess.PIPE, sys.stdin):
            prev_stdout.close()
        prev_stdout = p.stdout
        processes.append((p, stdout, stderr))
    for p, stdout, stderr in processes:
        p.wait()
        if stdout not in (None, subprocess.PIPE):
            stdout.close()
        if stderr not in (None, subprocess.PIPE):
            stderr.close()


def main():
    readline.set_completer(auto_complete)
    readline.parse_and_bind("tab: complete")
    try:
        command = input("$ ").strip()
    except EOFError:
        sys.exit(0)
    if not command:
        return
    history_list.append(command)
    try:
        lexer = shlex.shlex(command, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        parts = list(lexer)
    except ValueError as e:
        print(f"Error parsing command: {e}")
        return
    if not parts:
        return
    if "|" in parts:
        pipeline = []
        current_cmd = []
        for part in parts:
            if part == "|":
                pipeline.append(current_cmd)
                current_cmd = []
            else:
                current_cmd.append(part)
        pipeline.append(current_cmd)
        run_pipeline(pipeline)
        return
    stdout_file, stdout_append, stderr_file, stderr_append = parse_redirection(
        parts)
    if not parts:
        return
    cmd = parts[0]
    args = parts[1:]
    if cmd == "exit":
        save_history_and_exit(args)
    elif cmd in SHELL_BUILTIN:
        output = run_builtins(cmd, args)
        if output:
            if stdout_file:
                mode = "a" if stdout_append else "w"
                with open(stdout_file, mode) as f:
                    f.write(output)
            else:
                sys.stdout.write(output)
                sys.stdout.flush()
        if stderr_file:
            mode = "a" if stderr_append else "w"
            open(stderr_file, mode).close()
        return
    exe_path = find_exec(cmd)
    if not exe_path:
        print(f"{cmd}: command not found")
        return
    stdout_handle = open(
        stdout_file, "a" if stdout_append else "w") if stdout_file else None
    stderr_handle = open(
        stderr_file, "a" if stderr_append else "w") if stderr_file else None
    try:
        p = subprocess.Popen([cmd] + args, executable=exe_path, stdout=stdout_handle if stdout_handle else None,
                             stderr=stderr_handle if stderr_handle else None, text=True)
        p.wait()
    finally:
        if stdout_handle:
            stdout_handle.close()
        if stderr_handle:
            stderr_handle.close()


if __name__ == "_main_":
    while True:
        main()
