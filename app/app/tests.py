"""
sample test
"""
from django.test import SimpleTestCase
from app import calc


class CalcTests(SimpleTestCase):
    """Test the calc module."""

    def test_add_number(self):
        """Test adding two numbers"""
        res = calc.add(4, 5)
        self.assertEqual(res, 9)

    def test_subtract_numbers(self):
        """Test subtracting two numbers"""
        res = calc.subtract(10, 5)
        self.assertEqual(res, 5)
