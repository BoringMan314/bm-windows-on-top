import os
import struct
import zlib

DIR = os.path.join(os.path.dirname(__file__), "icons")
W, H = 16, 16


def _px(x: int, y: int) -> tuple:
    if 1 <= x < W - 1 and 1 <= y < H - 1:
        return 50, 120, 210, 255
    return 240, 240, 240, 255


def _write_png_rgba(path: str) -> None:
    raw_data = b""
    for y in range(H):
        raw_data += b"\x00"
        for x in range(W):
            r, g, b, a = _px(x, y)
            raw_data += bytes((r, g, b, a))

    def _chunk(t: bytes, d: bytes) -> bytes:
        c = (zlib.crc32(t + d) & 0xFFFFFFFF) if t != b"" else 0
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", c)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    comp = zlib.compress(raw_data, 9)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_chunk(b"IHDR", ihdr))
        f.write(_chunk(b"IDAT", comp))
        f.write(_chunk(b"IEND", b""))


def _write_ico_pil() -> bool:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    im = Image.new("RGBA", (W, H), (50, 120, 210, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W - 1, H - 1], outline=(220, 220, 220, 255))
    im.save(os.path.join(DIR, "icon.ico"), format="ICO", sizes=[(W, H)])
    return True


def main() -> None:
    os.makedirs(DIR, exist_ok=True)
    p_png = os.path.join(DIR, "icon.png")
    _write_png_rgba(p_png)
    print("Wrote", p_png)
    p_ico = os.path.join(DIR, "icon.ico")
    if _write_ico_pil():
        print("Wrote", p_ico)
    else:
        print(
            "Note: 安裝 Pillow 後可產生 icon.ico: pip install pillow",
        )


if __name__ == "__main__":
    main()
