import tempfile
import unittest
from pathlib import Path

from app.rag.retriever import LocalKnowledgeRetriever, split_markdown, tokenize


class RetrieverTests(unittest.TestCase):
    def test_markdown_is_split_by_headings(self):
        chunks = split_markdown("sample.md", "# 总则\n说明\n## 视野分\n视野复盘方法")
        self.assertEqual(2, len(chunks))
        self.assertEqual("视野分", chunks[1].title)

    def test_chinese_query_retrieves_relevant_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.md"
            path.write_text(
                "# 补刀\n补刀每分钟用于观察发育。\n## 视野\n视野分用于信息贡献复盘。",
                encoding="utf-8",
            )
            retriever = LocalKnowledgeRetriever(Path(directory))
            results = retriever.search("输局视野分为什么低", top_k=1)
            self.assertEqual("视野", results[0].title)

    def test_tokenizer_supports_english_metrics(self):
        tokens = tokenize("DPM 与伤害/分钟")
        self.assertIn("dpm", tokens)
        self.assertIn("伤害", tokens)


if __name__ == "__main__":
    unittest.main()
