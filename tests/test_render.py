from pathlib import Path
import unittest
from llm_authoring.render import make_html


class RenderTests(unittest.TestCase):
    def test_chinese_code_uses_explicit_font_and_remains_escaped(self):
        result=make_html('```python\nprint("中文代码测试")\n<script>\n```\n\n`中文内联代码`\n\n    print("中文缩进代码")\n',
                         {'display_name':'Seed 2.1 Turbo','reply_sha256':'fixture'},'测试',Path('/tmp/font.otf'))
        self.assertIn('<span class="cjk-code">中文代码测试</span>',result)
        self.assertIn('<code><span class="cjk-code">中文内联代码</span></code>',result)
        self.assertIn('<span class="cjk-code">中文缩进代码</span>',result)
        self.assertIn('&lt;script&gt;',result);self.assertNotIn('<script>',result)
    def test_answer_html_and_remote_images_do_not_execute(self):
        result=make_html('# 中文\n\n<script>alert(1)</script>\n\n![图片](https://secret.example/track)\n\n|甲|乙|\n|---|---|\n|1|2|\n',
                         {'display_name':'Seed 2.1 Turbo','reply_sha256':'fixture'},'<秘密>题面',Path('/tmp/font.otf'))
        self.assertNotIn('<script>alert',result);self.assertNotIn('src="https://',result)
        self.assertIn('<table>',result);self.assertIn('&lt;秘密&gt;题面',result)
        self.assertIn('这不是模型官网、Arena',result);self.assertIn('完整回复结束',result)


if __name__=='__main__':unittest.main()
