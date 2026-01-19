#!/usr/bin/env python
"""
Feature Mining Agent
====================
LangGraph-based agent for solid electrolyte ionic conductivity research

Usage:
    python main.py --use-fma                        # Run FMA extraction pipeline
    python main.py --use-fma --md-dir /path/to/md   # FMA with specific markdown directory
    python main.py --interactive                    # Interactive mode with Supervisor Agent
"""

import argparse
import os


def run_fma(args):
    from fma.graph import build_fma_workflow, run_fma_pipeline
    
    print("Initializing Feature Mining Agent (FMA)...")
    
    app = build_fma_workflow()
    print("   Workflow build complete")
    
    md_paths = None
    if args.md_dir:
        if os.path.isdir(args.md_dir):
            md_paths = [
                os.path.join(args.md_dir, f)
                for f in os.listdir(args.md_dir)
                if f.lower().endswith('.md')
            ]
            print(f"   Found {len(md_paths)} markdown files")
        else:
            print(f"   [ERROR] Directory not found: {args.md_dir}")
            return
    
    run_fma_pipeline(app, md_paths=md_paths, auto_approve=True)


def run_interactive():
    from fma.supervisor import run_supervisor_interactive
    run_supervisor_interactive()


def main():
    parser = argparse.ArgumentParser(description="Feature Mining Agent")
    
    parser.add_argument("--use-fma", action="store_true", help="Run FMA extraction pipeline")
    parser.add_argument("--md-dir", type=str, help="Directory containing markdown files")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode with Supervisor Agent")
    
    args = parser.parse_args()
    
    if args.interactive:
        run_interactive()
    elif args.use_fma:
        run_fma(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
