"""JM 图片反分割（descramble），移植自原 JMComic-qt 的 tool.py.

JM 按章节将图片纵向切分为若干条并倒序堆叠，这里按原算法还原:
- 分割数由 epsId / scramble_id / 图片名经 md5 计算得出;
- 还原方式：将源图按高度等分为 num 条（余数归最后一条），倒序贴回新图.
"""

from __future__ import annotations

import hashlib
import io
import math
import re

from PIL import Image

# 与原项目 ParseBookEpsScramble 一致：解析失败时的兜底值
DEFAULT_SCRAMBLE_ID = 220980

# 解析 /media/photos/{epsId}/{pictureName}.{ext} 路径，用于反分割参数
_PHOTO_PATH_RE = re.compile(r"^media/photos/(\d+)/(.+)\.([A-Za-z0-9]+)$")


def parse_photo_path(path: str) -> tuple[str, str] | None:
    """从图片代理路径中提取 (epsId, pictureName).

    pictureName 为不含扩展名的文件名，与原项目 md5 计算所用的 pictureName 一致.
    """
    match = _PHOTO_PATH_RE.match(path)
    if not match:
        return None
    return match.group(1), match.group(2)


def get_segmentation_num(eps_id: str | int, scramble_id: str | int, picture_name: str) -> int:
    """获得图片分割数，移植自 tool.py ToolUtil.GetSegmentationNum."""
    scramble_id = int(scramble_id)
    eps_id = int(eps_id)
    if eps_id < scramble_id:
        return 0
    if eps_id < 268850:
        return 10
    digest = hashlib.md5((str(eps_id) + picture_name).encode()).hexdigest()
    last = ord(digest[-1])
    if eps_id > 421926:
        # num = (md5 末位字符码 % 8) * 2 + 2
        return (last % 8) * 2 + 2
    # num = (md5 末位字符码 % 10) * 2 + 2
    return (last % 10) * 2 + 2


def deslice_image(
    img_data: bytes,
    eps_id: str | int,
    scramble_id: str | int,
    picture_name: str,
) -> bytes:
    """按 JM 规则还原被纵向切分的图片，移植自 tool.py ToolUtil.SegmentationPicture.

    分割数 <= 1 时原样返回.
    """
    num = get_segmentation_num(eps_id, scramble_id, picture_name)
    if num <= 1:
        return img_data

    src_img = Image.open(io.BytesIO(img_data))
    width, height = src_img.size
    des_img = Image.new(src_img.mode, (width, height))
    fmt = src_img.format or "JPEG"

    rem = height % num
    copy_height = math.floor(height / num)
    blocks: list[tuple[int, int]] = []
    total_h = 0
    for i in range(num):
        h = copy_height * (i + 1)
        if i == num - 1:
            h += rem
        blocks.append((total_h, h))
        total_h = h

    h = 0
    for start, end in reversed(blocks):
        co_h = end - start
        des_img.paste(src_img.crop((0, start, width, end)), (0, h, width, h + co_h))
        h += co_h

    out = io.BytesIO()
    des_img.save(out, fmt)
    return out.getvalue()

