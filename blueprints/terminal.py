from flask import Blueprint, request, render_template, session
from tools import json_response, getClientIP
from datetime import datetime

terminal_bp = Blueprint('terminal', __name__)


@terminal_bp.route("/terminal")
def index():
    return render_template("terminal.html", user=getClientIP(request))


COMMANDS = {
    "help": "Show this help message",
    "about": "About this terminal",
    "clear": "Clear the terminal",
    "echo [text]": "Echo text back",
    "whoami": "Display the current user",
    "ls": "List directory contents",
    "pwd": "Print working directory",
    "date": "Show current date and time with optional format",
    "cd [path]": "Change directory to path",
    "cat [file]": "Display file contents",
    "rm [file]": "Remove a file",
    "tree [path]": "Display directory tree",
    "touch [file]": "Create a new empty file",
    "nano [file]": "Edit a file (write content)",
    "reset": "Reset the terminal session",
    "exit": "Exit the terminal session",
}


def get_nodes_in_directory(path: str) -> list[str]:
    """Simulate getting files in a directory for the terminal."""
    # If path is valid, get files from session
    if session.get("paths", None) is None:
        setup_path_session()

    # Split path into parts
    parts = path.strip("/").split("/")
    if not parts or parts == [""]:
        return session["paths"]

    current_level = session["paths"]
    for part in parts:
        found = False
        for item in current_level:
            if item["name"] == part and item["type"] == 0:
                current_level = item.get("children", [])
                found = True
                break
        if not found:
            return []

    return current_level


def setup_path_session():
    """Initialize the session path variables if not already set."""
    if "pwd" not in session:
        session["pwd"] = f"/home/{getClientIP(request)}"
    if "paths" not in session:
        binaries = []
        for cmd in COMMANDS.keys():
            binaries.append({"name": cmd.split()[0], "type": 2, "content": "", "permissions": 1})

        session["paths"] = [
            {"name": "home", "type": 0, "children": [
                {"name": str(getClientIP(request)), "type": 0, "children": [
                    {"name": "Readme.txt", "type": 1, "content": "This is a README file.", "permissions": 2},
                ], "permissions": 2}
            ], "permissions": 1},
            {"name": "bin", "type": 0, "children": binaries, "permissions": 1},
            {"name": "boot", "type": 0, "children": [], "permissions": 1},
            {"name": "dev", "type": 0, "children": [], "permissions": 1},
            {"name": "etc", "type": 0, "children": [], "permissions": 1},
            {"name": "lib", "type": 0, "children": [], "permissions": 1},
            {"name": "lib64", "type": 0, "children": [], "permissions": 1},
            {"name": "mnt", "type": 0, "children": [], "permissions": 1},
            {"name": "nix", "type": 0, "children": [], "permissions": 1},
            {"name": "opt", "type": 0, "children": [], "permissions": 1},
            {"name": "proc", "type": 0, "children": [], "permissions": 1},
            {"name": "root", "type": 0, "children": [], "permissions": 1},
            {"name": "run", "type": 0, "children": [], "permissions": 1},
            {"name": "sbin", "type": 0, "children": [], "permissions": 1},
            {"name": "srv", "type": 0, "children": [], "permissions": 1},
            {"name": "sys", "type": 0, "children": [], "permissions": 1},
            {"name": "tmp", "type": 0, "children": [], "permissions": 1},
            {"name": "usr", "type": 0, "children": [], "permissions": 1},
            {"name": "var", "type": 0, "children": [], "permissions": 1},
        ]


def is_valid_path(path: str) -> bool:
    """Check if the given path is valid in the simulated terminal."""
    if session.get("paths", None) is None:
        setup_path_session()

    # Split path into parts
    parts = path.strip("/").split("/")
    if not parts or parts == [""]:
        return True  # Root path is valid

    current_level = session["paths"]
    for part in parts:
        found = False
        for item in current_level:
            if item["name"] == part and item["type"] == 0:
                current_level = item.get("children", [])
                found = True
                break                
        if not found:
            return False

    return True

def is_valid_file(path: str) -> bool:
    """Check if the given file exists in the current directory."""
    if session.get("paths", None) is None:
        setup_path_session()

    # Get path parts
    parts = path.split("/")
    # Get files in the directory
    if is_valid_path("/".join(parts[:-1])):
        files = get_nodes_in_directory("/".join(parts[:-1]))
        for item in files:
            if item["name"] == parts[-1] and item["type"] == 1:
                return True
    return False

