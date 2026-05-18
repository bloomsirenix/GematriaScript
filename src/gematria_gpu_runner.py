#!/usr/bin/env python3
"""
GematriaScript GPU Acceleration
Runs GematriaScript bytecode on GPU using CUDA (via PyCUDA) or OpenCL (via PyOpenCL)
"""

import numpy as np
from typing import List, Tuple
from pathlib import Path

try:
    import pycuda.autoinit
    import pycuda.driver as cuda
    from pycuda.compiler import SourceModule
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False

try:
    import pyopencl as cl
    OPENCL_AVAILABLE = True
except ImportError:
    OPENCL_AVAILABLE = False

class GematriaGPUInterpreter:
    """GPU-accelerated GematriaScript interpreter"""
    
    def __init__(self, use_cuda: bool = True):
        self.use_cuda = use_cuda and CUDA_AVAILABLE
        self.use_opencl = not use_cuda and OPENCL_AVAILABLE
        
        if self.use_cuda:
            print("Using CUDA for GPU acceleration")
            self.init_cuda()
        elif self.use_opencl:
            print("Using OpenCL for GPU acceleration")
            self.init_opencl()
        else:
            # print("GPU acceleration not available, using CPU")
            pass
    
    def init_cuda(self):
        """Initialize CUDA"""
        self.context = pycuda.autoinit.context
        self.device = pycuda.autoinit.device
        
        # CUDA kernel for GematriaScript execution
        self.cuda_source = """
        __global__ void gematria_execute(
            unsigned char *bytecode,
            int bytecode_len,
            unsigned char *tape,
            int tape_size,
            int *pointer,
            unsigned char *output,
            int *output_len
        ) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int pc = 0;
            int ptr = *pointer;
            int out_idx = 0;
            int tape_local[30000];
            
            // Copy tape to local memory
            for (int i = 0; i < tape_size; i++) {
                tape_local[i] = tape[i];
            }
            
            // Execute bytecode
            while (pc < bytecode_len) {
                unsigned char op = bytecode[pc];
                
                switch (op) {
                    case 1:  // PTR_RIGHT
                        ptr = (ptr + 1) % tape_size;
                        break;
                    case 2:  // PTR_LEFT
                        ptr = (ptr - 1 + tape_size) % tape_size;
                        break;
                    case 3:  // INC
                        tape_local[ptr] = (tape_local[ptr] + 1) % 256;
                        break;
                    case 4:  // DEC
                        tape_local[ptr] = (tape_local[ptr] - 1 + 256) % 256;
                        break;
                    case 5:  // OUT
                        if (out_idx < 10000) {
                            output[out_idx] = tape_local[ptr];
                            out_idx++;
                        }
                        break;
                    case 6:  // IN
                        tape_local[ptr] = 0;  // Skip input in GPU mode
                        break;
                    case 7:  // LOOP_START
                        if (tape_local[ptr] == 0) {
                            // Find matching LOOP_END
                            int depth = 1;
                            while (depth > 0 && pc < bytecode_len) {
                                pc++;
                                if (bytecode[pc] == 7) depth++;
                                if (bytecode[pc] == 8) depth--;
                            }
                        }
                        break;
                    case 8:  // LOOP_END
                        if (tape_local[ptr] != 0) {
                            // Find matching LOOP_START
                            int depth = 1;
                            while (depth > 0 && pc >= 0) {
                                pc--;
                                if (bytecode[pc] == 8) depth++;
                                if (bytecode[pc] == 7) depth--;
                            }
                        }
                        break;
                    case 255:  // HALT
                        pc = bytecode_len;
                        break;
                }
                pc++;
            }
            
            // Copy back tape
            for (int i = 0; i < tape_size; i++) {
                tape[i] = tape_local[i];
            }
            
            *pointer = ptr;
            *output_len = out_idx;
        }
        """
        
        self.cuda_module = SourceModule(self.cuda_source)
        self.gematria_execute = self.cuda_module.get_function("gematria_execute")
    
    def init_opencl(self):
        """Initialize OpenCL"""
        self.context = cl.create_some_context()
        self.queue = cl.CommandQueue(self.context)
        
        # OpenCL kernel for GematriaScript execution
        self.opencl_source = """
        __kernel void gematria_execute(
            __global unsigned char *bytecode,
            int bytecode_len,
            __global unsigned char *tape,
            int tape_size,
            __global int *pointer,
            __global unsigned char *output,
            __global int *output_len
        ) {
            int idx = get_global_id(0);
            int pc = 0;
            int ptr = *pointer;
            int out_idx = 0;
            int tape_local[30000];
            
            // Copy tape to local memory
            for (int i = 0; i < tape_size; i++) {
                tape_local[i] = tape[i];
            }
            
            // Execute bytecode
            while (pc < bytecode_len) {
                unsigned char op = bytecode[pc];
                
                if (op == 1) {  // PTR_RIGHT
                    ptr = (ptr + 1) % tape_size;
                } else if (op == 2) {  // PTR_LEFT
                    ptr = (ptr - 1 + tape_size) % tape_size;
                } else if (op == 3) {  // INC
                    tape_local[ptr] = (tape_local[ptr] + 1) % 256;
                } else if (op == 4) {  // DEC
                    tape_local[ptr] = (tape_local[ptr] - 1 + 256) % 256;
                } else if (op == 5) {  // OUT
                    if (out_idx < 10000) {
                        output[out_idx] = tape_local[ptr];
                        out_idx++;
                    }
                } else if (op == 6) {  // IN
                    tape_local[ptr] = 0;
                } else if (op == 7) {  // LOOP_START
                    if (tape_local[ptr] == 0) {
                        int depth = 1;
                        while (depth > 0 && pc < bytecode_len) {
                            pc++;
                            if (bytecode[pc] == 7) depth++;
                            if (bytecode[pc] == 8) depth--;
                        }
                    }
                } else if (op == 8) {  // LOOP_END
                    if (tape_local[ptr] != 0) {
                        int depth = 1;
                        while (depth > 0 && pc >= 0) {
                            pc--;
                            if (bytecode[pc] == 8) depth++;
                            if (bytecode[pc] == 7) depth--;
                        }
                    }
                } else if (op == 255) {  // HALT
                    pc = bytecode_len;
                }
                pc++;
            }
            
            // Copy back tape
            for (int i = 0; i < tape_size; i++) {
                tape[i] = tape_local[i];
            }
            
            *pointer = ptr;
            *output_len = out_idx;
        }
        """
        
        self.opencl_program = cl.Program(self.context, self.opencl_source).build()
        self.gematria_execute = self.opencl_program.gematria_execute
    
    def run_bytecode_cuda(self, bytecode: bytes) -> Tuple[str, int]:
        """Run bytecode using CUDA"""
        if not self.use_cuda:
            raise RuntimeError("CUDA not available")
        
        # Prepare data
        bytecode_np = np.array([b for b in bytecode], dtype=np.uint8)
        tape_np = np.zeros(30000, dtype=np.uint8)
        pointer_np = np.array([0], dtype=np.int32)
        output_np = np.zeros(10000, dtype=np.uint8)
        output_len_np = np.array([0], dtype=np.int32)
        
        # Copy to GPU
        bytecode_gpu = cuda.mem_alloc(bytecode_np.nbytes)
        tape_gpu = cuda.mem_alloc(tape_np.nbytes)
        pointer_gpu = cuda.mem_alloc(pointer_np.nbytes)
        output_gpu = cuda.mem_alloc(output_np.nbytes)
        output_len_gpu = cuda.mem_alloc(output_len_np.nbytes)
        
        cuda.memcpy_htod(bytecode_gpu, bytecode_np)
        cuda.memcpy_htod(tape_gpu, tape_np)
        cuda.memcpy_htod(pointer_gpu, pointer_np)
        cuda.memcpy_htod(output_gpu, output_np)
        cuda.memcpy_htod(output_len_gpu, output_len_np)
        
        # Execute kernel
        self.gematria_execute(
            bytecode_gpu, np.int32(len(bytecode)),
            tape_gpu, np.int32(30000),
            pointer_gpu, output_gpu, output_len_gpu,
            block=(1, 1, 1), grid=(1, 1)
        )
        
        # Copy back
        cuda.memcpy_dtoh(output_np, output_gpu)
        cuda.memcpy_dtoh(output_len_np, output_len_gpu)
        
        # Get output
        output_len = output_len_np[0]
        output = ''.join(chr(b) for b in output_np[:output_len])
        
        return output, output_len
    
    def run_bytecode_opencl(self, bytecode: bytes) -> Tuple[str, int]:
        """Run bytecode using OpenCL"""
        if not self.use_opencl:
            raise RuntimeError("OpenCL not available")
        
        # Prepare data
        bytecode_np = np.array([b for b in bytecode], dtype=np.uint8)
        tape_np = np.zeros(30000, dtype=np.uint8)
        pointer_np = np.array([0], dtype=np.int32)
        output_np = np.zeros(10000, dtype=np.uint8)
        output_len_np = np.array([0], dtype=np.int32)
        
        # Create buffers
        bytecode_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=bytecode_np)
        tape_buf = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=tape_np)
        pointer_buf = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=pointer_np)
        output_buf = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=output_np)
        output_len_buf = cl.Buffer(self.context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=output_len_np)
        
        # Execute kernel
        self.gematria_execute(
            self.queue, (1,), None,
            bytecode_buf, np.int32(len(bytecode)),
            tape_buf, np.int32(30000),
            pointer_buf, output_buf, output_len_buf
        )
        
        # Copy back
        cl.enqueue_copy(self.queue, output_np, output_buf)
        cl.enqueue_copy(self.queue, output_len_np, output_len_buf)
        self.queue.finish()
        
        # Get output
        output_len = output_len_np[0]
        output = ''.join(chr(b) for b in output_np[:output_len])
        
        return output, output_len
    
    def run_bytecode(self, bytecode: bytes) -> Tuple[str, int]:
        """Run bytecode using GPU (CUDA or OpenCL)"""
        if self.use_cuda:
            return self.run_bytecode_cuda(bytecode)
        elif self.use_opencl:
            return self.run_bytecode_opencl(bytecode)
        else:
            # Fallback to CPU
            from gematria_compiler import BytecodeInterpreter
            interpreter = BytecodeInterpreter()
            interpreter.load_bytecode(bytecode)
            output = interpreter.run(interactive=False)
            return ''.join(output), len(output)

