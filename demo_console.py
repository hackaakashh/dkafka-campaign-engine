"""
Demo console — run this in a SECOND terminal while the main app is running.
Lets you simulate open / click / reply / bounce events live during the demo.

Usage:
    python -m aakash.demo_console
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aakash.ai_agent import AIAgent
from aakash.reply_detector import TestReplyHarness

harness = TestReplyHarness(AIAgent())

HELP = """
╔══════════════════════════════════════════════════════╗
  DEMO CONSOLE — simulate events while campaign runs
  ──────────────────────────────────────────────────
  open   <email>           → simulate email open
  click  <email>           → simulate link click
  reply  <email> <text>    → simulate a reply
  bounce <email>           → simulate hard bounce
  status                   → show subscriber states
  events                   → show recent event log
  help                     → show this menu
  quit                     → exit console
╚══════════════════════════════════════════════════════╝
"""

print(HELP)

while True:
    try:
        raw = input("demo › ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nConsole closed.")
        break

    if not raw:
        continue

    parts = raw.split(" ", 2)
    cmd   = parts[0].lower()

    if cmd == "open" and len(parts) >= 2:
        harness.simulate_open(parts[1])

    elif cmd == "click" and len(parts) >= 2:
        harness.simulate_click(parts[1])

    elif cmd == "reply" and len(parts) >= 3:
        harness.simulate_reply(parts[1], parts[2])

    elif cmd == "reply" and len(parts) == 2:
        text = input("  Reply text: ").strip()
        harness.simulate_reply(parts[1], text)

    elif cmd == "bounce" and len(parts) >= 2:
        harness.simulate_bounce(parts[1])

    elif cmd == "status":
        harness.print_status()

    elif cmd in ("events", "log"):
        harness.print_events()

    elif cmd == "help":
        print(HELP)

    elif cmd in ("quit", "exit", "q"):
        break

    else:
        print("Unknown command. Type 'help' for options.")
