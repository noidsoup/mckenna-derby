"""Entry point for the McKenna Derby planner crew."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from planner_crew.crew import PlannerCrew

CREWAI_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = CREWAI_DIR.parent
PLAN_OUTPUT = CREWAI_DIR / "plan_output.md"
CURSOR_PLAN = REPO_ROOT / ".cursor" / "plans" / "PLAN.md"


def run() -> None:
    load_dotenv(CREWAI_DIR / ".env")
    task = os.getenv(
        "PLANNER_TASK",
        "Add support for loading UK/Ireland horse-racing CSV from the hwaitt/horse-racing schema.",
    )
    inputs = {"task": task}
    result = PlannerCrew().crew().kickoff(inputs=inputs)
    markdown = str(result)
    PLAN_OUTPUT.write_text(markdown)
    CURSOR_PLAN.parent.mkdir(parents=True, exist_ok=True)
    CURSOR_PLAN.write_text(markdown)
    print(f"Plan written to {PLAN_OUTPUT}")
    print(f"Plan copied to {CURSOR_PLAN}")


if __name__ == "__main__":
    run()
