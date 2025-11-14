import unittest
from unittest.mock import patch, Mock

from app.agent import QuantumMindAgent


class TestAIBenchmarkTool(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = QuantumMindAgent()

    @patch("app.agent.requests.get")
    def test_ai_benchmark_search_returns_top_three(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"id": "dataset/one", "downloads": 100, "likes": 10, "lastModified": "2025-01-10"},
            {"id": "dataset/two", "downloads": 80, "likes": 5, "lastModified": "2024-12-03"},
            {"id": "dataset/three", "downloads": 60, "likes": 2, "lastModified": "2024-11-01"},
            {"id": "dataset/four", "downloads": 40, "likes": 1, "lastModified": "2024-10-01"},
        ]
        mock_get.return_value = mock_response

        results = self.agent._perform_ai_benchmark_search("benchmarks pour NLP")

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["id"], "dataset/one")
        mock_get.assert_called_once()

    @patch("app.agent.requests.get")
    def test_ai_benchmark_search_fallback(self, mock_get: Mock) -> None:
        first_response = Mock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = []

        second_response = Mock()
        second_response.raise_for_status.return_value = None
        second_response.json.return_value = [
            {"id": "dataset/fallback", "downloads": 10, "likes": 0, "lastModified": "2024-10-05"},
        ]

        mock_get.side_effect = [first_response, second_response]

        results = self.agent._perform_ai_benchmark_search("SOTA vision benchmark")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "dataset/fallback")
        self.assertEqual(mock_get.call_count, 2)

    def test_format_ai_benchmark_results(self) -> None:
        sample = [
            {
                "id": "dataset/sample",
                "tags": ["task:text-classification", "modality:text"],
                "downloads": 123,
                "likes": 4,
                "lastModified": "2025-05-01T10:00:00.000Z",
            }
        ]

        formatted = self.agent._format_ai_benchmark_results(sample)

        self.assertIn("dataset/sample", formatted)
        self.assertIn("text-classification", formatted)
        self.assertIn("123 téléchargements", formatted)

    def test_should_search_ai_benchmarks_keywords(self) -> None:
        queries = [
            "Quel est le benchmark MMMU?",
            "Score MT-Bench pour les modèles open source",
            "Evaluation RLHF",
            "Classement GSM8K",
        ]

        for query in queries:
            with self.subTest(query=query):
                result = self.agent._assess_tool_query('ai_benchmarks', query, consider_cooldown=False)
                self.assertTrue(result['should_run'])


if __name__ == "__main__":
    unittest.main()
