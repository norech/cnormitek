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
    print("Please use it as shown : cnormitek [folder]\n")
    print("If you think this is an error please open an issue !")
    exit()

header_regex = (
        r"\/\*\n"
        r"\*\* EPITECH PROJECT, [0-9]{4}\n"
        r"\*\* (.*)\n"
        r"\*\* File description:\n"
        r"\*\* (.*)\n"
        r"\*\/"
        )


function_impl_regex = r"[^\(\)\n]+\([^\n]*\)((?:\n|\r|\s)*){(?:\s+(?:[^\n]*)(?:\n|\r)|(?:\n|\r))*}"

errors = {
        "F3": ("too many columns", "major"),
        "F4": ("too long function", "major"),
        "G1": ("bad or missing header", "major"),
        "O1": ("Your delivery folder should not contain unncessary files", "major"),

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

    check_G1(file, content)
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

    error = errors[code]

    print(file + ":" + str(line) + "::" + code + " - " + get_error_color(error[1]) + error[0] + " (" + error[1] + ")" + color.NORMAL)

def check_function_declarations(file, content):
    matches = re.finditer(function_impl_regex, content, re.MULTILINE)

    for matchNum, match in enumerate(matches, start=1):
        whole_match = match.group()
        line_nb_start = get_line_pos(content, match.start())
        line_nb_end = get_line_pos(content, match.end())
        if line_nb_end - line_nb_start >= 23:
            show_error(file, "F4", line_nb_start)
        # if no newline present between function ")" and "{"
        if not "\n" in match.group(1):
            show_error(file, "L3", line_nb_start)

def check_G1(file, content):
    matches = re.search(header_regex, content)

    if not matches:
        show_error(file, "G1")

def check_lines(file):
    fi = fileinput.input(file)

    line_nb = 0
    empty_lines_count = 0
    has_include_guard = False

    for line in fi:
        line_nb += 1

        # don't match headers
        if line.startswith("/*") or line.startswith("**") or line.startswith("*/"):
            continue

        # match ifndef or other if
        if re.search('^\s*\#if', line):
            has_include_guard = True

        # check for forbidden system_call
        if re.search('(^|[^0-9a-zA-Z_])(printf|dprintf|fprintf|vprintf|sprintf|snprintf|vprintf|vfprintf|vsprintf|vsnprintf|asprintf|scranf|memcpy|memset|memmove|strcat|strchar|strcpy|atoi|strlen|strstr|strncat|strncpy|strcasestr|strncasestr|strcmp|strncmp|strtok|strnlen|strdup|realloc)[^0-9a-zA-Z]', line):
            show_error(file, "INF", line_nb)

        # columns length
        if len(line.replace("\t", "    ")) > 80:
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
        if re.search('^\s+\{', line):
            show_error(file, "L3", line_nb)

        # in functions
        if re.search('^(?!\s).+\s*\{\s*$', line):
            show_error(file, "L3", line_nb)

        # trailing spaces
        if re.search('\s+\n$', line):
            show_error(file, "implicit_L001", line_nb)

        # empty line
        if re.search('^\s+$', line):
            empty_lines_count += 1
        else:
            empty_lines_count = 0

        if empty_lines_count >= 2:
            show_error(file, "G2", line_nb)

    if file.endswith(".h") and not has_include_guard:
        show_error(file, "H2")

    fi.close()

def read_dir(dir):
    for file in os.listdir(dir):
        if os.path.isfile(dir + "/" + file):
            if re.search('\.(c|h)$', file):
                check_file(dir + "/" + file)
            elif re.search('\.(o|sh|a|so|d|gcda|gcno|out|swp|elf|obj)$', file):
                show_error(dir + "/" + file, "O1", 0)

        elif not (file == "tests" and os.path.exists(dir + "/.git")):
            read_dir(dir + "/" + file)

argdir = sys.argv

if not len(sys.argv) > 1:
    usage()

if os.path.isfile(argdir[1]):
    check_file(argdir[1])
else:
    read_dir(argdir[1])
