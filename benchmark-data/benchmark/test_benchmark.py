import unittest

from benchmark.benchmark import decimal_equal, levenshtein, rate, scalar_equal


class BenchmarkUnitTests(unittest.TestCase):
    def test_numeric_comparison_is_exact_after_decimal_normalization(self):
        self.assertTrue(decimal_equal(7000.0, "7000.00"))
        self.assertFalse(decimal_equal("7000.00", "7000.01"))

    def test_identifiers_are_exact(self):
        self.assertTrue(scalar_equal("10030290", "10030290"))
        self.assertFalse(scalar_equal("10030290", "1003029O"))

    def test_levenshtein_and_error_rates(self):
        self.assertEqual(levenshtein("kitten", "sitting"), 3)
        self.assertEqual(rate("a b", "a c", words=True), 0.5)


if __name__ == "__main__":
    unittest.main()
