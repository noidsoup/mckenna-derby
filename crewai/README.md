# CrewAI planner

Turns a task description into `.cursor/plans/PLAN.md` for the McKenna Derby repo.

## Requirements

- **Python 3.10–3.13** (CrewAI does not support 3.9; the main repo venv may be 3.9)
- `OPENAI_API_KEY` in `crewai/.env`

## Setup

```bash
cd crewai
cp .env.example .env
# edit .env — set OPENAI_API_KEY and optionally PLANNER_TASK

python3.10 -m venv .venv
source .venv/bin/activate
pip install -e .
# or, with CrewAI CLI installed globally:
crewai install
```

## Run

```bash
cd crewai
source .venv/bin/activate
crewai run
# or:
run_crew
```

Output:

- `crewai/plan_output.md`
- `.cursor/plans/PLAN.md` (copied automatically)

Pair with the global **plan-and-implement** skill to execute the plan task-by-task.