class GPUBibleRunner:
    """Run Bible programs on GPU"""
    
    def __init__(self, use_cuda: bool = True):
        self.interpreter = GematriaGPUInterpreter(use_cuda)
    
    def run_compiled_bible(self, bytecode_file: str, limit: int = None):
        """Run compiled Bible bytecode on GPU"""
        import struct
        import time
        
        with open(bytecode_file, 'rb') as f:
            # Read header
            magic = f.read(8)
            if magic != b'BIBLEGEM':
                raise ValueError("Invalid Bible bytecode file")
            
            num_programs = struct.unpack('<I', f.read(4))[0]
            total_size = struct.unpack('<I', f.read(4))[0]
            
            print(f"Loading {num_programs} programs from {bytecode_file}")
            print(f"Total bytecode size: {total_size} bytes")
            
            # Read program index
            programs = []
            for i in range(num_programs):
                name = f.read(64).rstrip(b'\x00').decode('utf-8')
                offset = struct.unpack('<I', f.read(4))[0]
                size = struct.unpack('<I', f.read(4))[0]
                
                programs.append({
                    'name': name,
                    'offset': offset,
                    'size': size
                })
            
            # Read bytecode data
            bytecode_data = f.read(total_size)
            
            print(f"Loaded {len(programs)} programs")
        
        if limit:
            programs = programs[:limit]
            print(f"Processing first {limit} programs")
        
        print()
        print("Running programs on GPU...")
        print("-" * 40)
        
        results = []
        start_time = time.time()
        
        for i, prog in enumerate(programs):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"Progress: {i}/{len(programs)} | Rate: {rate:.1f} prog/sec")
            
            try:
                # Extract program bytecode
                start = prog['offset']
                end = start + prog['size']
                program_bytecode = bytecode_data[start:end]
                
                # Run on GPU
                output, output_len = self.interpreter.run_bytecode(program_bytecode)
                
                results.append({
                    'name': prog['name'],
                    'output': output,
                    'output_length': output_len
                })
                
            except Exception as e:
                results.append({
                    'name': prog['name'],
                    'output': f"Error: {str(e)}",
                    'output_length': 0
                })
        
        elapsed = time.time() - start_time
        
        # Generate report
        self.generate_report(results, elapsed)
        
        print()
        print("=" * 80)
        print("GPU EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Programs processed: {len(results)}")
        print(f"Time elapsed: {elapsed:.2f} seconds")
        print(f"Average rate: {len(results)/elapsed:.1f} prog/sec")
        print(f"Report saved to: bible_gpu_execution_report.txt")
    
    def generate_report(self, results: list, elapsed: float):
        """Generate execution report"""
        report = []
        report.append("=" * 80)
        report.append("GPU BIBLE GEMATRIASCRIPT EXECUTION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        processed = len(results)
        with_output = sum(1 for r in results if r['output_length'] > 0 and 'Error' not in r['output'])
        with_errors = sum(1 for r in results if 'Error' in r['output'])
        
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Programs processed: {processed}")
        report.append(f"Programs with output: {with_output}")
        report.append(f"Programs with errors: {with_errors}")
        report.append(f"Time elapsed: {elapsed:.2f} seconds")
        report.append(f"Average rate: {len(results)/elapsed:.1f} prog/sec")
        report.append("")
        
        # Statistics
        output_lengths = [r['output_length'] for r in results if r['output_length'] > 0 and 'Error' not in r['output']]
        if output_lengths:
            report.append("OUTPUT STATISTICS")
            report.append("-" * 40)
            report.append(f"Total output characters: {sum(output_lengths)}")
            report.append(f"Average output length: {sum(output_lengths)/len(output_lengths):.2f}")
            report.append(f"Max output length: {max(output_lengths)}")
            report.append(f"Min output length: {min(output_lengths)}")
            report.append("")
        
        # Programs with output
        report.append("PROGRAMS WITH OUTPUT (first 50)")
        report.append("-" * 40)
        output_programs = [r for r in results if r['output_length'] > 0 and 'Error' not in r['output']]
        
        for r in output_programs[:50]:
            output_preview = r['output'][:50] if len(r['output']) > 50 else r['output']
            report.append(f"{r['name']}: {repr(output_preview)}")
        
        if len(output_programs) > 50:
            report.append(f"... and {len(output_programs) - 50} more")
        
        report.append("")
        
        # Save report
        with open('bible_gpu_execution_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

def main():
    """Main entry point"""
    import sys
    
    bytecode_file = "bible_compiled.gbc"
    use_cuda = True
    limit = None
    
    if len(sys.argv) > 1:
        bytecode_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2] == '--opencl':
            use_cuda = False
        else:
            try:
                limit = int(sys.argv[2])
            except ValueError:
                print(f"Invalid limit: {sys.argv[2]}")
    
    if len(sys.argv) > 3:
        if sys.argv[3] == '--opencl':
            use_cuda = False
        else:
            try:
                limit = int(sys.argv[3])
            except ValueError:
                print(f"Invalid limit: {sys.argv[3]}")
    
    runner = GPUBibleRunner(use_cuda)
    runner.run_compiled_bible(bytecode_file, limit)

if __name__ == "__main__":
    main()
