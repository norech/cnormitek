#!/bin/python
import os
import sys
import fileinput
import re

class color:
    MAJOR   = '\033[91m'
    MINOR   = '\033[92m'
    INFO    = '\033[94m'
    NORMAL  = '\033[0m'

def usage():
    print("Please use it as shown : cnormitek [folder] [--no-CODE]\n")
    print("If you think this is an error please open an issue!")
    print()
    print("Flags:")
    for error in errors:
        print("  --no-" + error + ": ignore " + error + " (" + errors[error][0] + ")")
    exit()


blacklist = []

header_regex = (
        r"\/\*\n"
        r"\*\* EPITECH PROJECT, [0-9]{4}\n"
        r"\*\* (.*)\n"
        r"\*\* File description:\n"
        r"\*\* (.*)\n"
        r"\*\/"
        )

forbidden_syscall_regex = (
        r'(^|[^0-9a-zA-Z_])(printf|dprintf|fprintf|vprintf|sprintf|snprintf'
        r'|vprintf|vfprintf|vsprintf|vsnprintf|asprintf|scranf|memcpy|memset'
        r'|memmove|strcat|strchar|strcpy|atoi|strlen|strstr|strncat|strncpy'
        r'|strcasestr|strncasestr|strcmp|strncmp|strtok|strnlen|strdup|realloc'
        r')[^0-9a-zA-Z_]'
        )

function_impl_regex = r"(?:[^\(\)\n]+ |)([^\(\)\n ]+)\([^\n]*\)((?:\n|\r|\s)*){(?:\s+(?:[^\n]*)(?:\n|\r)|(?:\n|\r))*}"

errors = {
        "F2": ("function name should be in snake_case", "major"),
        "F3": ("too many columns", "major"),
        "F4": ("too long function", "major"),
        "G1": ("bad or missing header", "major"),
        "O1": ("delivery folder should not contain unnecessary files", "major"),
        "O3": ("too many functions in file", "major"), 
        "O4": ("file or folder should be named in snake_case", "major"), 

        "C1": ("probably too many conditions nested", "minor"),
        "C3": ("goto is discouraged", "minor"),
        "H2": ("no inclusion guard found", "minor"),
        "L2": ("bad indentation", "minor"),
        "L3": ("misplaced or missing space", "minor"),

        "implicit_L001": ("trailing space", "info"),
        "INF": ("suspicious system call found", "info")
        }

def get_line_pos(string, pos):
    line = 1
    if pos > len(string):
        raise IndexError("pos")
    for i in range(0, pos):
        char = string[i]
        if char == "\r":
            continue
        if char == "\n":
            line += 1
    return line

def check_file(file):
    content = ""
    fi = fileinput.input(file)
    for line in fi:
        content += line
    fi.close()

    check_header_comment(file, content)
    check_function_declarations(file, content)
    check_lines(file)

def get_error_color(error_type):
    if error_type == "major":
        return color.MAJOR
    elif error_type == "minor":
        return color.MINOR
    elif error_type == "info":
        return color.INFO
    return color.NORMAL

def show_error(file, code, line = None):
    if line is None:
        line = "?"

    if code in blacklist:
        return

    error = errors[code]

    print(file + ":" + str(line) + "::" + code + " - "
        + get_error_color(error[1])  + error[0] + " (" + error[1] + ")"
        + color.NORMAL)

def check_function_declarations(file, content):
    matches = re.finditer(function_impl_regex, content, re.MULTILINE)
    func_count = 0
    for matchNum, match in enumerate(matches, start=1):
        whole_match = match.group()
        line_nb_start = get_line_pos(content, match.start())
        line_nb_end = get_line_pos(content, match.end())
        if line_nb_end - line_nb_start >= 23:
            show_error(file, "F4", line_nb_start)
        if not re.match("^[a-z][a-z_0-9]*$", match.group(1)):
            show_error(file, "F2", line_nb_start)
        # if no newline present between function ")" and "{"
        if not "\n" in match.group(2):
            show_error(file, "L3", line_nb_start)
        func_count += 1
    if func_count > 5:
        show_error(file, "O3")

def check_header_comment(file, content):
    matches = re.search(header_regex, content)

    if not matches:
        show_error(file, "G1")

def check_lines(file):
    fi = fileinput.input(file)

    line_nb = 0
    has_include_guard = False
    was_statement = False

    for line in fi:
        line_nb += 1

        # don't match headers
        if line.startswith("/*") or line.startswith("**") or line.startswith("*/"):
            continue

        # match ifndef or other if
        if re.search('^\s*\#if', line):
            has_include_guard = True

        # check for forbidden system_call
        if re.search(forbidden_syscall_regex, line):
            show_error(file, "INF", line_nb)

        # columns length
        if len(line.replace("\t", "    ")) > 81: # 80 characters + \n
            show_error(file, "F3", line_nb)

        # tabs
        if "\t" in line or re.search('\t', line):
            show_error(file, "L2", line_nb)

        if re.search('(\t|    ){3,}(while|for|if)', line):
            show_error(file, "C1", line_nb)
        if re.search('(\t|    ){2,}\}?\s*(else if)', line):
            show_error(file, "C1", line_nb)


        # goto
        if "goto " in line:
            show_error(file, "C3", line_nb)

        # misplaced spaces
        if re.search('(while|for|if|return)\(', line):
            show_error(file, "L3", line_nb)

        # in while/for/if/...
        if was_statement and re.search('^\s+\{', line):
            show_error(file, "L3", line_nb)
        was_statement = False
        if re.search('^(\t|    )(while|for|if)', line):
            was_statement = True

        # trailing spaces
        if re.search('\s+\n$', line):
            show_error(file, "implicit_L001", line_nb)

    if file.endswith(".h") and not has_include_guard:
        show_error(file, "H2")

    fi.close()

def read_dir(dir):
    for file in os.listdir(dir):
        if not file.startswith(".") and not re.match("^[a-z][a-z_0-9]*($|\.)", file):
            show_error(file, "O4")

        if os.path.isfile(dir + "/" + file):
            if re.search('\.(c|h)$', file):
                check_file(dir + "/" + file)
            elif re.search('\.(o|sh|a|so|d|gcda|gcno|out|swp|elf|obj)$', file):
                show_error(dir + "/" + file, "O1")

        elif not (file == "tests" and os.path.exists(dir + "/.git")):
            read_dir(dir + "/" + file)

def read_args():
    args = sys.argv
    path = None

    if not len(args) > 1:
        usage()

    for i in range(1, len(args)):
        if args[i] == "--help":
            usage()
        if args[i].startswith('--no-'):
            blacklist.append(args[i][5:])
            continue
        if path is not None:
            usage()
        path = args[i]

    if path is None:
        path = os.getcwd()
    return path

path = read_args()
if os.path.isfile(path):
    check_file(path)
else:
    read_dir(path)
