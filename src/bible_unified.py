#!/usr/bin/env python3
"""
Unified Bible Gematria Processor
Processes .gs files using gematria esolang to generate images, videos, and MP4s
Supports all output modes: live preview, final image, video recording, screen recording with audio
"""

import sys
import subprocess
import cv2
import numpy as np
import math
import time
import signal
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab
from pathlib import Path
from multiprocessing import Pool, cpu_count
import argparse
import threading
import queue


def process_program(args):
    """Process a single program (module-level for multiprocessing)"""
    prog_path, programs_dir, use_cuda = args
    
    try:
        from src.gematria_compiler import BytecodeCompiler
        from src.gematria_hybrid_executor import HybridExecutor
        
        full_path = programs_dir / prog_path
        with open(full_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        compiler = BytecodeCompiler()
        bytecode = compiler.compile_hebrew(code)
        
        executor = HybridExecutor(use_cuda=use_cuda)
        result = executor.execute_program(bytecode, prog_path)
        
        return result
    except Exception as e:
        return {
            'program': prog_path,
            'target': 'cpu',
            'output': "Error: %s" % str(e),
            'output_length': 0,
            'success': False
        }


class GematriaProcessor:
    """Processes GematriaScript programs and yields byte output"""
    
    def __init__(self, use_cuda=True, workers=None):
        self.use_cuda = use_cuda
        self.workers = workers if workers else cpu_count()
        self.programs_dir = Path("bible_instructions")
        
    def process_all_programs(self, limit=None):
        """Process all .gs files and yield output bytes"""
        try:
            from src.gematria_lang import GematriaInterpreter
            from src.gematria_compiler import BytecodeCompiler
            from src.gematria_hybrid_executor import HybridExecutor
        except ImportError:
            yield b"Gematria modules not available\n"
            for i in range(10000):
                yield b"Placeholder data line %d\n" % i
            return
        
        if not self.programs_dir.exists():
            yield b"Programs directory not found\n"
            for i in range(10000):
                yield b"Placeholder data line %d\n" % i
            return
        
        programs = sorted(p.name for p in self.programs_dir.glob("*.gs"))
        
        if limit:
            programs = programs[:limit]
        
        yield b"Processing %d programs with %d workers\n" % (len(programs), self.workers)
        yield b"GPU mode: %s\n" % ('CUDA' if self.use_cuda else 'OpenCL').encode('utf-8')
        yield b"-" * 80 + b"\n"
        
        start_time = time.time()
        
        with Pool(self.workers) as pool:
            args_list = [(prog, self.programs_dir, self.use_cuda) for prog in programs]
            
            for i, result in enumerate(pool.imap_unordered(process_program, args_list)):
                if result['success'] and result.get('output'):
                    output = result['output']
                    if isinstance(output, bytes):
                        output = output.decode('utf-8', errors='ignore')
                    program_name = str(result.get('program', 'unknown'))
                    output_str = str(output)[:100]
                    output_line = b"%s: %s\n" % (program_name.encode('utf-8'), output_str.encode('utf-8'))
                    yield output_line
                
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    progress = b"Progress: %d/%d (%.1f%%)\n" % (i, len(programs), i/len(programs)*100)
                    yield progress
        
        elapsed = time.time() - start_time
        yield b"\nComplete! Processed %d programs in %.2fs\n" % (len(programs), elapsed)


class ImageGenerator:
    """Generates images from byte data"""
    
    @staticmethod
    def bytes_to_image(data, max_size=1024):
        """Convert bytes to numpy image array"""
        if len(data) < 3:
            return np.zeros((512, 512, 3), dtype=np.uint8)
        
        padding = (3 - len(data) % 3) % 3
        padded = data + b'\x00' * padding
        
        num_pixels = len(padded) // 3
        width = max(1, int(math.sqrt(num_pixels)))
        height = math.ceil(num_pixels / width)
        
        total = width * height * 3
        final_bytes = padded + b'\x00' * (total - len(padded))
        
        frame = np.frombuffer(final_bytes, dtype=np.uint8).reshape((height, width, 3))
        
        if width > max_size or height > max_size:
            scale = max_size / max(width, height)
            new_w = int(width * scale)
            new_h = int(height * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        
        return frame
    
    @staticmethod
    def bytes_to_ppm(data):
        """Convert bytes to PPM format for Tkinter"""
        if len(data) < 3:
            return None, 0, 0
        
        padding = (3 - len(data) % 3) % 3
        padded = data + b'\x00' * padding
        
        num_pixels = len(padded) // 3
        width = max(1, int(math.sqrt(num_pixels)))
        height = math.ceil(num_pixels / width)
        
        total_needed = width * height * 3
        final_data = padded + b'\x00' * (total_needed - len(padded))
        
        ppm_header = b"P6\n%d %d\n255\n" % (width, height)
        return ppm_header + final_data, width, height


class VideoRecorder:
    """Records video from byte stream"""
    
    def __init__(self, output_file, fps=20, max_size=1024, use_ffmpeg=True):
        self.output_file = output_file
        self.fps = fps
        self.max_size = max_size
        self.use_ffmpeg = use_ffmpeg
        self.data = bytearray()
        self.frame_count = 0
        self.writer = None
        self.ffmpeg_process = None
        self.start_time = time.time()
        self.running = True
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        print("\nStop signal received. Saving video...")
        self.running = False
    
    def get_frame(self):
        """Generate frame from current data"""
        return ImageGenerator.bytes_to_image(self.data, self.max_size)
    
    def start_ffmpeg(self, frame):
        """Initialize FFmpeg for streaming-safe MP4"""
        h, w = frame.shape[:2]
        
        # Check if FFmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("FFmpeg not found, falling back to OpenCV")
            self.use_ffmpeg = False
            self.start_cv2(frame)
            return
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{w}x{h}',
            '-r', str(self.fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+frag_keyframe+empty_moov+default_base_moov+faststart',
            self.output_file
        ]
        
        try:
            self.ffmpeg_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            print(f"FFmpeg started: {w}x{h} @ {self.fps}fps")
        except Exception as e:
            print(f"FFmpeg failed to start: {e}, falling back to OpenCV")
            self.use_ffmpeg = False
            self.start_cv2(frame)
    
    def start_cv2(self, frame):
        """Initialize OpenCV VideoWriter"""
        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.output_file, fourcc, self.fps, (w, h))
        if self.writer.isOpened():
            print(f"OpenCV VideoWriter started: {w}x{h} @ {self.fps}fps")
        else:
            print("Failed to initialize OpenCV VideoWriter")
            self.running = False
    
    def write_frame(self, frame):
        """Write frame to video"""
        if self.use_ffmpeg and self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.write(frame.tobytes())
            except (BrokenPipeError, OSError):
                pass
        elif self.writer:
            self.writer.write(frame)
    
    def cleanup(self):
        """Clean up resources"""
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.wait(timeout=10)
            except:
                self.ffmpeg_process.kill()
            self.ffmpeg_process = None
        
        if self.writer:
            self.writer.release()
        
        print(f"\nVideo saved: {self.output_file}")
        print(f"Frames: {self.frame_count}")
        print(f"Bytes: {len(self.data):,}")
        video_duration = self.frame_count / self.fps if self.fps > 0 else 0
        print(f"Video duration: {video_duration:.2f}s ({self.frame_count} frames @ {self.fps}fps)")
        print(f"Processing duration: {time.time() - self.start_time:.1f}s")


class ScreenRecorder:
    """Records screen with audio for live feed recording"""
    
    def __init__(self, output_file, fps=20):
        self.output_file = output_file
        self.fps = fps
        self.running = True
        self.frame_count = 0
        self.start_time = time.time()
        
        # Video capture
        self.video_queue = queue.Queue(maxsize=30)
        self.video_thread = None
        
        # FFmpeg process
        self.ffmpeg_process = None
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        print("\nStop signal received. Saving recording...")
        self.running = False
    
    def capture_screen(self, window=None):
        """Capture screen or specific window"""
        print("Screen capture started")
        
        while self.running:
            try:
                if window:
                    # Capture specific window
                    x = window.winfo_rootx()
                    y = window.winfo_rooty()
                    w = window.winfo_width()
                    h = window.winfo_height()
                    screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
                else:
                    # Capture entire screen
                    screenshot = ImageGrab.grab()
                
                # Convert to numpy array
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                self.video_queue.put(frame)
                
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"Screen capture error: {e}")
                time.sleep(0.1)
    
    def start_recording(self, window=None):
        """Start recording screen"""
        # Start video capture thread
        self.video_thread = threading.Thread(target=self.capture_screen, args=(window,), daemon=True)
        self.video_thread.start()
        
        # Wait for first frame to get dimensions
        time.sleep(0.5)
        if not self.video_queue.empty():
            first_frame = self.video_queue.get()
            h, w = first_frame.shape[:2]
            self.video_queue.put(first_frame)  # Put it back
        else:
            w, h = 1920, 1080  # Default resolution
        
        # Check if FFmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("FFmpeg not found, screen recording requires FFmpeg")
            self.running = False
            return
        
        # Start FFmpeg for video only
        cmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{w}x{h}',
            '-r', str(self.fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            self.output_file
        ]
        
        try:
            self.ffmpeg_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Recording started: {w}x{h} @ {self.fps}fps")
        except Exception as e:
            print(f"Failed to start FFmpeg: {e}")
            self.running = False
    
    def process_frames(self):
        """Process frames"""
        while self.running or not self.video_queue.empty():
            try:
                # Get video frame
                if not self.video_queue.empty():
                    frame = self.video_queue.get(timeout=0.1)
                    
                    # Write video frame
                    if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                        try:
                            self.ffmpeg_process.stdin.write(frame.tobytes())
                            self.frame_count += 1
                            
                            if self.frame_count % 30 == 0:
                                elapsed = time.time() - self.start_time
                                print(f"Recording: {self.frame_count} frames | {elapsed:.1f}s", end="\r")
                        except (BrokenPipeError, OSError) as e:
                            print(f"FFmpeg write error: {e}")
                            self.running = False
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Frame processing error: {e}")
                self.running = False
    
    def stop_recording(self):
        """Stop recording and save file"""
        self.running = False
        
        # Wait for thread to finish
        if self.video_thread:
            self.video_thread.join(timeout=2)
        
        # Close FFmpeg
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.wait(timeout=10)
                stderr = self.ffmpeg_process.stderr.read().decode()
                if stderr:
                    print(f"FFmpeg stderr: {stderr}")
            except:
                self.ffmpeg_process.kill()
        
        elapsed = time.time() - self.start_time
        video_duration = self.frame_count / self.fps if self.fps > 0 else 0
        print(f"\nRecording saved: {self.output_file}")
        print(f"Frames: {self.frame_count}")
        print(f"Video duration: {video_duration:.2f}s ({self.frame_count} frames @ {self.fps}fps)")
        print(f"Processing duration: {elapsed:.1f}s")


