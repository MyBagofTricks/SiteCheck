#!/usr/bin/env python3

import unittest
import sitecheck
import time
import asyncio

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class TestQuietHours(unittest.TestCase):
    
    @async_test
    def test_sitecheck_true_12_4_22(self):
        result = sitecheck.quiet_hours([12, 4], 22)
        self.assertEqual(result, True)
    @async_test
    def test_sitecheck_false_22_2_12(self):
        result = sitecheck.quiet_hours([22, 2], 12)
        self.assertEqual(result, False)
    @async_test
    def test_sitecheck_false_23_1_5(self):
        result = sitecheck.quiet_hours([23, 1], 5)
        self.assertEqual(result, False)
    @async_test
    def test_sitecheck_true_22_5_22(self):
        result = sitecheck.quiet_hours([22, 5], 22)
        self.assertEqual(result, True)
    @async_test
    def test_sitecheck_true_22_5_5(self):
        result = sitecheck.quiet_hours([22, 5], 5)
        self.assertEqual(result, True)
    @async_test
    def test_sitecheck_true_9_17_12(self):
        result = sitecheck.quiet_hours([9, 17], 12)
        self.assertEqual(result, True)
    @async_test
    def test_sitecheck_false_23_5_18(self):
        result = sitecheck.quiet_hours([23, 5], 18)
        self.assertEqual(result, False)
    @async_test
    def test_sitecheck_false_23_5_9(self):
        result = sitecheck.quiet_hours([23, 5], 9)
        self.assertEqual(result, False)
    @async_test
    def test_sitecheck_hours_false(self):
        result = sitecheck.quiet_hours(False, 9)
        self.assertEqual(result, False)


if __name__ == '__main__':
    unittest.main()