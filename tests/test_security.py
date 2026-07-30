import json
import unittest

import douyin_desc


class UrlValidationTest(unittest.TestCase):
    def test_allows_douyin_and_subdomains(self):
        self.assertTrue(douyin_desc.is_allowed_douyin_url("https://douyin.com/video/1"))
        self.assertTrue(douyin_desc.is_allowed_douyin_url("https://www.douyin.com/note/1"))
        self.assertTrue(douyin_desc.is_allowed_douyin_url("https://v.douyin.com/ABC123/"))

    def test_rejects_lookalike_and_local_urls(self):
        rejected = [
            "https://douyin.com.evil.example/video/1",
            "https://douyin.com@evil.example/video/1",
            "http://127.0.0.1:5000/",
            "http://localhost/admin",
            "file:///etc/passwd",
        ]

        for url in rejected:
            with self.subTest(url=url):
                self.assertFalse(douyin_desc.is_allowed_douyin_url(url))

    def test_extracts_url_and_removes_share_text_punctuation(self):
        share_text = "复制链接打开抖音：https://v.douyin.com/ABC123/，查看作品"

        self.assertEqual(
            douyin_desc.extract_douyin_url(share_text),
            "https://v.douyin.com/ABC123/",
        )

    def test_rejects_oversized_input(self):
        text = "https://v.douyin.com/ABC123/" + ("x" * 4096)

        self.assertIsNone(douyin_desc.extract_douyin_url(text))

    def test_blocks_only_untrusted_main_frame_navigation(self):
        self.assertTrue(
            douyin_desc.should_block_navigation(
                "http://127.0.0.1/private",
                is_navigation_request=True,
                is_main_frame=True,
            )
        )
        self.assertFalse(
            douyin_desc.should_block_navigation(
                "https://www.douyin.com/video/1",
                is_navigation_request=True,
                is_main_frame=True,
            )
        )
        self.assertFalse(
            douyin_desc.should_block_navigation(
                "https://example-cdn.test/app.js",
                is_navigation_request=False,
                is_main_frame=True,
            )
        )
        self.assertFalse(
            douyin_desc.should_block_navigation(
                "https://captcha.example.test/frame",
                is_navigation_request=True,
                is_main_frame=False,
            )
        )


class ApiSecurityTest(unittest.TestCase):
    def setUp(self):
        self.client = douyin_desc.app.test_client()

    def test_rejects_invalid_json(self):
        response = self.client.post(
            "/api/extract",
            data="not-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_non_object_json(self):
        response = self.client.post("/api/extract", json=123)

        self.assertEqual(response.status_code, 400)

    def test_rejects_non_douyin_url_before_browser_launch(self):
        response = self.client.post(
            "/api/extract",
            json={"url": "http://127.0.0.1:5000/private"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "error")

    def test_rejects_oversized_request_body(self):
        response = self.client.post(
            "/api/extract",
            data=json.dumps({"url": "x" * (17 * 1024)}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 413)

    def test_returns_busy_when_browser_slot_is_occupied(self):
        acquired = douyin_desc.BROWSER_SEMAPHORE.acquire(blocking=False)
        self.assertTrue(acquired)
        try:
            response = self.client.post(
                "/api/extract",
                json={"url": "https://v.douyin.com/ABC123/"},
            )
        finally:
            douyin_desc.BROWSER_SEMAPHORE.release()

        self.assertEqual(response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
