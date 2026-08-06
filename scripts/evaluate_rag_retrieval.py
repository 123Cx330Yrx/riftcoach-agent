import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.evaluation import evaluate_retrieval, load_retrieval_dataset
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
    parser.add_argument(
        "--split",
        help="Evaluate only cases from this dataset split.",
    )
    parser.add_argument(
        "--require-independent",
        action="store_true",
        help="Require a held-out dataset explicitly excluded from calibration.",
    )
    parser.add_argument("--output")
    parser.add_argument("--min-recall", type=float)
    parser.add_argument("--min-mrr", type=float)
    parser.add_argument("--min-ndcg", type=float)
    parser.add_argument("--max-no-answer-fpr", type=float)
    parser.add_argument("--min-abstention-accuracy", type=float)
    parser.add_argument("--min-citation-support", type=float)
    args = parser.parse_args()

    dataset = load_retrieval_dataset(Path(args.cases))
    if args.require_independent and (
        dataset.role != "held_out" or not dataset.calibration_excluded
    ):
        raise SystemExit(
            "Independent evaluation requires role=held_out and "
            "calibration_excluded=true."
        )

    cases = (
        tuple(case for case in dataset.cases if case.split == args.split)
        if args.split
        else dataset.cases
    )
    if not cases:
        raise SystemExit("No retrieval cases matched the requested split.")

    knowledge_dir = Path(args.knowledge_dir)
    if args.provider == "hybrid":
        provider = LocalHybridKnowledgeProvider.from_directory(knowledge_dir)
    else:
        provider = LegacyLocalKnowledgeProvider(
            LocalKnowledgeRetriever(knowledge_dir)
        )
    evaluation = evaluate_retrieval(
        provider,
        cases,
    )
    payload = asdict(evaluation)
    payload["provider"] = provider.provider_name
    payload["dataset_version"] = dataset.dataset_version
    payload["dataset_role"] = dataset.role
    payload["calibration_excluded"] = dataset.calibration_excluded
    payload["selected_split"] = args.split

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
    print(f"Dataset: {dataset.dataset_version} ({dataset.role})")
    print(f"Cases: {len(evaluation.cases)}")
    print(f"Recall@K: {evaluation.recall_at_k:.4f}")
    print(f"MRR: {evaluation.mrr:.4f}")
    print(f"nDCG@K: {evaluation.ndcg_at_k:.4f}")
    print(
        "No-answer false-positive rate: "
        f"{evaluation.no_answer_false_positive_rate:.4f}"
    )
    print(
        "Abstention accuracy: "
        f"{_format_metric(evaluation.abstention_accuracy)}"
    )
    print(
        "Citation support rate: "
        f"{_format_metric(evaluation.citation_support_rate)}"
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
    if args.min_abstention_accuracy is not None:
        if evaluation.abstention_accuracy is None:
            failures.append("Abstention accuracy has no annotated cases")
        elif evaluation.abstention_accuracy < args.min_abstention_accuracy:
            failures.append(
                "Abstention accuracy "
                f"{evaluation.abstention_accuracy:.4f} < "
                f"{args.min_abstention_accuracy:.4f}"
            )
    if args.min_citation_support is not None:
        if evaluation.citation_support_rate is None:
            failures.append("Citation support rate has no annotated cases")
        elif evaluation.citation_support_rate < args.min_citation_support:
            failures.append(
                "Citation support rate "
                f"{evaluation.citation_support_rate:.4f} < "
                f"{args.min_citation_support:.4f}"
            )

    if failures:
        print("Retrieval quality gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)


def _format_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    main()
