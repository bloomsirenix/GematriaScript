#!/usr/bin/env python3
"""
GematriaScript - An esoteric programming language based on Hebrew gematria
Each Hebrew character maps to a numerical value, and these values drive program execution.
"""

import re
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Hebrew gematria values (standard system)
HEBREW_GEMATRIA = {
    # Aleph (1)
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    # Yod (10)
    'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90,
    # Kuf (100)
    'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400,
    # Final forms (same values as regular)
    'ך': 20, 'ם': 40, 'ן': 50, 'ף': 80, 'ץ': 900,
}

class Opcode(Enum):
    """Turing-complete operation codes based on Brainfuck model"""
    # Memory pointer operations (like Brainfuck > and <)
    PTR_RIGHT = 1      # Move pointer right (>)
    PTR_LEFT = 2       # Move pointer left (<)
    
    # Cell value operations (like Brainfuck + and -)
    INC = 3            # Increment cell (+)
    DEC = 4            # Decrement cell (-)
    
    # I/O operations (like Brainfuck . and ,)
    OUT = 5            # Output cell (.)
    IN = 6             # Input to cell (,)
    
    # Loop operations (like Brainfuck [ and ])
    LOOP_START = 7     # Start loop ([) - jump to matching ] if cell is 0
    LOOP_END = 8       # End loop (]) - jump back to matching [ if cell is non-zero
    
    # Additional operations for convenience
    SET = 9            # Set cell to specific value
    ADD_PTR = 10       # Add value to cell
    ZERO = 11          # Set cell to 0
    COPY = 12          # Copy current cell to next cell
    HALT = 13          # Halt execution

@dataclass
class Instruction:
    """A single instruction in GematriaScript"""
    opcode: Opcode
    operand: Optional[int] = None
    position: int = 0

