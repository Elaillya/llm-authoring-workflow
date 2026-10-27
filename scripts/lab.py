#!/usr/bin/env python3
from pathlib import Path
import sys
for stream in (sys.stdin,sys.stdout,sys.stderr):
    if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm_authoring.cli import main
raise SystemExit(main())
