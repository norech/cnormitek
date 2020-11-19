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

blacklist = []
allowed_syscalls = [ "malloc", "free", "write" ]

def usage():
    print(
        "Please use it as shown : cnormitek [folder] "
        "[--allowed=malloc,free,...] [--no-CODE]\n")
    print("If you think this is an error please open an issue!")
    print()
    print("OPTIONS")
    print("\t--allowed=<functions>")
    print("\t\tA comma-separated list of allowed system calls")
    print("\t\tIf omitted, defaults to: " + ",".join(allowed_syscalls))
    print()
    print("FLAGS")
    for error in errors:
        spacing = "\t" * (1 + (len(error) < 10))
        print("\t--no-" + error + " " + spacing +
            "ignore " + error + " (" + errors[error][0] + ")")
    exit()

header_regex = (
        r"^"
        r"\/\*\n"
        r"\*\* EPITECH PROJECT, [0-9]{4}\n"
        r"\*\* (.*)\n"
        r"\*\* File description:\n"
        r"\*\* (.*)\n"
        r"\*\/"
        )

forbidden_syscall_regex = (
        r'(?:^|[^0-9a-zA-Z_])(printf|dprintf|fprintf|vprintf|sprintf|snprintf'
        r'|vprintf|vfprintf|vsprintf|vsnprintf|asprintf|scranf|memcpy|memset'
        r'|memmove|strcat|strchr|strcpy|atoi|strlen|strstr|strncat|strncpy'
        r'|strcasestr|strncasestr|strcmp|strncmp|strtok|strnlen|strdup|realloc'
        r'|write|free|malloc|opendir|readdir|closedir|stat|lstat|getpwuid'
        r'|getgrgid|time|ctime|readlink|perror|strerrir|exit|calloc|realloc'
        r'|qsort|bsearch|rand|srand|atof|atoi|atol|strtod|strtol|strtoll'
        r'|strtoul|mblen|mbtowc|wctomb|mbstowcs|wcstombs|fscanf|scanf'
        r'|sscanf|fopen|fflush|fclose|freopen|remove|rename|setbuf|setvbuf'
        r'|tmpfile|tmpnam|fgetc|fgets|fputc|fputs|getc|getchar|gets|putc'
        r'|putchar|puts|ungetc|fread|fwrite|fgetpos|fseek|fsetpos|ftell|rewind'
        r'|clearerr|feof|perror|memcmp|strcmp|strcoll|strxfrm|strcspn'
        r'|strpbrk|acos|asin|atan|atan2|ceil|cos|cosh|exp|fabs|floor|fmod|frexp'
        r'|ldexp|log|log10|modf|pow|sin|sinh|sqrt|tan|tanh|clock|asctime'
        r'|difftime|gmtime|localtime|mktime|strftime|assert|isalpha|isalnum'
        r'|iscntrl|isdigit|isgraph|islower|isprint|inpunct|isspace|isupper'
        r'|isxdigit|tolower|toupper|localeconv|setlocale|longjmp|setjmp'
        r'|raise|signal|atexit|div|abs|labs|ldiv'
        r')[^0-9a-zA-Z_]'
        )

unnecessary_files_regex = (
        r'('
        r'^vgcore\.'
        r'|\.(o|sh|a|so|d|gcda|gcno|out|swp|elf|obj)$'
        r'|^\#(.*)\#$'
        r'|~$'
        r')'
        )

function_impl_regex = (
        r"(?:\n|^)(?:[^\(\)\n\s\*][^\(\)\n\*]+|)(\*+[ ]*| )([^\(\)\n ]+)"
        r"\(([^\n]*)\)((?:\n|\r|\s)*){(?:\s+(?:[^\n]*)(?:\n|\r)|(?:\n|\r))*}"
        )

