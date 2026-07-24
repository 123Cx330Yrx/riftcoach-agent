import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.rag.models import KnowledgeQuery


def main():
    parser = argparse.ArgumentParser(description="Query the local RiftCoach knowledge base.")
    parser.add_argument("query", help="Natural-language retrieval query.")
    parser.add_argument("--knowledge-dir", default="data/rag_docs")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    provider = LocalHybridKnowledgeProvider.from_directory(
        Path(args.knowledge_dir)
    )
    result = provider.search(KnowledgeQuery(text=args.query, top_k=args.top_k))
    print(
        f"Parents: {len(provider.corpus.parents)}; "
        f"children: {len(provider.corpus.children)}"
    )
    print(f"Provider: {result.provider}; abstained: {result.abstained}")
    print(f"Diagnostics: {dict(result.diagnostics)}")
    for hit in result.hits:
        print(
            f"\n[K{hit.rank}] {hit.metadata.source_id} > "
            f"{hit.metadata.title} (score={hit.score})"
        )
        print(hit.content)


if __name__ == "__main__":
    main()
