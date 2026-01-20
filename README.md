# 🐚 Mini Python Shell

A Unix-like command-line shell implemented in _Python_, supporting built-in commands,
external program execution, pipelines, redirections, history management, and tab
auto-completion.

This project was built to understand _how real shells work internally_, including
process creation, piping, and command parsing.

---

## ✨ Features

### 🔹 Built-in Commands

- echo
- cd (supports ~)
- pwd
- type
- history (-r, -w, -a)
- exit [code]

### 🔹 Shell Capabilities

- Execute external commands via $PATH
- Pipelines using |
- I/O redirection:
  - > / >> (stdout)
  - 2> / 2>> (stderr)
- Command history with HISTFILE
- Tab auto-completion:
  - Built-in commands
  - Executables in $PATH

---

## 🛠 Technologies Used

- Python 3
- os, sys
- subprocess
- shlex
- readline
- POSIX concepts (pipes, file descriptors)

---

## 🚀 How to Run

```bash
python shell.py
```

You will be presented with a prompt:

```bash
$
```

You can run commands like:

```bash
$ ls | grep py > files.txt
$ echo Hello World
$ cd ~
$ history
```

## 📂 Example Usage

```bash
$ pwd
/home/user

$ echo Hello | wc -c
6

$ ls nonexistent 2> error.txt
```

---

## ⚠️ Limitations

This is a learning project, not a full Bash replacement.

No job control (fg, bg, &)

No environment variable expansion ($VAR)

Limited Bash compatibility

Built-ins inside pipelines are simplified

---

## 🎯 Learning Outcomes

Through this project, I gained hands-on experience with:

Process creation and execution

Pipes and file descriptor redirection

Command parsing and tokenization

Shell built-in behavior

Unix process model
