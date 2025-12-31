#!/usr/bin/env python3
"""
Windows AI Agent - Main Entry Point
Offline AI-powered Windows control system using LLaMA 4 + MCP-style tools
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.cli import main

if __name__ == "__main__":
    main()