class GematriaInterpreter:
    """Turing-complete interpreter for GematriaScript (Brainfuck-like)"""
    
    def __init__(self, tape_size: int = 30000):
        self.tape: List[int] = [0] * tape_size  # Memory tape
        self.pointer: int = 0  # Data pointer
        self.instructions: List[Instruction] = []
        self.pc: int = 0  # Program counter
        self.loop_map: Dict[int, int] = {}  # Map loop start/end positions
        self.output_buffer: List[str] = []
        self.running: bool = True
        
    def calculate_gematria(self, text: str) -> int:
        """Calculate gematria value of Hebrew text"""
        total = 0
        for char in text:
            if char in HEBREW_GEMATRIA:
                total += HEBREW_GEMATRIA[char]
        return total
    
    def text_to_opcode(self, text: str) -> Tuple[Opcode, Optional[int]]:
        """Convert Hebrew text to opcode and operand (Turing-complete version)
        
        Brainfuck-like mappings using Hebrew gematria:
        - Single letters map directly to opcodes 1-9
        - Words can also be used for readability
        """
        # Direct letter-to-opcode mappings (1-9)
        single_char_mappings = {
            'א': Opcode.PTR_RIGHT,   # Move pointer right
            'ב': Opcode.PTR_LEFT,    # Move pointer left
            'ג': Opcode.INC,         # Increment cell
            'ד': Opcode.DEC,         # Decrement cell
            'ה': Opcode.OUT,         # Output
            'ו': Opcode.IN,          # Input
            'ז': Opcode.LOOP_START,  # Loop start
            'ח': Opcode.LOOP_END,    # Loop end
            'ט': Opcode.SET,         # Set value
        }
        
        # Word mappings for readability
        word_mappings = {
            # Pointer movements
            'ימין': Opcode.PTR_RIGHT,   # "right"
            'שמאל': Opcode.PTR_LEFT,    # "left"
            'קדימה': Opcode.PTR_RIGHT,  # "forward"
            'אחור': Opcode.PTR_LEFT,    # "backward"
            
            # Cell operations
            'ודא': Opcode.INC,          # "add"
            'חסר': Opcode.DEC,          # "subtract"
            'גדל': Opcode.INC,          # "increase"
            'קטן': Opcode.DEC,          # "decrease"
            
            # I/O
            'אמר': Opcode.OUT,          # "say"
            'דבר': Opcode.OUT,          # "speak"
            'קבל': Opcode.IN,           # "receive"
            'שמע': Opcode.IN,           # "hear"
            
            # Loops
            'התחל': Opcode.LOOP_START,  # "begin"
            'סיים': Opcode.LOOP_END,    # "end"
            'עד': Opcode.LOOP_END,      # "until"
            'כל': Opcode.LOOP_END,      # "while"
            
            # Other
            'עצור': Opcode.HALT,        # "stop"
            'שב': Opcode.HALT,         # "return"
            'אפס': Opcode.ZERO,         # "zero"
            'העתק': Opcode.COPY,        # "copy"
        }
        
        # Check if single character
        if len(text) == 1 and text in single_char_mappings:
            return single_char_mappings[text], None
        
        # Check if word
        if text in word_mappings:
            return word_mappings[text], None
        
        # Calculate gematria and map to opcode
        value = self.calculate_gematria(text)
        
        # Map to opcode based on value mod 13 (number of opcodes)
        opcode_list = list(Opcode)
        opcode_index = (value - 1) % len(opcode_list)
        opcode = opcode_list[opcode_index]
        
        # Use remaining value as operand for SET operation
        if opcode == Opcode.SET:
            operand = value
        else:
            operand = None
            
        return opcode, operand
    
    def parse_hebrew(self, code: str) -> List[Instruction]:
        """Parse Hebrew text into instructions with loop matching"""
        instructions = []
        
        # Direct character-to-opcode mappings (same as compiler)
        char_mappings = {
            'א': Opcode.PTR_RIGHT,
            'ב': Opcode.PTR_LEFT,
            'ג': Opcode.INC,
            'ד': Opcode.DEC,
            'ה': Opcode.OUT,
            'ו': Opcode.IN,
            'ז': Opcode.LOOP_START,
            'ח': Opcode.LOOP_END,
            'ט': Opcode.SET,
        }
        
        # Remove comments
        lines = code.split('\n')
        cleaned_code = ''
        for line in lines:
            if '#' in line:
                line = line[:line.index('#')]
            cleaned_code += line
        
        # Process each character in the code
        for char in cleaned_code:
            if char in char_mappings:
                opcode = char_mappings[char]
                instructions.append(Instruction(opcode, None, len(instructions)))
        
        # Build loop map for matching [ and ]
        self.build_loop_map(instructions)
            
        return instructions
    
    def build_loop_map(self, instructions: List[Instruction]) -> None:
        """Build mapping between loop start and end positions"""
        stack = []
        self.loop_map = {}
        
        for i, inst in enumerate(instructions):
            if inst.opcode == Opcode.LOOP_START:
                stack.append(i)
            elif inst.opcode == Opcode.LOOP_END:
                if stack:
                    start = stack.pop()
                    self.loop_map[start] = i
                    self.loop_map[i] = start
    
    def execute(self, instruction: Instruction) -> None:
        """Execute a single instruction (Brainfuck-like)"""
        op = instruction.opcode
        
        if op == Opcode.PTR_RIGHT:
            # Move pointer right (>)
            self.pointer = (self.pointer + 1) % len(self.tape)
            
        elif op == Opcode.PTR_LEFT:
            # Move pointer left (<)
            self.pointer = (self.pointer - 1) % len(self.tape)
            
        elif op == Opcode.INC:
            # Increment cell at pointer (+)
            self.tape[self.pointer] = (self.tape[self.pointer] + 1) % 256
            
        elif op == Opcode.DEC:
            # Decrement cell at pointer (-)
            self.tape[self.pointer] = (self.tape[self.pointer] - 1) % 256
            
        elif op == Opcode.OUT:
            # Output cell at pointer (.)
            value = self.tape[self.pointer]
            self.output_buffer.append(chr(value))
            print(chr(value), end='')
            
        elif op == Opcode.IN:
            # Input to cell at pointer (,)
            if hasattr(self, 'interactive') and not self.interactive:
                # Non-interactive mode: skip input
                self.tape[self.pointer] = 0
            else:
                try:
                    user_input = input("> ")
                    char = user_input[0] if user_input else '\0'
                    self.tape[self.pointer] = ord(char) % 256
                except:
                    self.tape[self.pointer] = 0
                
        elif op == Opcode.LOOP_START:
            # Start loop ([) - jump to matching ] if cell is 0
            if self.tape[self.pointer] == 0 and self.pc in self.loop_map:
                self.pc = self.loop_map[self.pc]
                
        elif op == Opcode.LOOP_END:
            # End loop (]) - jump back to matching [ if cell is non-zero
            if self.tape[self.pointer] != 0 and self.pc in self.loop_map:
                self.pc = self.loop_map[self.pc]
                
        elif op == Opcode.SET:
            # Set cell to specific value
            if instruction.operand is not None:
                self.tape[self.pointer] = instruction.operand % 256
                
        elif op == Opcode.ADD_PTR:
            # Add value to cell
            if instruction.operand is not None:
                self.tape[self.pointer] = (self.tape[self.pointer] + instruction.operand) % 256
                
        elif op == Opcode.ZERO:
            # Set cell to 0
            self.tape[self.pointer] = 0
            
        elif op == Opcode.COPY:
            # Copy current cell to next cell
            next_ptr = (self.pointer + 1) % len(self.tape)
            self.tape[next_ptr] = self.tape[self.pointer]
            
        elif op == Opcode.HALT:
            self.running = False
    
    def run(self, code: str, debug: bool = False, interactive: bool = False) -> List[str]:
        """Run GematriaScript code (Turing-complete version)"""
        self.instructions = self.parse_hebrew(code)
        self.pc = 0
        self.pointer = 0
        self.tape = [0] * 30000  # Reset tape
        self.output_buffer.clear()
        self.running = True
        self.interactive = interactive  # Store interactive mode
        
        if debug:
            print(f"Parsed {len(self.instructions)} instructions")
            for i, inst in enumerate(self.instructions):
                print(f"{i}: {inst.opcode.name} {inst.operand or ''}")
            print()
        
        while self.running and self.pc < len(self.instructions):
            instruction = self.instructions[self.pc]
            
            if debug:
                print(f"PC={self.pc} | {instruction.opcode.name} {instruction.operand or ''} | Ptr={self.pointer} | Cell={self.tape[self.pointer]}")
            
            old_pc = self.pc
            self.execute(instruction)
            
            # Only increment PC if not jumped
            if self.pc == old_pc:
                self.pc += 1
        
        return self.output_buffer

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gematria_lang.py <hebrew_code_file> [--debug] [--non-interactive]")
        print("\nExample Hebrew words and their gematria values:")
        for char, value in list(HEBREW_GEMATRIA.items())[:10]:
            print(f"  {char}: {value}")
        sys.exit(1)
    
    filename = sys.argv[1]
    debug = '--debug' in sys.argv
    interactive = '--non-interactive' not in sys.argv
    
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()
    
    interpreter = GematriaInterpreter()
    output = interpreter.run(code, debug, interactive)
    
    print()  # Newline after output

if __name__ == "__main__":
    main()
