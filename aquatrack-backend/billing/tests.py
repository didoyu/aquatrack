from django.test import TestCase

from billing.services import calculate_bill


class CowdBillTests(TestCase):
    """The three worked examples from the paper (business rule 6)."""

    def test_minimum_charge(self):
        self.assertEqual(float(calculate_bill(10)["total"]), 218.40)

    def test_15_cubic_meters(self):
        self.assertEqual(float(calculate_bill(15)["total"]), 371.15)

    def test_27_cubic_meters(self):
        self.assertEqual(float(calculate_bill(27)["total"]), 746.85)

    def test_top_tier(self):
        # 218.40 + 30.55*10 + 31.85*10 + 33.65*10 + 36.00*5
        self.assertEqual(float(calculate_bill(45)["total"]), 1358.90)
