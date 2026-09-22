"""Run one unchanged full-report control through the native issue-list candidate."""
from app.evaluation import golden_native_issues_review as candidate
from app.evaluation import golden_native_business_policy as business
from app.evaluation import golden_native_tool_review as tool
from app.evaluation import golden_native_partitioned_tool_review as partitioned_tool
from app.evaluation import golden_native_block_tool_review as block_tool
from app.evaluation import golden_native_buffered_block_review as buffered_block
from scripts.run_golden_native_review import main

if __name__ == '__main__':
    main(candidate_module=candidate, policy_variants={
        'business': business, 'tool': tool, 'partitioned-tool': partitioned_tool,
        'block-tool': block_tool, 'buffered-block': buffered_block})
