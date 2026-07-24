import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.evaluation import evaluate_retrieval, load_retrieval_cases
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.rag.legacy_provider import LegacyLocalKnowledgeProvider
from app.rag.retriever import LocalKnowledgeRetriever


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the current local RAG against a fixed retrieval set."
    )
    parser.add_argument("--knowledge-dir", default="data/rag_docs")
    parser.add_argument(
        "--provider",
        choices=("legacy", "hybrid"),
        default="legacy",
    )
    parser.add_argument(
        "--cases",
        default="data/evaluation/rag_retrieval_cases.json",
    )
    parser.add_argument("--output")
    parser.add_argument("--min-recall", type=float)
    parser.add_argument("--min-mrr", type=float)
    parser.add_argument("--min-ndcg", type=float)
    parser.add_argument("--max-no-answer-fpr", type=float)
    args = parser.parse_args()

    knowledge_dir = Path(args.knowledge_dir)
    if args.provider == "hybrid":
        provider = LocalHybridKnowledgeProvider.from_directory(knowledge_dir)
    else:
        provider = LegacyLocalKnowledgeProvider(
            LocalKnowledgeRetriever(knowledge_dir)
        )
    evaluation = evaluate_retrieval(
        provider,
        load_retrieval_cases(Path(args.cases)),
    )
    payload = asdict(evaluation)
    payload["provider"] = provider.provider_name

    output_path = Path(
        args.output
        or (
            "data/evaluation/results/rag_v1_hybrid_baseline.json"
            if args.provider == "hybrid"
            else "data/evaluation/results/rag_v0_1_baseline.json"
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Provider: {provider.provider_name}")
    print(f"Cases: {len(evaluation.cases)}")
    print(f"Recall@K: {evaluation.recall_at_k:.4f}")
    print(f"MRR: {evaluation.mrr:.4f}")
    print(f"nDCG@K: {evaluation.ndcg_at_k:.4f}")
    print(
        "No-answer false-positive rate: "
        f"{evaluation.no_answer_false_positive_rate:.4f}"
    )
    print(f"Saved: {output_path}")

    failures = []
    if (
        args.min_recall is not None
        and evaluation.recall_at_k < args.min_recall
    ):
        failures.append(
            f"Recall@K {evaluation.recall_at_k:.4f} < {args.min_recall:.4f}"
        )
    if args.min_mrr is not None and evaluation.mrr < args.min_mrr:
        failures.append(f"MRR {evaluation.mrr:.4f} < {args.min_mrr:.4f}")
    if args.min_ndcg is not None and evaluation.ndcg_at_k < args.min_ndcg:
        failures.append(
            f"nDCG@K {evaluation.ndcg_at_k:.4f} < {args.min_ndcg:.4f}"
        )
    if (
        args.max_no_answer_fpr is not None
        and evaluation.no_answer_false_positive_rate
        > args.max_no_answer_fpr
    ):
        failures.append(
            "No-answer false-positive rate "
            f"{evaluation.no_answer_false_positive_rate:.4f} "
            f"> {args.max_no_answer_fpr:.4f}"
        )

    if failures:
        print("Retrieval quality gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