def is_valid_binary(path: str) -> bool:
    """Check if the given file exists in the current directory."""
    if session.get("paths", None) is None:
        setup_path_session()

    # Get path parts
    parts = path.split("/")
    # Get files in the directory
    if is_valid_path("/".join(parts[:-1])):
        files = get_nodes_in_directory("/".join(parts[:-1]))
        for item in files:
            if item["name"] == parts[-1] and item["type"] == 2:
                return True
    return False
    
def get_node(path: str) -> dict:
    """Get the node (file or directory) at the given path."""
    if session.get("paths", None) is None:
        setup_path_session()

    parts = path.strip("/").split("/")
    current_level = session["paths"]
    for part in parts:
        for item in current_level:
            if item["name"] == part:
                if part == parts[-1]:
                    return item
                else:
                    current_level = item.get("children", [])
                    break
    return {}

def build_tree(path: str, prefix: str = "") -> str:
        output = ""
        files = get_nodes_in_directory(path)
        for i, item in enumerate(files):
            connector = "└── " if i == len(files) - 1 else "├── "
            output += f"{prefix}{connector}{item['name']}\n"
            if item["type"] == 0:  # Directory
                extension = "    " if i == len(files) - 1 else "│   "
                output += build_tree(sanitize_path(path + "/" + item["name"]), prefix + extension)
        return output

def sanitize_path(path: str) -> str:
    """Sanitize the given path to prevent directory traversal."""
    parts = path.strip("/").split("/")
    sanitized_parts = []
    for part in parts:
        if part == "" or part == ".":
            continue
        elif part == "..":
            if sanitized_parts:
                sanitized_parts.pop()
        else:
            sanitized_parts.append(part)
    return "/" + "/".join(sanitized_parts)

def remove_node(path: str) -> bool:
    """Remove the node (file or directory) at the given path."""
    if session.get("paths", None) is None:
        setup_path_session()

    parts = path.strip("/").split("/")
    current_level = session["paths"]
    for i, part in enumerate(parts):
        for j, item in enumerate(current_level):
            if item["name"] == part:
                if i == len(parts) - 1:
                    # Remove the item
                    del current_level[j]

                    # Update the session paths
                    session["paths"] = session["paths"]

                    return True
                else:
                    current_level = item.get("children", [])
                    break
    return False


@terminal_bp.route("/terminal/execute/ls", methods=["POST"])
def ls():
    data = request.get_json() or {}
    args = data.get("args", "")
    args = args.split()
    # Check if -a flag is provided
    # Pop if -a flag from args
    all_files = False
    if "-a" in args:
        all_files = True
        args.remove("-a")
    elif "--all" in args:
        all_files = True
        args.remove("--all")

    path = session.get("pwd", f"/home/{getClientIP(request)}")
    if args:
        path = args[0]
        if not path.startswith("/"):
            # Relative path
            path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)
    if not is_valid_path(path):
        return json_response(request, {"output": f"ls: cannot access '{path}': No such file or directory"}, 200)
    
    files = get_nodes_in_directory(path)
    output = [file["name"] for file in files]
    if all_files:
        output.insert(0, ".")
        output.insert(1, "..")
    else:
        output = [file for file in output if not file.startswith(".")]
    output = " ".join(output)

    return json_response(request, {"output": output}, 200)


@terminal_bp.route("/terminal/pwd")
def pwd():
    if "pwd" not in session:
        session["pwd"] = f"/home/{getClientIP(request)}"
    pwd = session["pwd"]
    if pwd == "/home/" + getClientIP(request):
        pwd = "~"
    return json_response(request, {"output": pwd, "raw": session["pwd"]}, 200)


@terminal_bp.route("/terminal/execute/cd", methods=["POST"])
def cd():
    data = request.get_json() or {}
    args = data.get("args", "")
    args = args.split()

    if not args:
        # No path provided, go to home
        session["pwd"] = f"/home/{getClientIP(request)}"
        output = ""
    else:
        path = args[0]
        # Simulate changing directory
        if path == "~":
            session["pwd"] = f"/home/{getClientIP(request)}"
            output = ""
        
        if not path.startswith("/"):
            path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)

        if is_valid_path(path):
            session["pwd"] = sanitize_path(path)
            output = ""
        else:
            output = f"bash: cd: {path}: No such file or directory"

    return json_response(request, {"output": output}, 200)

