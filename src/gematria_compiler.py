#!/usr/bin/env python3
"""
GematriaScript Compiler
Compiles GematriaScript to bytecode for faster execution
"""

import struct
from pathlib import Path
from .gematria_lang import HEBREW_GEMATRIA, Opcode, GematriaInterpreter
from typing import List, Tuple

class BytecodeCompiler:
    """Compiles GematriaScript to bytecode"""
    
    # Bytecode opcodes (1 byte each)
    BYTECODE_OPS = {
        Opcode.PTR_RIGHT: 0x01,
        Opcode.PTR_LEFT: 0x02,
        Opcode.INC: 0x03,
        Opcode.DEC: 0x04,
        Opcode.OUT: 0x05,
        Opcode.IN: 0x06,
        Opcode.LOOP_START: 0x07,
        Opcode.LOOP_END: 0x08,
        Opcode.SET: 0x09,
        Opcode.ADD_PTR: 0x0A,
        Opcode.ZERO: 0x0B,
        Opcode.COPY: 0x0C,
        Opcode.HALT: 0xFF,
    }
    
    def __init__(self):
        self.bytecode = []
        self.constants = []
    
    def compile_hebrew(self, hebrew_text: str) -> bytes:
        """Compile Hebrew text to bytecode"""
        self.bytecode = []
        interpreter = GematriaInterpreter()
        
        # Strip comments: remove everything after # on each line
        lines = hebrew_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if '#' in line:
                line = line[:line.index('#')]
            cleaned_lines.append(line)
        cleaned_code = '\n'.join(cleaned_lines)
        
        # Split into tokens (space-separated words, or individual characters if no spaces)
        tokens = []
        for line in cleaned_lines:
            line = line.strip()
            if not line:
                continue
            # If line contains spaces, split by spaces
            if ' ' in line:
                tokens.extend(line.split())
            else:
                # No spaces: each character is a token
                for char in line:
                    tokens.append(char)
        
        # Map each token to opcode
        for token in tokens:
            opcode, operand = interpreter.text_to_opcode(token)
            bytecode_op = self.BYTECODE_OPS.get(opcode, 0x00)
            if bytecode_op != 0x00:
                self.bytecode.append(bytecode_op)
                # For SET and ADD_PTR, emit operand as additional byte if available
                if operand is not None and opcode in (Opcode.SET, Opcode.ADD_PTR):
                    self.bytecode.append(operand % 256)
        
        # Add HALT at end
        self.bytecode.append(self.BYTECODE_OPS[Opcode.HALT])
        
        return bytes(self.bytecode)
    
    def compile_file(self, input_file: str, output_file: str = None):
        """Compile a GematriaScript file to bytecode"""
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Compile to bytecode
        bytecode = self.compile_hebrew(code)
        
        # Determine output filename
        if output_file is None:
            output_file = input_path.stem + '.gbc'
        
        # Write bytecode to file
        with open(output_file, 'wb') as f:
            # Write header
            f.write(b'GEMATRIA')  # Magic number
            f.write(struct.pack('<I', len(bytecode)))  # Bytecode length
            f.write(bytecode)  # Bytecode data
        
        print(f"Compiled {input_file} to {output_file}")
        print(f"  Bytecode size: {len(bytecode)} bytes")
        
        return output_file
    
    def compile_bible_programs(self, programs_dir: str, output_file: str):
        """Compile all Bible programs into single bytecode file"""
        programs_path = Path(programs_dir)
        
        if not programs_path.exists():
            raise FileNotFoundError(f"Programs directory not found: {programs_dir}")
        
        print(f"Compiling all programs from {programs_dir}...")
        print("-" * 40)
        
        all_bytecode = []
        program_offsets = []
        total_size = 0
        
        # Compile each program
        programs = sorted(programs_path.glob("*.gs"))
        for i, prog_path in enumerate(programs):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(programs)}")
            
            try:
                with open(prog_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                bytecode = self.compile_hebrew(code)
                
                # Store offset and size
                program_offsets.append({
                    'name': prog_path.name,
                    'offset': total_size,
                    'size': len(bytecode)
                })
                
                all_bytecode.append(bytecode)
                total_size += len(bytecode)
                
            except Exception as e:
                print(f"  Error compiling {prog_path.name}: {e}")
        
        # Combine all bytecode
        combined_bytecode = b''.join(all_bytecode)
        
        # Write to file
        with open(output_file, 'wb') as f:
            # Write header
            f.write(b'BIBLEGEM')  # Magic number
            f.write(struct.pack('<I', len(programs)))  # Number of programs
            f.write(struct.pack('<I', len(combined_bytecode)))  # Total bytecode size
            
            # Write program index
            for prog in program_offsets:
                # Write program name (null-terminated, max 64 chars)
                name_bytes = prog['name'].encode('utf-8')[:63]
                f.write(name_bytes)
                f.write(b'\x00' * (64 - len(name_bytes)))
                f.write(struct.pack('<I', prog['offset']))
                f.write(struct.pack('<I', prog['size']))
            
            # Write bytecode data
            f.write(combined_bytecode)
        
        print(f"\nCompilation complete!")
        print(f"  Programs compiled: {len(programs)}")
        print(f"  Total bytecode size: {len(combined_bytecode)} bytes")
        print(f"  Output file: {output_file}")
        
        return output_file

class BytecodeInterpreter:
    """Interprets compiled GematriaScript bytecode"""
    
    def __init__(self):
        self.tape = [0] * 30000
        self.pointer = 0
        self.pc = 0
        self.running = True
        self.output_buffer = []
        self.loop_map = {}
        self.interactive = False
    
    def load_bytecode(self, bytecode: bytes):
        """Load bytecode for execution"""
        self.bytecode = bytecode
        self.pc = 0
        self.pointer = 0
        self.tape = [0] * 30000
        self.output_buffer = []
        self.running = True
        
        # Build loop map
        self.build_loop_map()
    
    def build_loop_map(self):
        """Build map of loop start/end positions"""
        stack = []
        self.loop_map = {}
        
        for i, byte in enumerate(self.bytecode):
            if byte == 0x07:  # LOOP_START
                stack.append(i)
            elif byte == 0x08:  # LOOP_END
                if stack:
                    start = stack.pop()
                    self.loop_map[start] = i
                    self.loop_map[i] = start
    
    def run(self, interactive: bool = False) -> List[str]:
        """Run the bytecode"""
        self.interactive = interactive
        self.output_buffer = []
        
        while self.running and self.pc < len(self.bytecode):
            byte = self.bytecode[self.pc]
            
            # Execute instruction
            if byte == 0x01:  # PTR_RIGHT
                self.pointer = (self.pointer + 1) % len(self.tape)
            
            elif byte == 0x02:  # PTR_LEFT
                self.pointer = (self.pointer - 1) % len(self.tape)
            
            elif byte == 0x03:  # INC
                self.tape[self.pointer] = (self.tape[self.pointer] + 1) % 256
            
            elif byte == 0x04:  # DEC
                self.tape[self.pointer] = (self.tape[self.pointer] - 1) % 256
            
            elif byte == 0x05:  # OUT
                value = self.tape[self.pointer]
                char = chr(value)
                self.output_buffer.append(char)
                print(char, end='')
            
            elif byte == 0x06:  # IN
                if self.interactive:
                    try:
                        user_input = input("> ")
                        char = user_input[0] if user_input else '\0'
                        self.tape[self.pointer] = ord(char) % 256
                    except:
                        self.tape[self.pointer] = 0
                else:
                    self.tape[self.pointer] = 0
            
            elif byte == 0x07:  # LOOP_START
                if self.tape[self.pointer] == 0 and self.pc in self.loop_map:
                    self.pc = self.loop_map[self.pc]
            
            elif byte == 0x08:  # LOOP_END
                if self.tape[self.pointer] != 0 and self.pc in self.loop_map:
                    self.pc = self.loop_map[self.pc]
            
            elif byte == 0xFF:  # HALT
                self.running = False
            
            self.pc += 1
        
        return self.output_buffer
    
    def run_compiled_file(self, bytecode_file: str, interactive: bool = False):
        """Load and run a compiled bytecode file"""
        with open(bytecode_file, 'rb') as f:
            # Read header
            magic = f.read(8)
            if magic != b'GEMATRIA':
                raise ValueError("Invalid bytecode file")
            
            bytecode_len = struct.unpack('<I', f.read(4))[0]
            bytecode = f.read(bytecode_len)
        
        self.load_bytecode(bytecode)
        return self.run(interactive)

def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 gematria_compiler.py <input_file> [output_file]")
        print("       python3 gematria_compiler.py --compile-bible <programs_dir> <output_file>")
        sys.exit(1)
    
    compiler = BytecodeCompiler()
    
    if sys.argv[1] == '--compile-bible':
        # Compile all Bible programs
        if len(sys.argv) < 4:
            print("Usage: python3 gematria_compiler.py --compile-bible <programs_dir> <output_file>")
            sys.exit(1)
        
        programs_dir = sys.argv[2]
        output_file = sys.argv[3]
        compiler.compile_bible_programs(programs_dir, output_file)
    
    else:
        # Compile single file
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        compiler.compile_file(input_file, output_file)

if __name__ == "__main__":
    main()
