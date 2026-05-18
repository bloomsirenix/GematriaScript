#!/usr/bin/env python3
"""
GematriaScript - Main Entry Point
An esoteric programming language based on Hebrew gematria
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.bible_unified import main as bible_unified_main
from src.gematria_lang import main as gematria_lang_main
from src.gematria_compiler import main as gematria_compiler_main


def main():
    parser = argparse.ArgumentParser(
        description='GematriaScript - An esoteric programming language based on Hebrew gematria',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available modes:
  bible-unified    Process Bible Gematria programs with various output modes
  gematria-lang    Run GematriaScript interpreter
  gematria-compiler Compile GematriaScript files to bytecode
        """
    )
    
    parser.add_argument('mode', nargs='?', default='bible-unified',
                        choices=['bible-unified', 'gematria-lang', 'gematria-compiler'],
                        help='Operation mode (default: bible-unified)')
    parser.add_argument('--version', action='version', version='GematriaScript 1.0.0')
    
    # Parse known args, pass the rest to the sub-command
    args, remaining_args = parser.parse_known_args()
    
    # Route to appropriate sub-command
    if args.mode == 'bible-unified':
        # Modify sys.argv to pass remaining args to bible_unified
        sys.argv = ['bible-unified'] + remaining_args
        bible_unified_main()
    elif args.mode == 'gematria-lang':
        sys.argv = ['gematria-lang'] + remaining_args
        gematria_lang_main()
    elif args.mode == 'gematria-compiler':
        sys.argv = ['gematria-compiler'] + remaining_args
        gematria_compiler_main()


if __name__ == "__main__":
    main()
