import unittest
from unittest.mock import patch

import douyin_desc


class GarbageFilteringTest(unittest.TestCase):
    def test_rejects_exact_page_placeholders(self):
        for text in (
            "加载中",
            "抖音",
            "原创音乐",
            "网络错误，请点击重试",
            "抖音 - 记录美好生活",
        ):
            with self.subTest(text=text):
                self.assertTrue(douyin_desc.is_garbage(text))

    def test_keeps_legitimate_captions_containing_common_words(self):
        captions = [
            "我用抖音记录美好生活",
            "这是今天完成的一段原创音乐作品",
            "遇到网络错误以后重新出发",
        ]

        for text in captions:
            with self.subTest(text=text):
                self.assertFalse(douyin_desc.is_garbage(text))


class DescriptionSelectionTest(unittest.TestCase):
    def test_target_item_beats_longer_unrelated_desc(self):
        data = {
            "aweme_detail": {
                "aweme_id": "123456",
                "desc": "目标作品文案",
            },
            "recommendations": [
                {
                    "aweme_id": "999999",
                    "desc": "这是一段更长但属于推荐作品的文案，不应该覆盖目标作品。",
                }
            ],
        }

        desc, priority = douyin_desc.get_best_desc(data, item_id="123456")

        self.assertEqual(desc, "目标作品文案")
        self.assertEqual(priority, douyin_desc.DESC_PRIORITIES["json_target"])

    def test_primary_detail_beats_longer_generic_desc_without_item_id(self):
        data = {
            "payload": {
                "item_detail": {
                    "desc": "作品主体文案",
                }
            },
            "comments": [
                {
                    "desc": "评论区里更长的一段文字不应该覆盖 item_detail 的作品文案。",
                }
            ],
        }

        desc, priority = douyin_desc.get_best_desc(data)

        self.assertEqual(desc, "作品主体文案")
        self.assertEqual(priority, douyin_desc.DESC_PRIORITIES["json_detail"])

    def test_falls_back_to_longest_desc_when_structure_is_unknown(self):
        data = {
            "unknown": [
                {"desc": "短"},
                {"desc": "没有结构线索时使用更完整的候选文案"},
            ]
        }

        desc, priority = douyin_desc.get_best_desc(data)

        self.assertEqual(desc, "没有结构线索时使用更完整的候选文案")
        self.assertEqual(priority, douyin_desc.DESC_PRIORITIES["json_fallback"])

    def test_lower_priority_candidate_cannot_replace_targeted_desc(self):
        state = {"desc": None, "priority": -1}
        douyin_desc.consider_desc(
            state,
            "目标作品文案",
            douyin_desc.DESC_PRIORITIES["json_target"],
        )

        changed = douyin_desc.consider_desc(
            state,
            "这段 DOM 文本虽然更长，但来源可信度更低，不应该覆盖目标作品文案。",
            douyin_desc.DESC_PRIORITIES["dom_selector"],
        )

        self.assertFalse(changed)
        self.assertEqual(state["desc"], "目标作品文案")

    def test_equal_priority_keeps_more_complete_candidate(self):
        state = {
            "desc": "较短文案",
            "priority": douyin_desc.DESC_PRIORITIES["dom_selector"],
        }

        changed = douyin_desc.consider_desc(
            state,
            "同一来源中更完整的一段作品文案",
            douyin_desc.DESC_PRIORITIES["dom_selector"],
        )

        self.assertTrue(changed)
        self.assertEqual(state["desc"], "同一来源中更完整的一段作品文案")


class DescriptionCleanupTest(unittest.TestCase):
    def test_preserves_paragraphs_and_normalizes_inline_whitespace(self):
        text = "  第一行   有空格\r\n\r\n\r\n 第二行\\/路径  "

        self.assertEqual(
            douyin_desc.clean_desc_text(text),
            "第一行 有空格\n\n第二行/路径",
        )


class ItemIdExtractionTest(unittest.TestCase):
    def test_extracts_item_id_from_video_and_note_urls(self):
        self.assertEqual(
            douyin_desc.extract_item_id("https://www.douyin.com/video/123456"),
            "123456",
        )
        self.assertEqual(
            douyin_desc.extract_item_id("https://www.douyin.com/note/987654"),
            "987654",
        )

    def test_extracts_item_id_from_modal_query(self):
        self.assertEqual(
            douyin_desc.extract_item_id(
                "https://www.douyin.com/discover?modal_id=246810",
            ),
            "246810",
        )

    def test_rejects_ids_from_untrusted_hosts(self):
        self.assertIsNone(
            douyin_desc.extract_item_id("https://example.com/video/123456"),
        )


class ShortLinkRetryTest(unittest.TestCase):
    @patch("douyin_desc.requests.Session")
    def test_retries_transient_errors_but_not_rate_limits(self, session_class):
        session = session_class.return_value
        expected_response = object()
        session.get.return_value = expected_response

        response = douyin_desc.fetch_short_link(
            "https://v.douyin.com/ABC123/",
            {"User-Agent": "test"},
        )

        self.assertIs(response, expected_response)
        self.assertEqual(session.mount.call_count, 2)
        adapter = session.mount.call_args_list[0].args[1]
        retry = adapter.max_retries
        self.assertEqual(retry.total, 2)
        self.assertIn(503, retry.status_forcelist)
        self.assertNotIn(429, retry.status_forcelist)
        session.get.assert_called_once_with(
            "https://v.douyin.com/ABC123/",
            headers={"User-Agent": "test"},
            allow_redirects=False,
            timeout=(5, 10),
        )
        session.close.assert_called_once()

    @patch("douyin_desc.requests.Session")
    def test_closes_session_when_request_fails(self, session_class):
        session = session_class.return_value
        session.get.side_effect = douyin_desc.requests.ConnectionError("offline")

        with self.assertRaises(douyin_desc.requests.ConnectionError):
            douyin_desc.fetch_short_link(
                "https://v.douyin.com/ABC123/",
                {"User-Agent": "test"},
            )

        session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
