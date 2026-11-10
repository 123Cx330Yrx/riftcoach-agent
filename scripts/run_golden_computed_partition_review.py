"""Isolated full-context batch review; preview is free, execution is CI gated."""
from scripts.run_golden_integrated_review import main

if __name__ == "__main__":
    main(partition=True)
