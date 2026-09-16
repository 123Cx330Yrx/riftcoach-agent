"""Run one frozen development control with provisional-first full reassessment."""
from scripts.run_golden_integrated_review import main


if __name__ == "__main__":
    main(provisional=True)
