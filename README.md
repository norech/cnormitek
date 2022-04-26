# cnormitek

An Epitech C coding style faults detector.

## Supported rules of the Epitech C coding style

- `--cs-2020`: C Coding Style 2020
  - **Rules checked:** C1, C2, C3, F2, F3, F4, F5, F6, G1, G2, H2, H3, L2, L6, L3, O1, O3, O4, V3 (minimal)
- `--cs-2021`: C Coding Style 2021
  - **Rules checked:** A3, C1, C2, C3, F2, F3, F4, F5, F6, G1, G2, G7, G8, G9, H2, L2, L3, L6, O1, O3, O4, V3 (minimal)

> Due to the nature of the rules and of the performed checks, the results are
> not fully accurate, neither complete. Some of the most common faults
> related to the rules indicated above should be reported, but more complex
> cases might not be reported accurately.

## Support for `.gitignore`

Cnormitek will not check coding style on files that are ignored by Git,
unless `--no-gitignore` is specified, or `git` is absent from the PATH.

## Installation

```bash
$ git clone git@github.com:norech/cnormitek.git
$ cd cnormitek
$ sudo ./install.sh
```

## Usage

```bash
# Displays help
$ cnormitek --help

# Runs cnormitek on all files in the current directory
# and doesn't report about the F3 and O4 rules
$ cnormitek --no-F3 --no-O4 .

# Runs cnormitek on the files in the `dir` folder
# and reports according to the 2020 coding style rules
$ cnormitek --cs-2020 dir

# Runs cnormitek on the `file.c` file.
$ cnormitek file.c

# Runs cnormitek from the input stream (as a C source file)
cat code.c | cnormitek -

# Runs cnormitek from the input stream (as a C header file)
cat code.h | cnormitek --stdin-h -
```
