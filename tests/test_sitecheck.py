#!/usr/bin/env python3

import unittest
import sitecheck
import time

class TestQuietHours(unittest.TestCase):
    def test_sitecheck_true_12_4_22(self):
        result = sitecheck.quiet_hours([12, 4], 22)
        self.assertEqual(result, True)

    def test_sitecheck_false_22_2_12(self):
        result = sitecheck.quiet_hours([22, 2], 12)
        self.assertEqual(result, False)

    def test_sitecheck_false_23_1_5(self):
        result = sitecheck.quiet_hours([23, 1], 5)
        self.assertEqual(result, False)

    def test_sitecheck_true_22_5_22(self):
        result = sitecheck.quiet_hours([22, 5], 22)
        self.assertEqual(result, True)

    def test_sitecheck_true_22_5_5(self):
        result = sitecheck.quiet_hours([22, 5], 5)
        self.assertEqual(result, True)

    def test_sitecheck_true_9_17_12(self):
        result = sitecheck.quiet_hours([9, 17], 12)
        self.assertEqual(result, True)

    def test_sitecheck_false_23_5_18(self):
        result = sitecheck.quiet_hours([23, 5], 18)
        self.assertEqual(result, False)

    def test_sitecheck_false_23_5_9(self):
        result = sitecheck.quiet_hours([23, 5], 9)
        self.assertEqual(result, False)

    def test_sitecheck_hours_false(self):
        result = sitecheck.quiet_hours(False, 9)
        self.assertEqual(result, False)


class TestIfPortIsDown(unittest.TestCase):
    def test_google_53_false(self):
        result = sitecheck.check_site_status('8.8.8.8', 53, 1)
        self.assertIsNone(result[1])
    def test_google_52_false(self):
        result = sitecheck.check_site_status('8.8.8.8', 52, 1)
        self.assertIsNotNone(result[1])




class TestRecentlyEmailed(unittest.TestCase):
    
    def test_recently_emailed_false(self):
        result = sitecheck.recently_emailed(time.time()-100)
        self.assertEqual(result, True)

    def test_emailable_true(self):
        result = sitecheck.recently_emailed(time.time()-18000)
        self.assertEqual(result, False)


if __name__ == '__main__':
    unittest.main()