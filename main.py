#!/bin/python
import os
import sys
import fileinput
import re

VERSION = "0.3.0"

SUPPORTED_CODING_STYLES = ["2020", "2021"]

class color:
    MAJOR   = '\033[91m'
    MINOR   = '\033[92m'
    INFO    = '\033[94m'
    NORMAL  = '\033[0m'

year = "2021"
strict = False
stdin_is_header = False
blacklist = []
allowed_syscalls = []
disallowed_syscalls = []

def usage():
    print("cnormitek " + VERSION)
    print()
    print(
        "Please use it as shown : cnormitek [folder] "
        "[--allowed=malloc,free,...] [--no-CODE]\n")
    print("If you think this is an error please open an issue!")
    print()
    print("OPTIONS")
    print("\t--allowed=<functions>")
    print("\t\tA comma-separated list of allowed system calls")
    print("\t\tIf omitted, all system calls are allowed, unless those specified with --disallowed")
    print()
    print("\t--disallowed=<functions>")
    print("\t\tA comma-separated list of disallowed system calls")
    print()
    print("FLAGS")
    print("\t--cs-2020, --cs-2021\tSelect the prefered coding style (default: cs-" + str(year) + ")")
    print("\t--strict\t\tallow more strict error checks (cause more false positives), also enables checks for " + ', '.join(strict_error_checks))
    print("\t--no-gitignore\t\tdo not read .gitignore files")
    print("\t--no-color\t\tdo not show colors")

    errors_tuple = list(dict([
        (error[:-5], errors[error][0]) if error.endswith("-2020") or error.endswith("-2021")
        else (error, errors[error][0]) for error in errors
    ]).items())

    for (error, desc) in errors_tuple:
        strict_check_message = ""
        if error in strict_error_checks:
            strict_check_message = "[when strict only] "

        spacing = "\t" * (1 + 1 * (len(error) < 8))
        print("\t--no-" + error + " " + spacing + strict_check_message +
            "ignore " + error + " (" + desc + ")")

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

makefile_header_regex = (
    r"^"
    r"##\n"
    r"## EPITECH PROJECT, [0-9]{4}\n"
    r"## (.*)\n"
    r"## File description:\n"
    r"## (.*)\n"
    r"##"
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
    r'|raise|signal|sigaction|atexit|div|abs|labs|ldiv|llabs|atoi'
    r'|atol|strtod|strtol|strtoll|strtoul|wcstombs|mbstowcs|mblen|mbtowc'
    r'|wctomb|malloc|calloc|realloc|free|abort|exit|getenv|system|rand|srand'
    r'|qsort|bsearch|qsort_r|bsearch_r|lldiv|atoll|strtoull|strtouq|strtoul'
    r'|strtoumax|strtof|strtold|strtoimax|strtol|strtoll|strtoumax|strtold'
    r'|strtof|strtod|strtoq|strtok|strchr|strrchr|strstr|strcasestr|strncat'
    r'|strspn|strcspn|strpbrk|strtok_r|strsep|strsignal|strverscmp|strxfrm'
    r'|strcoll|strxfrm|strxfrm_l|strxfrm_l|strxfrm_l|strxfrm_l|strxfrm_l'
    r'|strxfrm_l|strxfrm_l|strxfrm_l|strxfrm_l|strxfrm_l|strxfrm_l|strxfrm_l'
    r'|sbrk|wbrk|mbrk|mallinfo|mallopt|malloc_info|malloc_stats|malloc_trim'
    r'|posix_memalign|valloc|pvalloc|memalign|aligned_alloc|valloc|pvalloc'
    r'|strtoupper|strtolower|assert'
    r')( |\t)*\('
)

unnecessary_files_regex = (
    r'('
    r'^vgcore\.'
    r'|\.(o|a|so|d|gcda|gcno|swp|elf|obj)$'
    r'|^\#(.*)\#$'
    r'|~$'
    r')'
)

function_impl_regex = (
    r"(?:^|\n)"                  # beginning of file or newline
    r"(?:\w+?"                   # function type or keywords
        r"(?: \w+?| \w+? )*?"    # additional function type or keywords (if any)
        r"([\* ]+?)"             # pointer stars and spaces (group 1)
    r")"
    r"(\w+?)"                    # function name
    r"\("                        # function arguments open parenthesis
        r"("                     # function arguments content (group 2)
            r"(?:"
                r"\n[\t ]+?"     # newline and spaces
            r"|"
                r"[^\)\{]"       # anything but close parenthesis or open bracket
            r")*?"               # can have 0 or more arguments
        r")"
    r"\)"                        # function arguments close parenthesis
    r"((?:\\[\r\n]|[\r\n\s])*?)" # newlines/spaces between args and body (group 3)
    r"\{"                        # function body open bracket
        r"("                     # function body (group 4)
            r"(?:"
                r"\s*?"          # each line of body CAN start with spaces (not enforced due to backtracking issues!)
                r"(?:[^\n]*?)"   # match any character except newline
                r"(?:\n|\r)"     # match newline or carriage return
            r"|"
                r"(?:\n|\r)"     # maybe the line can alse be empty
            r")*?"               # a function have 0 or more lines in body
        r")"
    r"\}"                        # function body close bracket
)

