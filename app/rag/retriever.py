import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


WORD_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    content: str
    score: float = 0.0


def tokenize(text: str) -> list[str]:
    normalized = text.lower()
    units = WORD_PATTERN.findall(normalized)
    chinese = "".join(unit for unit in units if "\u4e00" <= unit <= "\u9fff")
    bigrams = [chinese[index : index + 2] for index in range(len(chinese) - 1)]
    non_chinese = [unit for unit in units if not ("\u4e00" <= unit <= "\u9fff")]
    return units + bigrams + non_chinese


def split_markdown(source: str, text: str) -> list[KnowledgeChunk]:
    chunks = []
    title = Path(source).stem
    body_lines = []

    def flush() -> None:
        content = "\n".join(body_lines).strip()
        if content:
            chunks.append(KnowledgeChunk(source=source, title=title, content=content))
        body_lines.clear()

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            title = line.lstrip("#").strip() or title
        else:
            body_lines.append(line)
    flush()
    return chunks


class LocalKnowledgeRetriever:
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.chunks = []
        self.document_count = 0
        self._load()

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def _load(self) -> None:
        if not self.knowledge_dir.exists():
            raise FileNotFoundError(f"Knowledge directory not found: {self.knowledge_dir}")

        paths = sorted(self.knowledge_dir.glob("*.md"))
        self.document_count = len(paths)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.chunks.extend(split_markdown(path.name, text))

        if not self.chunks:
            raise RuntimeError(f"No Markdown knowledge found in: {self.knowledge_dir}")

        self._tokens = [Counter(tokenize(f"{chunk.title} {chunk.content}")) for chunk in self.chunks]
        self._document_frequency = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(tokens.keys())

    def search(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        query_tokens = Counter(tokenize(query))
        if not query_tokens or top_k <= 0:
            return []

        total = len(self.chunks)
        ranked = []
        for chunk, chunk_tokens in zip(self.chunks, self._tokens):
            score = 0.0
            for token, query_frequency in query_tokens.items():
                term_frequency = chunk_tokens.get(token, 0)
                if not term_frequency:
                    continue
                inverse_frequency = math.log((total + 1) / (self._document_frequency[token] + 0.5)) + 1
                score += (1 + math.log(term_frequency)) * inverse_frequency * query_frequency
            if score > 0:
                ranked.append(
                    KnowledgeChunk(
                        source=chunk.source,
                        title=chunk.title,
                        content=chunk.content,
                        score=round(score, 4),
                    )
                )

        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]


def format_evidence(chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return "未检索到可用知识。"

    sections = []
    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            f"[知识 {index}] 来源：{chunk.source}；章节：{chunk.title}\n{chunk.content}"
        )
    return "\n\n".join(sections)
