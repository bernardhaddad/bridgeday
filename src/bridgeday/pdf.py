"""A tiny PDF writer: rectangles, lines and Helvetica text. Standard library only.

Coordinates are in points from the top-left corner of the page, which is easier to lay
out than PDF's bottom-left origin. Text uses the built-in Helvetica fonts (no embedding),
so it is limited to Windows-1252; anything else is transliterated or replaced.
"""

from __future__ import annotations

import unicodedata
import zlib

A4_LANDSCAPE = (842.0, 595.0)
FONTS = {"regular": "F1", "bold": "F2"}
Color = tuple[float, float, float]


SUBSTITUTES = {
    "→": "»",
    "←": "«",
    "≥": ">=",
    "≤": "<=",
    # Letters that do not decompose into a base letter plus an accent.
    "Ł": "L",
    "ł": "l",
    "Đ": "D",
    "đ": "d",
    "Ħ": "H",
    "ħ": "h",
    "ı": "i",
    "ß": "ß",
}


def to_pdf_text(s: str) -> bytes:
    out = bytearray()
    for ch in s:
        ch = SUBSTITUTES.get(ch, ch)
        try:
            out += ch.encode("cp1252")
            continue
        except UnicodeEncodeError:
            pass
        base = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore")
        out += base or b"?"
    return bytes(out).replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_width(s: str, size: float, bold: bool = False) -> float:
    """Rough Helvetica advance width; good enough to fit and centre labels."""
    narrow = sum(1 for c in s if c in "iljtfrI.,:;'|!() ")
    wide = sum(1 for c in s if c in "MWmw@%")
    caps = sum(1 for c in s if c.isupper() or c.isdigit())
    avg = 0.5 * len(s) - 0.22 * narrow + 0.3 * wide + 0.12 * caps
    return avg * size * (1.06 if bold else 1.0)


def fit(s: str, size: float, width: float, bold: bool = False) -> str:
    if text_width(s, size, bold) <= width:
        return s
    while s and text_width(s + "…", size, bold) > width:
        s = s[:-1]
    return s.rstrip() + "…"


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Page:
    def __init__(self, size: tuple[float, float] = A4_LANDSCAPE):
        self.w, self.h = size
        self.ops: list[str] = []

    def _y(self, y: float) -> float:
        return self.h - y

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: Color | None = None,
        stroke: Color | None = None,
        width: float = 0.6,
    ) -> None:
        if fill is None and stroke is None:
            return
        ops = ["q"]
        if fill is not None:
            ops.append("{} {} {} rg".format(*map(_num, fill)))
        if stroke is not None:
            ops.append("{} {} {} RG {} w".format(*map(_num, stroke), _num(width)))
        ops.append(f"{_num(x)} {_num(self._y(y + h))} {_num(w)} {_num(h)} re")
        ops.append("B" if fill is not None and stroke is not None else "f" if fill else "S")
        ops.append("Q")
        self.ops.append(" ".join(ops))

    def line(self, x1: float, y1: float, x2: float, y2: float, color: Color, width=0.6) -> None:
        self.ops.append(
            "q {} {} {} RG {} w {} {} m {} {} l S Q".format(
                *map(_num, color),
                _num(width),
                _num(x1),
                _num(self._y(y1)),
                _num(x2),
                _num(self._y(y2)),
            )
        )

    def text(
        self,
        x: float,
        y: float,
        s: str,
        size: float = 10,
        bold: bool = False,
        color: Color = (0.11, 0.12, 0.14),
        align: str = "left",
        max_width: float | None = None,
    ) -> None:
        """y is the baseline, measured from the top."""
        if max_width:
            s = fit(s, size, max_width, bold)
        if align != "left":
            w = text_width(s, size, bold)
            x -= w if align == "right" else w / 2
        font = FONTS["bold" if bold else "regular"]
        body = to_pdf_text(s).decode("latin-1")
        self.ops.append(
            "BT /{} {} Tf {} {} {} rg {} {} Td ({}) Tj ET".format(
                font, _num(size), *map(_num, color), _num(x), _num(self._y(y)), body
            )
        )


class Document:
    def __init__(self, title: str, size: tuple[float, float] = A4_LANDSCAPE):
        self.title = title
        self.size = size
        self.pages: list[Page] = []

    def page(self) -> Page:
        p = Page(self.size)
        self.pages.append(p)
        return p

    def bytes(self) -> bytes:
        objs: list[bytes] = []

        def add(body: bytes) -> int:
            objs.append(body)
            return len(objs)

        catalog = add(b"")  # filled in below once the pages object exists
        pages_id = add(b"")
        font = "<< /Type /Font /Subtype /Type1 /BaseFont /{} /Encoding /WinAnsiEncoding >>"
        f1 = add(font.format("Helvetica").encode())
        f2 = add(font.format("Helvetica-Bold").encode())
        kids = []
        w, h = self.size
        for p in self.pages:
            stream = zlib.compress("\n".join(p.ops).encode("latin-1"))
            content = add(
                b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream)
                + stream
                + b"\nendstream"
            )
            kids.append(
                add(
                    (
                        f"<< /Type /Page /Parent {pages_id} 0 R "
                        f"/MediaBox [0 0 {_num(w)} {_num(h)}] "
                        f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >> "
                        f"/Contents {content} 0 R >>"
                    ).encode()
                )
            )
        objs[pages_id - 1] = (
            f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
        ).encode()
        objs[catalog - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
        info = add(b"<< /Title (" + to_pdf_text(self.title) + b") /Producer (bridgeday) >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
        trailer = b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\n" % (
            len(objs) + 1,
            catalog,
            info,
        )
        out += trailer + b"startxref\n%d\n%%%%EOF\n" % xref
        return bytes(out)