def can_write_to_path(path: str) -> bool:
    """Check if the user can write to the given path (must be in their home directory)."""
    user_home = f"/home/{getClientIP(request)}"
    normalized_path = sanitize_path(path)
    return normalized_path.startswith(user_home)

def create_file(path: str, content: str = "") -> bool:
    """Create a new file at the given path."""
    if session.get("paths", None) is None:
        setup_path_session()

    parts = path.strip("/").split("/")
    filename = parts[-1]
    dir_path = "/".join(parts[:-1])

    # Get the directory
    if not is_valid_path("/" + dir_path):
        return False

    # Get nodes in directory
    dir_parts = dir_path.strip("/").split("/")
    current_level = session["paths"]
    
    for part in dir_parts:
        if part == "":
            continue
        for item in current_level:
            if item["name"] == part and item["type"] == 0:
                current_level = item.get("children", [])
                break

    # Check if file already exists
    for item in current_level:
        if item["name"] == filename:
            # Update existing file
            item["content"] = content
            session.modified = True
            return True

    # Create new file
    new_file = {
        "name": filename,
        "type": 1,
        "content": content,
        "permissions": 2
    }
    current_level.append(new_file)
    session.modified = True
    return True

def update_file_content(path: str, content: str) -> bool:
    """Update the content of an existing file."""
    if session.get("paths", None) is None:
        setup_path_session()

    parts = path.strip("/").split("/")
    current_level = session["paths"]
    
    for i, part in enumerate(parts):
        for item in current_level:
            if item["name"] == part:
                if i == len(parts) - 1:
                    # Update the file content
                    if item["type"] == 1:
                        item["content"] = content
                        session.modified = True
                        return True
                    return False
                else:
                    current_level = item.get("children", [])
                    break
    return False

@terminal_bp.route("/terminal/execute/touch", methods=["POST"])
def touch():
    try:
        data = request.get_json() or {}
        args = data.get("args", "")
        args = args.split()

        if not args:
            return json_response(request, {"output": "touch: missing file operand"}, 200)

        path = args[0]
        if not path.startswith("/"):
            path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)

        # Check if user can write to this path
        if not can_write_to_path(path):
            return json_response(request, {"output": f"touch: cannot touch '{path}': Permission denied"}, 200)

        # Check if file already exists
        if is_valid_file(path):
            return json_response(request, {"output": f"touch: '{path}': File already exists"}, 200)

        # Create the file
        if create_file(path, ""):
            output = ""
        else:
            output = f"touch: cannot create '{path}': No such file or directory"

        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"touch: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/nano", methods=["POST"])
def nano():
    try:
        data = request.get_json() or {}
        args = data.get("args", "")
        
        # Parse args - format: filename CONTENT content here
        parts = args.split(" CONTENT ", 1)
        if len(parts) != 2:
            return json_response(request, {"output": "Usage: nano [file] CONTENT [text]\nExample: nano test.txt CONTENT Hello World"}, 200)

        path = parts[0].strip()
        content = parts[1]

        if not path.startswith("/"):
            path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)

        # Check if user can write to this path
        if not can_write_to_path(path):
            return json_response(request, {"output": f"nano: cannot write to '{path}': Permission denied"}, 200)

        # Check if file exists
        if is_valid_file(path):
            # Update existing file
            node = get_node(path)
            if node.get("permissions", 0) < 2:
                return json_response(request, {"output": f"nano: cannot write to '{path}': Permission denied"}, 200)
            
            if update_file_content(path, content):
                output = ""
            else:
                output = f"nano: failed to update '{path}'"
        else:
            # Create new file
            if create_file(path, content):
                output = f"File '{path}' created successfully"
            else:
                output = f"nano: cannot create '{path}': No such file or directory"

        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"nano: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/cat", methods=["POST"])
def cat():
    try:
        data = request.get_json() or {}
        args = data.get("args", "")
        args = args.split()

        if not args:
            return json_response(request, {"output": "cat: missing file operand"}, 200)

        path = args[0]
        if not path.startswith("/"):
            path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)

        # Check if path is valid
        if not is_valid_file(path):
            # Check if it is a binary
            if is_valid_binary(path):
                return json_response(request, {"output": f"cat: {path}: Binary file"}, 200)
            return json_response(request, {"output": f"cat: {path}: No such file or directory"}, 200)

        output = get_node(path).get("content", "")

        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"cat: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/echo", methods=["POST"])
