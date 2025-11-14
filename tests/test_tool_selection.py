import unittest
from unittest.mock import patch

from app.agent import QuantumMindAgent


class TestToolSelectionStrategy(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = QuantumMindAgent()

    def test_google_search_scoring(self) -> None:
        assessment = self.agent._assess_tool_query(
            'google_search',
            "Quelle est la toute dernière actualité sur la réglementation IA en Europe aujourd'hui?",
            consider_cooldown=False,
        )
        self.assertTrue(assessment['should_run'])
        self.assertGreaterEqual(assessment['score'], assessment['threshold'])
        self.assertTrue(assessment['strong_hits'] or assessment['weak_hits'])

    def test_huggingface_detection(self) -> None:
        assessment = self.agent._assess_tool_query(
            'huggingface_models',
            'Peux-tu me recommander trois modèles HuggingFace pour le résumé en français?',
            consider_cooldown=False,
        )
        self.assertTrue(assessment['should_run'])
        self.assertGreaterEqual(assessment['score'], assessment['threshold'])

    def test_cooldown_respected_without_refresh(self) -> None:
        query = 'Donne-moi les dernières actualités sur la réglementation IA'
        with patch('time.time', side_effect=[1000.0, 1000.0]):
            assessment = self.agent._assess_tool_query('google_search', query)
            self.assertTrue(assessment['should_run'])
            self.agent._register_tool_usage('google_search')

        with patch('time.time', side_effect=[1010.0]):
            assessment = self.agent._assess_tool_query('google_search', query)
            self.assertFalse(assessment['should_run'])
            self.assertEqual(assessment['reason'], 'cooldown')

    def test_refresh_keyword_overrides_cooldown(self) -> None:
        query = 'Actualise les derniers résultats MT-Bench pour Mixtral stp'
        with patch('time.time', side_effect=[2000.0, 2000.0]):
            assessment = self.agent._assess_tool_query('ai_benchmarks', query)
            self.assertTrue(assessment['should_run'])
            self.agent._register_tool_usage('ai_benchmarks')

        with patch('time.time', side_effect=[2010.0]):
            assessment = self.agent._assess_tool_query('ai_benchmarks', query)
            self.assertTrue(assessment['should_run'])
            self.assertIn(assessment['reason'], {'cooldown_override', 'recent_repeat_allowed'})


if __name__ == '__main__':
    unittest.main()