class LiveViewer:
    """Live GUI viewer for pixel stream"""
    
    def __init__(self, root, max_size=1024):
        self.root = root
        self.root.title("Unified Bible Gematria Viewer")
        self.root.configure(bg='black')
        
        self.canvas = tk.Canvas(root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.status = ttk.Label(root, text="Waiting for data...", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.data = bytearray()
        self.photo = None
        self.lock = threading.Lock()
        self.max_size = max_size
        self.running = True
        
    def update_data(self, chunk):
        """Add data to buffer"""
        with self.lock:
            self.data.extend(chunk)
    
    def update_display(self):
        """Update the display with current data"""
        with self.lock:
            if len(self.data) < 3:
                self.root.after(100, self.update_display)
                return
            
            ppm_data, w, h = ImageGenerator.bytes_to_ppm(self.data)
            
            if ppm_data:
                try:
                    photo = tk.PhotoImage(data=ppm_data)
                    
                    if w > self.max_size or h > self.max_size:
                        factor = max(1, max(w, h) // self.max_size)
                        photo = photo.subsample(factor)
                        w //= factor
                        h //= factor
                    
                    self.canvas.config(width=w, height=h)
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                    self.photo = photo
                    
                    self.status.config(text=f"Live: {w}x{h} pixels | {len(self.data):,} bytes")
                except:
                    pass
        
        if self.running:
            self.root.after(150, self.update_display)
    
    def stop(self):
        """Stop the viewer"""
        self.running = False


class UnifiedBibleProcessor:
    """Main unified processor class"""
    
    def __init__(self, mode='video', output_file=None, fps=20, max_size=1024, 
                 use_cuda=True, use_ffmpeg=True, enable_gui=False, limit=None):
        self.mode = mode
        self.output_file = output_file
        self.fps = fps
        self.max_size = max_size
        self.use_cuda = use_cuda
        self.use_ffmpeg = use_ffmpeg
        self.enable_gui = enable_gui
        self.limit = limit
        
        self.processor = GematriaProcessor(use_cuda=use_cuda)
        self.data = bytearray()
        
        if not self.output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if mode == 'video':
                self.output_file = f"bible_video_{timestamp}.mp4"
            elif mode == 'image':
                self.output_file = f"bible_image_{timestamp}.png"
            elif mode == 'screen':
                self.output_file = f"bible_screen_{timestamp}.mp4"
            else:
                self.output_file = f"bible_output_{timestamp}.bin"
    
    def run(self):
        """Main execution loop"""
        self.start_time = time.time()
        print(f"Mode: {self.mode}")
        print(f"Output: {self.output_file}")
        print(f"Processing with {'CUDA' if self.use_cuda else 'CPU'}\n")
        
        if self.mode == 'live':
            self.run_live_mode()
        elif self.mode == 'video':
            self.run_video_mode()
        elif self.mode == 'image':
            self.run_image_mode()
        elif self.mode == 'screen':
            self.run_screen_mode()
        else:
            self.run_raw_mode()
        
        # Print execution time
        elapsed = time.time() - self.start_time
        print(f"\nExecution time: {elapsed:.2f}s")
    
    def run_live_mode(self):
        """Run live GUI viewer mode"""
        root = tk.Tk()
        viewer = LiveViewer(root, self.max_size)
        
        def process_thread():
            generator = self.processor.process_all_programs(limit=self.limit)
            for chunk in generator:
                viewer.update_data(chunk)
        
        threading.Thread(target=process_thread, daemon=True).start()
        viewer.update_display()
        root.mainloop()
    
    def run_video_mode(self):
        """Run video recording mode"""
        recorder = VideoRecorder(self.output_file, self.fps, self.max_size, self.use_ffmpeg)
        viewer = None
        root = None
        
        if self.enable_gui:
            try:
                root = tk.Tk()
                viewer = LiveViewer(root, self.max_size)
                viewer.update_display()
                
                def gui_thread():
                    root.mainloop()
                
                threading.Thread(target=gui_thread, daemon=True).start()
            except Exception as e:
                print(f"Failed to initialize GUI: {e}")
                self.enable_gui = False
        
        generator = self.processor.process_all_programs(limit=self.limit)
        last_frame_time = time.time()
        
        try:
            for chunk in generator:
                self.data.extend(chunk)
                
                if not recorder.running:
                    print("Recorder stopped, exiting...")
                    break
                
                if time.time() - last_frame_time >= 1.0 / self.fps:
                    frame = recorder.get_frame()
                    
                    if recorder.use_ffmpeg and recorder.ffmpeg_process is None:
                        recorder.start_ffmpeg(frame)
                    elif not recorder.use_ffmpeg and recorder.writer is None:
                        recorder.start_cv2(frame)
                    
                    if recorder.running:
                        recorder.write_frame(frame)
                        recorder.frame_count += 1
                        last_frame_time = time.time()
                    
                    if self.enable_gui and viewer:
                        viewer.update_data(chunk)
                    
                    if recorder.frame_count % 10 == 0:
                        print(f"Frames: {recorder.frame_count:5d} | Bytes: {len(self.data):,}", end="\r")
        except Exception as e:
            print(f"\nError during video recording: {e}")
        finally:
            recorder.cleanup()
            
            if self.enable_gui and viewer:
                try:
                    viewer.stop()
                    if root:
                        root.quit()
                except:
                    pass
    
    def run_image_mode(self):
        """Run final image generation mode"""
        generator = self.processor.process_all_programs(limit=self.limit)
        
        try:
            for chunk in generator:
                self.data.extend(chunk)
                print(f"Received {len(self.data):,} bytes", end="\r")
        except Exception as e:
            print(f"\nError during processing: {e}")
            return
        
        print(f"\nGenerating image from {len(self.data):,} bytes...")
        
        try:
            frame = ImageGenerator.bytes_to_image(self.data, self.max_size)
        except Exception as e:
            print(f"Error generating image: {e}")
            return
        
        if self.enable_gui:
            try:
                root = tk.Tk()
                viewer = LiveViewer(root, self.max_size)
                viewer.data = self.data
                viewer.update_display()
                root.mainloop()
            except Exception as e:
                print(f"GUI error: {e}")
        
        try:
            cv2.imwrite(self.output_file, frame)
            print(f"Image saved: {self.output_file}")
            print(f"Size: {frame.shape[1]}x{frame.shape[0]}")
            print(f"Bytes processed: {len(self.data):,}")
        except Exception as e:
            print(f"Error saving image: {e}")
    
    def run_raw_mode(self):
        """Run raw byte output mode"""
        generator = self.processor.process_all_programs(limit=self.limit)
        
        try:
            with open(self.output_file, 'wb') as f:
                for chunk in generator:
                    f.write(chunk)
                    self.data.extend(chunk)
                    print(f"Written {len(self.data):,} bytes", end="\r")
        except Exception as e:
            print(f"\nError writing raw data: {e}")
            return
        
        print(f"\nRaw data saved: {self.output_file}")
        print(f"Total bytes: {len(self.data):,}")
    
    def run_screen_mode(self):
        """Run screen recording with audio mode"""
        try:
            root = tk.Tk()
            viewer = LiveViewer(root, self.max_size)
        except Exception as e:
            print(f"Failed to initialize GUI: {e}")
            print("Screen mode requires GUI support")
            return
        
        # Start screen recorder
        recorder = ScreenRecorder(self.output_file, self.fps)
        recorder.start_recording(window=root)
        
        if not recorder.running:
            print("Failed to start screen recorder")
            return
        
        # Start frame processing in background
        def process_frames_thread():
            recorder.process_frames()
        
        threading.Thread(target=process_frames_thread, daemon=True).start()
        
        # Process gematria programs and update viewer
        def process_thread():
            generator = self.processor.process_all_programs(limit=self.limit)
            try:
                for chunk in generator:
                    viewer.update_data(chunk)
            except Exception as e:
                print(f"Error processing programs: {e}")
        
        threading.Thread(target=process_thread, daemon=True).start()
        viewer.update_display()
        
        # Run GUI and stop recording when window closes
        try:
            root.mainloop()
        except Exception as e:
            print(f"GUI error: {e}")
        finally:
            recorder.stop_recording()


def main():
    parser = argparse.ArgumentParser(description='Unified Bible Gematria Processor')
    parser.add_argument('mode', choices=['live', 'video', 'image', 'raw', 'screen'], 
                        help='Output mode: live (GUI preview), video (MP4), image (PNG), raw (binary), screen (screen recording with audio)')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--fps', type=int, default=20, help='Video FPS (default: 20)')
    parser.add_argument('--size', type=int, default=1024, help='Max image/video size (default: 1024)')
    parser.add_argument('--no-cuda', action='store_true', help='Disable CUDA, use CPU only')
    parser.add_argument('--no-ffmpeg', action='store_true', help='Use OpenCV instead of FFmpeg for video')
    parser.add_argument('--gui', action='store_true', help='Enable GUI preview')
    parser.add_argument('--limit', type=int, help='Limit number of programs to process')
    
    args = parser.parse_args()
    
    processor = UnifiedBibleProcessor(
        mode=args.mode,
        output_file=args.output,
        fps=args.fps,
        max_size=args.size,
        use_cuda=not args.no_cuda,
        use_ffmpeg=not args.no_ffmpeg,
        enable_gui=args.gui,
        limit=args.limit
    )
    
    processor.run()


if __name__ == "__main__":
    main()
