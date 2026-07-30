import unittest

from douyin_desc import get_longest_desc, is_garbage


class DescriptionHelpersTest(unittest.TestCase):
    def test_get_longest_desc_returns_longest_valid_value(self):
        data = {
            "aweme": {
                "desc": "这是作品文案",
                "nested": [{"desc": "这是一个更长的作品文案，用于测试提取逻辑"}],
            }
        }

        self.assertEqual(
            get_longest_desc(data),
            "这是一个更长的作品文案，用于测试提取逻辑",
        )

    def test_get_longest_desc_ignores_placeholders(self):
        data = {"items": [{"desc": "加载中"}, {"desc": "真正的作品描述"}]}

        self.assertEqual(get_longest_desc(data), "真正的作品描述")

    def test_is_garbage_rejects_empty_and_placeholder_text(self):
        self.assertTrue(is_garbage(""))
        self.assertTrue(is_garbage("页面加载中"))
        self.assertFalse(is_garbage("可以复制的作品文案"))


if __name__ == "__main__":
    unittest.main()