def echo():
    try:
        data = request.get_json() or {}
        args = data.get("args", "")
        return json_response(request, {"output": args}, 200)
    except Exception as e:
        return json_response(request, {"output": f"echo: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/date", methods=["POST"])
def date():
    try:
        # See if any args are passed
        data = request.get_json() or {}
        args = data.get("args", "")

        # Use arguments to format date if needed
        if args:
            # If args if --help or -h, show help message
            if args in ("--help", "-h"):
                output = (
                    "Usage: date [FORMAT]\n\n"
                    "Display the current date and time.\n\n"
                    "FORMAT controls the output. Some common format specifiers:\n"
                    "  %a  Abbreviated weekday name (e.g., 'Mon')\n"
                    "  %b  Abbreviated month name (e.g., 'Jan')\n"
                    "  %d  Day of the month (01 to 31)\n"
                    "  %H  Hour (00 to 23)\n"
                    "  %M  Minute (00 to 59)\n"
                    "  %S  Second (00 to 60)\n"
                    "  %Y  Year with century (e.g., 2024)\n\n"
                    "Example: date '%Y-%m-%d %H:%M:%S'"
                )
                return json_response(request, {"output": output}, 200)

            try:
                output = datetime.now().strftime(args)
            except Exception:
                output = "Invalid date format."
        else:
            output = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"date: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/rm", methods=["POST"])
def rm():
    try:
        data = request.get_json() or {}
        args = data.get("args", "")
        args = args.split()

        if not args:
            return json_response(request, {"output": "rm: missing operand"}, 200)

        path = args[0]
        if not path.startswith("/"):
            path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)

        # Check if user can write to this path
        if not can_write_to_path(path):
            return json_response(request, {"output": f"rm: cannot remove '{path}': Permission denied"}, 200)

        # Check if path is valid
        if not is_valid_file(path) and not is_valid_binary(path):
            return json_response(request, {"output": f"rm: cannot remove '{path}': No such file"}, 200)

        # Get the node
        node = get_node(path)
        # Only let user delete files if the permission is >1 (writable)
        if node.get("permissions", 0) < 2:
            return json_response(request, {"output": f"rm: cannot remove '{path}': Permission denied"}, 200)
        
        # Only let the user remove files
        if node.get("type", 1) != 1:
            return json_response(request, {"output": f"rm: cannot remove '{path}': Is a directory"}, 200)
        
        # Remove the file from session paths
        if remove_node(path):
            output = f"Removed '{path}'"
        else:
            output = f"Failed to remove '{path}'"

        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"rm: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/tree", methods=["POST"])
def tree():
    try:
        data = request.get_json() or {}
        args = data.get("args", "")
        path = session.get("pwd", f"/home/{getClientIP(request)}")
        if args:
            path = args
            if not path.startswith("/"):
                path = sanitize_path(session.get("pwd", f"/home/{getClientIP(request)}") + "/" + path)
        if not is_valid_path(path):
            return json_response(request, {"output": f"tree: cannot access '{path}': No such file or directory"}, 200)

        output = build_tree(path).rstrip()
        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"tree: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/<command>", methods=["POST"])
def execute_catch(command):
    try:
        data = request.get_json() or {}
        args = data.get("args", "")

        # Basic command processing
        if command == "help":
            output = "Available commands:\n" + \
                "\n".join(f"  {cmd}: {desc}" for cmd, desc in COMMANDS.items())
        elif command == "about":
            output = "This is a simulated terminal interface created by Nathan Woodburn."      

        elif command == "whoami":
            output = getClientIP(request)
        elif command == "pwd":
            # Get pwd from session or simulate
            output = session.get("pwd", f"/home/{getClientIP(request)}")
        else:
            output = f"Command not found: {command}"

        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"{command}: {str(e)}"}, 200)

@terminal_bp.route("/terminal/execute/reset", methods=["POST"])
def reset():
    try:
        # Clear the session data related to terminal
        session.pop("pwd", None)
        session.pop("paths", None)
        output = "Terminal session has been reset."
        return json_response(request, {"output": output}, 200)
    except Exception as e:
        return json_response(request, {"output": f"reset: {str(e)}"}, 200)

# Add error handler at the end
@terminal_bp.errorhandler(Exception)
def handle_terminal_error(error):
    """Handle all exceptions in terminal blueprint."""
    error_message = f"Terminal error: {str(error)}"
    return json_response(request, {"output": error_message}, 500)