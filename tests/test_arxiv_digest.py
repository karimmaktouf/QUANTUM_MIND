import unittest
from unittest.mock import patch, Mock

from app.agent import QuantumMindAgent


class TestArxivDigestTool(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = QuantumMindAgent()

    def test_should_search_arxiv_digest_triggers_on_keywords(self) -> None:
        queries = [
            "Donne-moi un TLDR des derniers preprints",
            "Peux-tu résumer les publications arxiv récentes?",
            "Latest AI papers digest",
        ]
        for query in queries:
            with self.subTest(query=query):
                self.assertTrue(self.agent._should_search_arxiv_digest(query))

    def test_summarize_arxiv_abstract_limits_sentences(self) -> None:
        summary = (
            "We introduce a new transformer architecture for low-resource settings. "
            "Experiments on five benchmarks show consistent gains. "
            "Future work will explore multilingual extensions."
        )
        tldr = self.agent._summarize_arxiv_abstract(summary)
        self.assertIn("new transformer architecture", tldr.lower())
        self.assertNotIn("Future work", tldr)

    def test_format_arxiv_digest_results(self) -> None:
        sample = [
            {
                "title": "Awesome AI Paper",
                "link": "https://arxiv.org/abs/1234.56789",
                "pdf": "https://arxiv.org/pdf/1234.56789",
                "published": "2025-11-10",
                "authors": ["Alice Smith", "Bob Jones", "Carol Ray"],
                "summary": "This paper studies diffusion models for medical imaging and reports new SOTA results.",
            }
        ]

        formatted = self.agent._format_arxiv_digest_results(sample)
        self.assertIn("Awesome AI Paper", formatted)
        self.assertIn("TL;DR", formatted)
        self.assertIn("PDF", formatted)
        self.assertIn("Mots-clés", formatted)

    @patch("app.agent.requests.get")
    def test_perform_arxiv_digest_handles_api(self, mock_get: Mock) -> None:
        fake_feed = """
        <feed xmlns='http://www.w3.org/2005/Atom'>
            <entry>
                <title>Sample Paper</title>
                <summary>An approach to accelerate training of large models.</summary>
                <published>2025-11-12T10:00:00Z</published>
                <id>https://arxiv.org/abs/2511.12345</id>
                <author><name>Jane Doe</name></author>
                <author><name>John Roe</name></author>
                <link href='https://arxiv.org/pdf/2511.12345' rel='alternate' type='application/pdf' title='pdf'/>
            </entry>
        </feed>
        """
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = fake_feed
        mock_get.return_value = mock_response

        results = self.agent._perform_arxiv_digest("latest")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Sample Paper")
        mock_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
