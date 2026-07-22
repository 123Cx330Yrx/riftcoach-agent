import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.retriever import LocalKnowledgeRetriever


def main():
    parser = argparse.ArgumentParser(description="Query the local RiftCoach knowledge base.")
    parser.add_argument("query", help="Natural-language retrieval query.")
    parser.add_argument("--knowledge-dir", default="data/rag_docs")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    retriever = LocalKnowledgeRetriever(Path(args.knowledge_dir))
    results = retriever.search(args.query, top_k=args.top_k)
    print(f"Documents: {retriever.document_count}; chunks: {retriever.chunk_count}")
    for index, result in enumerate(results, start=1):
        print(f"\n[{index}] {result.source} > {result.title} (score={result.score})")
        print(result.content)


if __name__ == "__main__":
    main()
