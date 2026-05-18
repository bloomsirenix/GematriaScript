# GematriaScript

A **Turing-complete** esoteric programming language based on Hebrew gematria, designed to explore the concept of translating Biblical texts into executable programs to investigate simulation theory.

## Overview

GematriaScript is a Brainfuck-like esoteric programming language where Hebrew characters and words map to computational operations. It uses the ancient Hebrew practice of gematria (numerical value of words) to create a fully Turing-complete programming language capable of universal computation.

## Turing Completeness

GematriaScript is **Turing-complete** and can compute anything that any other programming language can compute. It follows the Brainfuck model with:

- **Memory tape**: 30,000 cells (like Brainfuck)
- **Pointer**: Can move left/right across the tape
- **Cell operations**: Increment, decrement, set, zero, copy
- **I/O operations**: Input and output
- **Conditional loops**: Proper loop matching and execution

This makes it computationally equivalent to Brainfuck and capable of universal computation.

## How It Works

### Hebrew Gematria Values

Each Hebrew letter has a numerical value:

```
א (Aleph) = 1    י (Yod) = 10     ק (Kuf) = 100
ב (Bet) = 2      כ (Kaf) = 20     ר (Resh) = 200
ג (Gimel) = 3    ל (Lamed) = 30   ש (Shin) = 300
ד (Dalet) = 4    מ (Mem) = 40     ת (Tav) = 400
ה (He) = 5       נ (Nun) = 50
ו (Vav) = 6      ס (Samekh) = 60
ז (Zayin) = 7    ע (Ayin) = 70
ח (Het) = 8      פ (Pe) = 80
ט (Tet) = 9      צ (Tsade) = 90
```

### Language Syntax (Brainfuck-like)

#### Single Character Mappings
For concise Brainfuck-like programming:

| Hebrew | Brainfuck | Operation |
|--------|-----------|-----------|
| א | > | Move pointer right |
| ב | < | Move pointer left |
| ג | + | Increment cell |
| ד | - | Decrement cell |
| ה | . | Output cell |
| ו | , | Input to cell |
| ז | [ | Start loop |
| ח | ] | End loop |
| ט | SET | Set cell to value |

#### Word Mappings
For more readable programs:

| Hebrew Word | Meaning | Operation |
|-------------|---------|-----------|
| ימין | right | PTR_RIGHT |
| שמאל | left | PTR_LEFT |
| ודא | add | INC |
| חסר | subtract | DEC |
| אמר | say | OUT |
| קבל | receive | IN |
| התחל | begin | LOOP_START |
| סיים | end | LOOP_END |
| שב | return | HALT |

### Example Programs

#### Simple Output (ASCII 10 - newline)
```hebrew
# Increment cell 10 times and output
גגגגגגגגגג  # INC 10 times
ה              # OUT
שב             # HALT
```

#### Loop Example
```hebrew
# Output 5 characters using a loop
גגגגג         # Set counter to 5
א              # Move to character cell
גגגגגגגגגגגגגגגגגגגגגגגגגגגגגגגגגגגג  # Set character to 42 ('*')
ב              # Move back to counter
ז              # Start loop
א              # Move to character
ה              # Output
ב              # Move back to counter
ד              # Decrement counter
א              # Move to character
ד              # Decrement character
ב              # Move back to counter
ח              # End loop
שב             # HALT
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run examples
python3 main.py gematria-lang examples/arithmetic.gs --debug
python3 main.py gematria-lang examples/loop.gs
```

## Usage

The unified app has three modes:

```bash
# Bible unified processor (default)
python3 main.py bible-unified <mode> [options]

# GematriaScript interpreter
python3 main.py gematria-lang <filename.gs> [--debug]

# GematriaScript compiler
python3 main.py gematria-compiler <input_file> [output_file]
python3 main.py gematria-compiler --compile-bible <programs_dir> <output_file>
```

### Building as a Standalone App

```bash
# Linux/Mac
./build.sh

# Windows
build.bat

# Or manually with PyInstaller
pyinstaller gematriascript.spec
```

The executable will be created in the `dist/` directory.

## Project Structure

```
gemtriascript/
├── main.py                 # Unified entry point
├── gematriascript.spec     # PyInstaller configuration
├── build.sh               # Linux/Mac build script
├── build.bat              # Windows build script
├── requirements.txt       # Python dependencies
├── src/                   # Core modules
│   ├── __init__.py
│   ├── gematria_lang.py          # Language interpreter
│   ├── gematria_compiler.py      # Bytecode compiler
│   ├── gematria_hybrid_executor.py  # CPU/GPU executor
│   ├── gematria_gpu_runner.py    # GPU execution
│   ├── gematria_elf_generator.py # ELF generation
│   └── bible_unified.py          # Bible processor
├── bible_instructions/    # Bible .gs programs
├── examples/              # Example programs
└── old/                   # Deprecated/experimental files
```

## Architecture

The interpreter consists of:
- **Gematria Calculator**: Converts Hebrew text to numerical values
- **Opcode Mapper**: Maps characters/words to Brainfuck-like operations
- **Tape Machine**: 30,000-cell memory tape with pointer (like Brainfuck)
- **Loop Matcher**: Builds matching pairs for loop operations
- **Parser**: Converts Hebrew text into executable instructions
- **Bytecode Compiler**: Compiles to bytecode for faster execution
- **Hybrid Executor**: Routes programs to CPU or GPU for optimal performance

## Bible Translation Project

The ultimate goal is to translate Biblical Hebrew texts into GematriaScript programs. This raises fascinating questions:
- Can ancient texts encode computational logic?
- What patterns emerge when Biblical verses are executed?
- Could this provide insights into simulation theory?

### Research Questions

1. Do specific verses produce meaningful computational outputs?
2. Are there hidden patterns in the gematria values of Biblical texts?
3. Can we identify "programs" within the text that produce coherent results?
4. Does the Torah contain universal computation capabilities?

## Philosophy

This project explores the intersection of:
- Ancient wisdom (Hebrew gematria)
- Modern computing (esoteric programming languages, Turing completeness)
- Metaphysical questions (simulation theory, hidden codes in sacred texts)
- Universal computation (can any text be a program?)

## Turing Completeness Proof

GematriaScript is Turing-complete because it implements all Brainfuck operations:
- Memory tape with unbounded cells (30,000 cells, circular)
- Pointer movement (PTR_RIGHT, PTR_LEFT)
- Cell modification (INC, DEC, SET, ZERO)
- I/O operations (OUT, IN)
- Conditional loops (LOOP_START, LOOP_END with proper matching)

Since Brainfuck is Turing-complete, and GematriaScript can directly simulate Brainfuck, GematriaScript is also Turing-complete.

## License

MIT License - Feel free to explore and experiment.

## Contributing

This is an experimental/artistic project. Contributions welcome, especially:
- Additional Biblical text analysis tools
- Pattern detection algorithms
- More sophisticated mapping schemes
- Visualization tools for execution traces
- Optimization techniques for Hebrew-to-opcode mapping