errors = {
        "F2": ("function name should be in snake_case", "major"),
        "F3": ("too many columns", "major"),
        "F4": ("too long function", "major"),
        "F5": ("too many arguments or missing void", "major"),
        "G1": ("bad or missing header", "major"),
        "O1": ("delivery folder should not contain unnecessary files", "major"),
        "O3": ("too many functions in file", "major"), 
        "O4": ("file or folder should be named in snake_case", "major"), 

        "C1": ("probably too many conditions nested", "minor"),
        "C3": ("goto is discouraged", "minor"),
        "H2": ("no inclusion guard found", "minor"),
        "L2": ("bad indentation", "minor"),
        "L3": ("misplaced or missing space", "minor"),
        "V3": ("pointer symbol is not attached to the name", "minor"),

        "implicit_L001": ("trailing space", "info"),
        "syscall": ("suspicious system call found", "info"),
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

def glob_match(s1, s2):
    if len(s1) == 0:
        s1 = "\0"
    if len(s2) == 0:
        s2 = "\0"
    s1_next = s1[1:]
    s2_next = s2[1:]
    if s1[0] == "\0" and s2[0] == "\0":
        return True
    elif s1[0] == s2[0]:
        return glob_match(s1_next, s2_next)
    elif s2[0] == '*':
        if s1[0] != "\0":
            return glob_match(s1_next, s2) or glob_match(s1, s2_next)
        else:
            return glob_match(s1, s2_next)
    else:
        return False

def get_ignored_files(gitignore_path):
    fi = fileinput.input(gitignore_path)
    start = os.path.dirname(gitignore_path)
    ignored_files = []

    for line in fi:
        parts = line.replace("\n", "").replace("\r", "").split("#")
        if parts[0].replace(" ", "") != "":
            ignored_files.append( os.path.relpath(parts[0], start=start))

    fi.close()
    return ignored_files

def is_file_ignored(file, ignored_files):
    for ignored_file in ignored_files:
        if glob_match(file, ignored_file):
            return True
    return False

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
        line_nb_start = get_line_pos(content, match.start() + 1)
        line_nb_end = get_line_pos(content, match.end())
        if line_nb_end - line_nb_start >= 23:
            show_error(file, "F4", line_nb_start)

        if match.group(1).startswith("*") and match.group(1).endswith(" "):
            show_error(file, "V3", line_nb_start)

        if not re.search("^[a-z][a-z_0-9]*$", match.group(2)):
            show_error(file, "F2", line_nb_start)

        args_str = match.group(3)
        if args_str.count(",") > 3 or args_str.replace(" ", "") == "":
            show_error(file, "F5", line_nb_start)

        # if no newline present between function ")" and "{"
        if not "\n" in match.group(4):
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
        if line.startswith("/*") or line.startswith("**") \
        or line.startswith("*/"):
            continue

        # match ifndef or other if
        if re.search('^\s*\#if', line):
            has_include_guard = True

        # check for forbidden system_call
        syscalls = re.finditer(forbidden_syscall_regex, line)
        for matchNum, match in enumerate(syscalls, start=1):
            if not match.group(1) in allowed_syscalls:
                show_error(file, "syscall", line_nb)

        # columns length
        if len(line.replace("\t", "    ")) > 81: # 80 characters + \n
            show_error(file, "F3", line_nb)

        # tabs
        if "\t" in line or re.search('\t', line):
            show_error(file, "L2", line_nb)

        if re.search('(\t|    ){4,}(while|for|if)', line):
            show_error(file, "C1", line_nb)
        if re.search('(\t|    ){3,}\}?\s*(else if)', line):
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

def read_dir(dir, ignored_files):
    if os.path.exists(dir + "/.gitignore"):
        ignored_files = ignored_files.copy()
        ignored_files.extend(get_ignored_files(dir + "/.gitignore"))

    for file in os.listdir(dir):
        if os.path.isfile(dir + "/" + file):
            if re.search('\.(c|h)$', file):
                if not re.search('^[a-z][a-z_0-9]*\.(c|h)$', file):
                    show_error(dir + "/" + file, "O4")
                check_file(dir + "/" + file)
            elif not is_file_ignored(dir + "/" + file, ignored_files) \
            and re.search(unnecessary_files_regex, file):
                show_error(dir + "/" + file, "O1")

        elif not file.startswith(".") and not (file == "tests" \
        and os.path.exists(dir + "/.git")):
            if not file.startswith(".") \
            and not re.search('^[a-z][a-z_0-9]*', file):
                show_error(dir + "/" + file, "O4")
            read_dir(dir + "/" + file, ignored_files)

def read_args():
    global blacklist
    global allowed_syscalls
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
        if args[i].startswith("--allowed="):
            allowed_syscalls = args[i][10:].split(",")
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
    read_dir(path, [])
