# 配方 v2（2026-10-26）：整视口分段拼长图；严格覆盖、比例与平铺校验。
#
# 用法：python stitch-screenshots.py --plan plan.json
# plan.json 在采集时生成，几何字段取"截图当时"实测值（勿用早前测量的旧值）：
# {
#   "segments": [                                  // 按 scroll_top 升序
#     {"file": "seg-00.png", "scroll_top": 0},
#     {"file": "seg-01.png", "scroll_top": 337}
#   ],
#   "container": {"left": 260, "top": 36, "width": 984,
#                  "client_height": 581, "content_height": 918},
#   "bar_strip": {"file": "seg-01.png", "box": [260, 615, 1244, 720]},  // 可选，底部栏条带
#   "out": "merged.png"
# }
#
# 输出：成功打印 {"ok": true, "out": ..., "width": ..., "height": ...}；
#       失败打印 {"ok": false, "reason": ...} 并退出 1；不覆盖已有图。
# 相对文件路径相对于 plan 所在目录；viewport: [CSS宽, CSS高] 可指定比例。
# 校验：每段逐列哈希查平铺伪影（只统计有墨迹的列，避免纯背景列的巧合匹配）；
#       分段裁剪按内容坐标衔接（各段覆盖 [scroll_top, scroll_top+client_height) 与
#       [0, content_height) 的交集，段间重叠按次序裁掉，无缺口无重复）。
# 依赖：Pillow（PIL）。几何单位为 CSS 像素，通过可选 viewport 字段自动换算 DPR；旧计划按 1:1。

import argparse
import json
import sys
import math
from pathlib import Path
from collections import Counter

from PIL import Image


def column_hashes(img):
    """每列的 RGB 哈希（按行采样），以及每列是否含墨迹（非背景像素）。"""
    w, h = img.size
    px = img.load()
    samples = list(range(0, h, 3))
    counter = Counter(px[x, y] for x in range(0, w, 3) for y in samples)
    background = counter.most_common(1)[0][0]
    hashes, inked = [], []
    for x in range(w):
        column = [px[x, y] for y in samples]
        hashes.append(hash(tuple(column)))
        inked.append(any(px[x, y] != background for y in samples))
    return hashes, inked


def check_tiling_artifact(img, label):
    """clip/fullPage 式横向平铺伪影：某偏移下右侧墨迹列大量等于左侧列。"""
    hashes, inked = column_hashes(img)
    w = img.size[0]
    for offset in range(200, w - 50):
        right_ink = [x for x in range(offset, w) if inked[x]]
        if not right_ink:
            continue
        dup = sum(1 for x in right_ink if hashes[x] == hashes[x - offset])
        if dup >= 40 and dup >= 0.9 * len(right_ink):
            return f"{label}: 疑似平铺伪影（偏移 {offset}，{dup}/{len(right_ink)} 墨迹列重复），弃用该段并整视口重截"
    return None


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), 'Invalid geometry number')
    return value


def pixel(value):
    return math.floor(value + .5)


def stitch(plan, directory=Path('.')):
    c = plan['container']
    left, top, width, client_h, content_h = [number(c[k]) for k in ('left', 'top', 'width', 'client_height', 'content_height')]
    require(left >= 0 and top >= 0 and min(width, client_h, content_h) > 0, 'Invalid container bounds')
    segments = plan['segments']
    require(isinstance(segments, list) and segments, 'No screenshot segments')
    directory = Path(directory)
    def location(name):
        p = Path(name)
        return p if p.is_absolute() else directory / p
    images = {}
    for seg in segments:
        with Image.open(location(seg['file'])) as source:
            images[seg['file']] = source.convert('RGB')
    size = next(iter(images.values())).size
    require(all(img.size == size for img in images.values()), 'Segment dimensions changed')
    viewport = plan.get('viewport', c.get('viewport', size))
    require(len(viewport) == 2 and all(number(v) > 0 for v in viewport), 'Invalid viewport')
    scale = size[0] / viewport[0]
    require(abs(size[1] - viewport[1] * scale) <= 1, 'Nonuniform screenshot scale')
    x0, x1 = pixel(left * scale), pixel((left + width) * scale)
    require(0 <= x0 < x1 <= size[0] and 0 <= pixel(top*scale) < pixel((top+client_h)*scale) <= size[1], 'Container exceeds screenshot')
    for name, img in images.items():
        problem = check_tiling_artifact(img, name)
        require(not problem, problem)
    parts, covered, previous = [], 0, -1
    for seg in segments:
        start = number(seg['scroll_top'])
        require(start >= 0 and start > previous and start <= max(0, content_h-client_h)+1e-6, 'Invalid or unordered scroll offsets')
        require(start <= covered + 1e-6, 'Gap in screenshot coverage')
        previous = start
        end = min(start + client_h, content_h)
        if end <= covered:
            continue
        # Round global content boundaries once; fractional seams cannot accumulate.
        height = pixel(end * scale) - pixel(covered * scale)
        y0 = pixel((top + covered - start) * scale)
        require(height > 0 and 0 <= y0 < y0 + height <= size[1], 'Crop exceeds screenshot')
        parts.append(images[seg['file']].crop((x0, y0, x1, y0+height)))
        covered = end
    require(abs(covered-content_h) <= 1e-6, 'Screenshot tail missing')
    bar = plan.get('bar_strip')
    if bar:
        require(bar['file'] in images, 'Status strip must come from a captured segment')
        require(len(bar['box']) == 4, 'Invalid status strip')
        box = [pixel(number(v) * scale) for v in bar['box']]
        a, b, d, e = box
        require(0 <= a < d <= size[0] and 0 <= b < e <= size[1] and d-a == x1-x0, 'Status strip out of bounds or wrong width')
        parts.append(images[bar['file']].crop(box))
    merged = Image.new('RGB', (x1-x0, sum(p.height for p in parts)))
    y = 0
    for part in parts:
        merged.paste(part, (0, y))
        y += part.height
    out = location(plan['out'])
    require(not out.exists(), 'Output already exists; preserve original evidence')
    try:
        with out.open('xb') as stream:
            merged.save(stream, format='PNG')
    except FileExistsError:
        raise
    except Exception:
        out.unlink(missing_ok=True)
        raise
    return {'ok': True, 'out': str(out), 'width': merged.width, 'height': merged.height, 'scale': scale}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    args = ap.parse_args()
    try:
        plan_path = Path(args.plan).resolve()
        result = stitch(json.loads(plan_path.read_text(encoding='utf-8')), plan_path.parent)
    except Exception as exc:
        print(json.dumps({'ok': False, 'reason': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
