"""One frozen whole-context development case, requiring exact clean-SHA CI.

Inspect actual claims, comparison bindings and explanations before starting
the second control. Old failed contextual entry remains offline_only.
"""
from scripts.run_golden_integrated_review import main


if __name__ == "__main__":
    main(comparison=True)
