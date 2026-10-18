import unittest

from digest.html_report import render


class HtmlReportTests(unittest.TestCase):
    def test_numbering_survives_blank_lines(self):
        content = """# 晚报
## 本期最重要的5条
1. **甲**。

2. **乙**。
## 一、市场复盘
1. 甲。

2. 乙。
## 二、信息提炼
一条。
## 三、重大提示
无新增公告。
## 四、阅读提示
一条。
## 五、最终总结
重点明确。
## 完整7源覆盖表
|来源|结果|
|---|---|
|甲|已读|
"""
        result = render(content)
        self.assertEqual(result.count('<ol start="2">'), 2)

    def test_no_first_line_indent_and_combined_source(self):
        content = """# 晚报
## 本期最重要的5条
1. **新闻**正文。（来源：甲；乙）
## 一、市场复盘
今天上涨。
## 二、信息提炼
一条。
## 三、重大提示
无新增公告。
## 四、阅读提示
一条。
## 五、最终总结
重点明确。
## 完整7源覆盖表
|来源|结果|
|---|---|
|甲|已读|
"""
        result = render(content)
        self.assertIn("text-indent:0", result)
        self.assertIn("<ol>", result)
        self.assertIn("（来源：甲；乙）", result)
        self.assertIn("<table>", result)


if __name__ == "__main__":
    unittest.main()
