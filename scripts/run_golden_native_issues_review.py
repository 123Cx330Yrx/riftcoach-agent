"""Run one unchanged full-report control through the native issue-list candidate."""
from app.evaluation import golden_native_issues_review as candidate
from scripts.run_golden_native_review import main

if __name__ == '__main__':
    main(candidate_module=candidate)
