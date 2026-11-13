"""
Unit Tests for Upgrade 1 & 2:
Testing on December 2025 Official Papers:
- MPA-011 Dec 2025 Q5 and Q10 must be FULL_20M
- MPA-014 Dec 2025 Q5 and Q10 must be FULL_20M
- MPA-012 Dec 2025 Q5 and Q10 must be SPLIT_10_10
- MPA-013 Dec 2025 Q5 and Q10 must be SPLIT_10_10
- Testing OCR Thinker Alias Normalizer
"""

import unittest
import sys
import os

# Add parent path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.layer1_format_parser import classify_question_format_and_marks, normalize_thinker_aliases

class TestLayer1Upgrades(unittest.TestCase):
    def test_thinker_alias_normalization(self):
        sample_text_1 = "Examine the views of Chester Bernard on organisation and authority."
        norm_1, logs_1 = normalize_thinker_aliases(sample_text_1)
        self.assertIn("Chester Barnard", norm_1)
        self.assertEqual(len(logs_1), 1)
        self.assertEqual(logs_1[0]['original'], 'chester bernard')

        sample_text_2 = "Discuss Herbert A. S. Simon on decision-making."
        norm_2, logs_2 = normalize_thinker_aliases(sample_text_2)
        self.assertIn("Herbert A. Simon", norm_2)

        sample_text_3 = "Explain Riggsian contribution to administration."
        norm_3, logs_3 = normalize_thinker_aliases(sample_text_3)
        self.assertIn("Riggs", norm_3)

    def test_december_2025_mpa011(self):
        # MPA-011 Dec 2025 Q5: Single 20M note
        q5_text = 'Write a note on "Applied aspects of social justice".'
        res5 = classify_question_format_and_marks(q5_text, header_text="All questions carry equal marks. Maximum Marks: 100")
        self.assertEqual(res5['format'], 'FULL_20M')
        self.assertEqual(res5['total_marks'], 20)
        self.assertFalse(res5['has_subparts'])

        # MPA-011 Dec 2025 Q10: Single 20M note
        q10_text = 'Write a note on "Ethical Concerns in Administration".'
        res10 = classify_question_format_and_marks(q10_text, header_text="All questions carry equal marks. Maximum Marks: 100")
        self.assertEqual(res10['format'], 'FULL_20M')
        self.assertEqual(res10['total_marks'], 20)

    def test_december_2025_mpa014(self):
        # MPA-014 Dec 2025 Q5: Single 20M note
        q5_text = "Write a note on Training Methods."
        res5 = classify_question_format_and_marks(q5_text, header_text="All questions carry equal marks.")
        self.assertEqual(res5['format'], 'FULL_20M')
        self.assertEqual(res5['total_marks'], 20)

        # MPA-014 Dec 2025 Q10: Single 20M essay
        q10_text = "Define organisational development and describe its techniques for change."
        res10 = classify_question_format_and_marks(q10_text, header_text="All questions carry equal marks.")
        self.assertEqual(res10['format'], 'FULL_20M')
        self.assertEqual(res10['total_marks'], 20)

    def test_december_2025_mpa012(self):
        # MPA-012 Dec 2025 Q5: 10+10
        q5_text = """Write short notes in about 250 words each on the following : 10+10
(a) Relay Assembly Test Room Experiment by Elton Mayo
(b) Role of choice and behaviour in decision making"""
        res5 = classify_question_format_and_marks(q5_text, header_text="All questions carry equal marks.")
        self.assertEqual(res5['format'], 'SPLIT_10_10')
        self.assertEqual(res5['total_marks'], 20)
        self.assertEqual(res5['subpart_marks'], 10)
        self.assertTrue(res5['has_subparts'])

        # MPA-012 Dec 2025 Q10: 10+10
        q10_text = """Write short notes on the following in about 250 words each : 10+10
(a) Organisational Culture
(b) Minnowbrook III"""
        res10 = classify_question_format_and_marks(q10_text, header_text="All questions carry equal marks.")
        self.assertEqual(res10['format'], 'SPLIT_10_10')
        self.assertEqual(res10['total_marks'], 20)

    def test_december_2025_mpa013(self):
        # MPA-013 Dec 2025 Q5: 10+10
        q5_text = """Write short notes on the following in about 250 words each : 10+10
(a) Digital Governance
(b) Areas of judicial activitism"""
        res5 = classify_question_format_and_marks(q5_text, header_text="All questions carry equal marks.")
        self.assertEqual(res5['format'], 'SPLIT_10_10')
        self.assertEqual(res5['total_marks'], 20)

        # MPA-013 Dec 2025 Q10: 10+10
        q10_text = """Write short notes on the following in about 250 words : 10+10
(a) Trend extrapolation
(b) Accountability for good governance"""
        res10 = classify_question_format_and_marks(q10_text, header_text="All questions carry equal marks.")
        self.assertEqual(res10['format'], 'SPLIT_10_10')
        self.assertEqual(res10['total_marks'], 20)

if __name__ == '__main__':
    unittest.main()