macro_statement_regex = (
    r"(?:\n|^)(#define) ([A-Za-z0-9]+)\([^\n]+\)"
    r"(?:\\\n|\\\r\n| |\t)*?(?:|\()(?:\\\n|\\\r\n| |\t)*?\{"
)

misplaced_multiline_before_else_regex = (
    r"}(?: |\t)*(?:\n|\r\n)(?: |\t)*else(?: |\t)+?"
)

misplaced_multiline_after_else_regex = (
    r"(?: |\t)else(?:(?:\n|\r\n)|(?: |\t)+?(.*?)(?:\n|\r\n))(?: |\t)*?{"
)

strict_error_checks = [
    "H3-2020"
]

errors = {
    "F2": ("function name should be in snake_case", "major"),
    "F3-2020": ("too many columns (CS2020)", "major"),
    "F3-2021": ("too many columns (CS2021)", "major"),
    "F4-2020": ("too long function (should be <=20 lines) (CS2020)", "major"),
    "F4-2021": ("too long function (should be <20 lines) (CS2021)", "major"),
    "F5": ("too many arguments or missing void", "major"),
    "G1-2020": ("bad or missing header (CS2020)", "major"),
    "G1-2021": ("bad or missing header (CS2021)", "major"),
    "O1": ("delivery folder should not contain unnecessary files", "major"),
    "O3": ("too many functions in file", "major"),
    "O4": ("file or folder should be named in snake_case", "major"),
    "C2": ("only header files should contain macros and static inline functions", "major"),

    "C1": ("probably too many conditions nested", "minor"),
    "C3": ("goto is discouraged", "minor"),
    "H2": ("no inclusion guard found", "minor"),
    "H3-2020": ("macros should not be used for constants and should only match one statement (CS2020)", "minor"),
    "L2": ("bad indentation", "minor"),
    "L3": ("misplaced or missing space", "minor"),
    "V3": ("pointer symbol is not attached to the name", "minor"),
    "G2": ("only one empty line should separate the implementations of functions", "minor"),
    "G7-2021": ("line endings must be done in UNIX style (LF) (CS2021)", "minor"),
    "G8-2021": ("trailing space (CS2021)", "minor"),
    "G9-2021": ("no more than one single trailing line must be present (CS2021)", "minor"),
    "F6": ("no comment inside a function", "minor"),
    "L6": ("one line break should be present to separate implementations from function remainder", "minor"),

    "A3-2021": ("one single trailing line must be present", "info"),
    "implicit_LF-2020": ("line endings must be done in UNIX style (LF) (CS2020)", "info"),
    "implicit_L001-2020": ("trailing space (CS2020)", "info"),
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

def is_header_file(file):
    if file == "stdin" and stdin_is_header:
        return True
    elif file == "stdin":
        return False
    return file.endswith(".h")

def glob_match(s1, s2):
    escaped = re.escape(s2)
    pattern = escaped.replace("\\*\\*", "(.*)").replace("\\*", "([^/]+)")
    return re.search("^" + pattern + "$", s1) is not None

def get_ignored_files(gitignore_path):
    if "gitignore" in blacklist:
        return []

    fi = fileinput.input(gitignore_path)
    start = os.path.dirname(gitignore_path)
    ignored_files = []

    for line in fi:
        parts = line.replace("\n", "").replace("\r", "").split("#")
        if parts[0].replace(" ", "") != "":
            if not "/" in parts[0]:
                ignored_files.append(parts[0])
            else:
                abspath = os.path.abspath(start + "/" + parts[0])
                ignored_files.append(abspath)

    fi.close()
    return ignored_files

def is_file_ignored(file, ignored_files):
    basename = os.path.basename(file)
    file = os.path.abspath(file)
    for ignored_file in ignored_files:
        if glob_match(file, ignored_file) or glob_match(basename, ignored_file):
            return True
    return False

def check_file(file):
    content = ""
    fi = fileinput.input(file)
    for line in fi:
        content += line
    fi.close()

    check_content(file, content)

def check_makefile(file):
    content = ""
    fi = fileinput.input(file)
    for line in fi:
        content += line
    fi.close()

    check_makefile_header_comment(file, content)
    check_makefile_lines(file, content.splitlines(True))

def check_content(file, content):
    check_eol(file, content)
    check_eof(file, content)
    check_header_comment(file, content)
    check_function_implementations(file, content)
    check_defines(file, content)
    check_misplaced_multiline_spaces(file, content)
    check_lines(file, content.splitlines(True))

def get_error_color(error_type):
    if "color" in blacklist:
        return ""
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

    if code in strict_error_checks and not strict:
        return

    codename = code;

    if code.endswith("-2020"):
        if year != "2020":
            return
        codename = code[:-5]

    if code.endswith("-2021"):
        if year != "2021":
            return
        codename = code[:-5]

    if codename in blacklist:
        return

    (desc, type) = errors[code]

    print(file + ":" + str(line) + "::" + codename + " - "
        + get_error_color(type) + desc + " (" + type + ")"
        + (color.NORMAL if "color" not in blacklist else ""))

def check_misplaced_multiline_spaces(file, content):
    for match in re.finditer(misplaced_multiline_before_else_regex, content):
        show_error(file, "L3", get_line_pos(content, match.start()))
    for match in re.finditer(misplaced_multiline_after_else_regex, content):
        show_error(file, "L3", get_line_pos(content, match.start()))

def check_defines(file, content):
    matches = re.finditer(macro_statement_regex, content, re.MULTILINE)
    for match in matches:
        line_nb = get_line_pos(content, match.start() + 1)
        show_error(file, "H3-2020", line_nb)

def check_function_implementations(file, content):
    matches = re.finditer(function_impl_regex, content, re.MULTILINE)
    func_count = 0
    previous_function_end = -1
    for match in matches:
        whole_match = match.group()
        line_nb = get_line_pos(content, match.start(3))
        line_nb_start = get_line_pos(content, match.end(4))
        line_nb_end = get_line_pos(content, match.end())

        # too long function (CS2020)
        if line_nb_end - line_nb_start - 1 > 20:
            show_error(file, "F4-2020", line_nb)

        # too long function (CS2021)
        if line_nb_end - line_nb_start - 1 >= 20:
            show_error(file, "F4-2021", line_nb)

        # misplaced pointer star in function declaration signature
        if match.group(1) is not None and match.group(1).startswith("*") and match.group(1).endswith(" "):
            show_error(file, "V3", line_nb)

        # function name not in snake_case
        if not re.search("^[a-z][a-z_0-9]*$", match.group(2)):
            show_error(file, "F2", line_nb)

        # too many function arguments or missing "void"
        args_str = match.group(3)
        if args_str.count(",") > 3 or args_str.replace(" ", "") == "":
            show_error(file, "F5", line_nb)

        # if no newline present between function ")" and "{"
        if not "\n" in match.group(4):
            show_error(file, "L3", line_nb)

        # too many functions in one file
        func_count += 1
        if func_count > 5:
            show_error(file, "O3", line_nb)

        # comment in function implementation
        function_content = match.group(5)
        if "//" in function_content or re.search("/\\*[^*]*\\*+(?:[^/*][^*]*\\*+)*/", function_content):
            show_error(file, "F6", line_nb)

        # too many blank lines in function
        if len(re.findall("\n\n", function_content.strip("\r\n"))) > 1:
            show_error(file, "L6", line_nb)

        # too many blank lines between function implementations
        if previous_function_end != -1:
            content_btw_functions = content[previous_function_end:match.start()];
            content_wo_spaces = content_btw_functions.replace(" ", "").replace("\t", "")
            content_wo_spaces_nl = content_wo_spaces.replace("\n", "").replace("\r", "")
            if len(content_wo_spaces_nl) == 0 and content_wo_spaces.count("\n") != 1:
                show_error(file, "G2", line_nb)

        previous_function_end = match.end()

def check_eol(file, content):
    if "\r" in content:
        show_error(file, "G7-2021")
        show_error(file, "implicit_LF-2020")

def check_eof(file, content):
    if not content.rstrip(' \t').endswith("\n"):
        show_error(file, "A3-2021", get_line_pos(content, len(content)))
    if content.endswith("\n\n"):
        show_error(file, "G9-2021", get_line_pos(content, len(content)))

def check_header_comment(file, content):
    matches = re.search(header_regex, content)

    if not matches:
        show_error(file, "G1-2020")
        show_error(file, "G1-2021")


def check_makefile_header_comment(file, content):
    matches = re.search(makefile_header_regex, content)

    if not matches:
        show_error(file, "G1-2021")

def check_makefile_lines(file, lines):
    line_nb = 0

    for line in lines:
        line_nb += 1
        # columns length
        if len(line.replace("\t", "    ")) > 81: # 80 characters + \n
            show_error(file, "F3-2021", line_nb)

def check_lines(file, lines):
    line_nb = 0
    has_include_guard = False
    was_statement = False

    for line in lines:
        line_nb += 1

        # don't match headers
        if line.startswith("/*") or line.startswith("**") \
        or line.startswith("*/"):
            continue

        if re.search('^\s*\#define [A-Za-z0-9]+ ', line):
            show_error(file, "H3-2020", line_nb)

        if re.search('^\s*\#define', line) and not is_header_file(file):
            show_error(file, "C2", line_nb)

        if (re.search('^static inline', line) or re.search('^inline static', line)) \
        and not is_header_file(file):
            show_error(file, "C2", line_nb)

        # match ifndef or other if
        if re.search('^\s*\#if', line):
            has_include_guard = True

        if re.search('^\s*\#pragma once$', line):
            has_include_guard = True

        # check for forbidden or allowed system_call
        syscalls = re.finditer(forbidden_syscall_regex, line)
        for matchNum, match in enumerate(syscalls, start=1):
            if len(allowed_syscalls) > 0:
                if not match.group(1) in allowed_syscalls:
                    show_error(file, "syscall", line_nb)
            if len(disallowed_syscalls) > 0:
                if match.group(1) in disallowed_syscalls:
                    show_error(file, "syscall", line_nb)

        # columns length
        if len(line.replace("\t", "    ")) > 81: # 80 characters + \n
            show_error(file, "F3-2020", line_nb)
            show_error(file, "F3-2021", line_nb)

        # tabs
        if "\t" in line or re.search('\t', line):
            show_error(file, "L2", line_nb)
        # multiple of 4 of indentation
        elif re.search('^( )+', line) and not re.search('^(    )+[^ ]', line):
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
            show_error(file, "G8-2021", line_nb)
            show_error(file, "implicit_L001-2020", line_nb)

    if is_header_file(file) and not has_include_guard:
        show_error(file, "H2")

def is_elf(file):
    file = open(file, "rb")
    magic = file.read(4)
    file.close()
    return magic == b"\x7fELF"

def read_dir(dir, ignored_files):
    if os.path.exists(dir + "/.gitignore"):
        ignored_files = list(element for element in ignored_files)
        ignored_files.extend(get_ignored_files(dir + "/.gitignore"))

    try:
        for file in os.listdir(dir):
            if os.path.isfile(dir + "/" + file):
                if file.lower() == "makefile":
                    check_makefile(dir + "/" + file)
                elif re.search('\.(c|h)$', file):
                    if not re.search('^[a-z][a-z_0-9]*\.(c|h)$', file):
                        show_error(dir + "/" + file, "O4")
                    check_file(dir + "/" + file)
                elif not is_file_ignored(dir + "/" + file, ignored_files):
                    if re.search(unnecessary_files_regex, file) or is_elf(dir + "/" + file):
                        show_error(dir + "/" + file, "O1")

            elif not file.startswith(".") and not (file == "tests" \
            and os.path.exists(dir + "/.git")):
                if not file.startswith(".") \
                and not re.search('^[a-z][a-z_0-9]*', file):
                    show_error(dir + "/" + file, "O4")
                read_dir(dir + "/" + file, ignored_files)
    except FileNotFoundError as error:
        print("cnormitek: " + str(error))
        sys.exit(84)

def read_args():
    global year
    global strict
    global blacklist
    global allowed_syscalls
    global disallowed_syscalls
    global stdin_is_header
    args = sys.argv
    path = None

    for i in range(1, len(args)):
        if args[i] == "--help" or args[i] == "-h":
            usage()
        if args[i] == "--strict" or args[i] == "-s":
            strict = True
            continue
        if args[i] == "--stdin-h":
            stdin_is_header = True
            continue
        if args[i].startswith("--cs-") and args[i][5:] in SUPPORTED_CODING_STYLES:
            year = args[i][5:]
            continue
        if args[i].startswith('--no-'):
            blacklist.append(args[i][5:])
            continue
        if args[i].startswith("--allowed="):
            allowed_syscalls = args[i][10:].split(",")
        if args[i].startswith("--disallowed="):
            disallowed_syscalls = args[i][10:].split(",")
            continue
        if path is not None:
            usage()
        path = args[i]

    if path is None:
        path = os.getcwd()
    return path

path = read_args()
if path == "-":
    check_content("stdin", ''.join(sys.stdin.readlines()))
elif os.path.isfile(path):
    check_file(path)
else:
    read_dir(path, [])
