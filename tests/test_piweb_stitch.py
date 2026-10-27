"""Synthetic row-coded screenshots exercise seams, scale, and error exits."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/llm-authoring-workflow/references/automation-recipes/stitch-screenshots.py'


@unittest.skipUnless(Image, 'Pillow required for image regression')
class StitchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        spec = importlib.util.spec_from_file_location('piweb_stitch', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def fixture(self, scale=1, left=2, top=2):
        segments = []
        for index, start in enumerate([0, 4, 6]):
            image = Image.new('RGB', (20*scale, 14*scale), 'white')
            for y in range(8*scale):
                for x in range(10*scale):
                    image.putpixel((self.module.pixel(left*scale)+x, self.module.pixel(top*scale)+y), ((start*scale+y)%256, x, 19))
            file = f'{index}.png'
            image.save(self.root/file)
            segments.append({'file':file,'scroll_top':start})
        return {'segments':segments,'container':{'left':left,'top':top,'width':10,'client_height':8,'content_height':14},'viewport':[20,14],'out':'merged.png'}

    def test_exact_pixels_overlap_dpr_and_fractional_origin(self):
        for scale, origin in [(1,2),(2,2),(2,2.5),(1,2.5)]:
            with self.subTest(scale=scale,origin=origin):
                plan=self.fixture(scale,origin,origin)
                result=self.module.stitch(plan,self.root)
                with Image.open(result['out']) as image:
                    self.assertEqual(image.size,(10*scale,14*scale))
                    self.assertEqual([image.getpixel((0,y))[0] for y in range(14*scale)],list(range(14*scale)))
                (self.root/'merged.png').unlink()

    def test_reject_gap_head_tail_order_empty_and_invalid_geometry(self):
        mutations=[lambda p:p['segments'].pop(0),lambda p:p['segments'].pop(),lambda p:p.update(segments=[]),lambda p:p['segments'].reverse(),lambda p:p['container'].update(top=-1),lambda p:p['container'].update(width=float('nan'))]
        for mutate in mutations:
            plan=self.fixture();mutate(plan)
            with self.assertRaises(ValueError):self.module.stitch(plan,self.root)
            self.assertFalse((self.root/'merged.png').exists())
        plan=self.fixture();plan['container']['content_height']=30;plan['segments'][1]['scroll_top']=9
        with self.assertRaisesRegex(ValueError,'Gap'):self.module.stitch(plan,self.root)

    def test_fractional_scroll_and_height_at_double_scale(self):
        plan=self.fixture(2,2.5,2.5)
        plan['container'].update(client_height=8.5,content_height=14.5)
        for seg,start in zip(plan['segments'],[0,4.5,6]):
            seg['scroll_top']=start
            img=Image.new('RGB',(40,28),'white')
            for y in range(17):
                for x in range(20):img.putpixel((5+x,5+y),(int(start*2+y),x,19))
            img.save(self.root/seg['file'])
        result=self.module.stitch(plan,self.root)
        with Image.open(result['out']) as image:
            self.assertEqual(image.height,29)
            self.assertEqual([image.getpixel((0,y))[0] for y in range(29)],list(range(29)))

    def test_strip_bounds_size_change_and_existing_output(self):
        plan=self.fixture();plan['bar_strip']={'file':'2.png','box':[2,10,12,14]}
        self.assertEqual(self.module.stitch(plan,self.root)['height'],18)
        with self.assertRaisesRegex(ValueError,'already exists'):self.module.stitch(plan,self.root)
        (self.root/'merged.png').unlink();plan['bar_strip']['box']=[2,10,12,16]
        with self.assertRaisesRegex(ValueError,'strip'):self.module.stitch(plan,self.root)
        Image.new('RGB',(2,2)).save(self.root/'1.png')
        with self.assertRaisesRegex(ValueError,'dimensions'):self.module.stitch(plan,self.root)

    def test_failure_exit_code_and_horizontal_tiling(self):
        plan=self.fixture();plan['segments']=[]
        plan_file=self.root/'plan.json';plan_file.write_text(json.dumps(plan),encoding='utf-8')
        result=subprocess.run([sys.executable,str(SCRIPT),'--plan',str(plan_file)],capture_output=True,text=True)
        self.assertEqual(result.returncode,1);self.assertFalse(json.loads(result.stdout)['ok'])
        img=Image.new('RGB',(800,60),'white')
        for x in range(800):
            for y in range(60):img.putpixel((x,y),(x%200,y,0))
        self.assertIn('平铺',self.module.check_tiling_artifact(img,'synthetic'))
