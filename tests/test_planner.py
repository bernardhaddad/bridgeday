import re
import zipfile

from bridgeday.config import Config, ConfigError, Shop, load, slug
from bridgeday.pdf import Document, to_pdf_text
from bridgeday.products import build_products


def check_pdf(data: bytes) -> int:
    """Structural check: header, trailer, and every xref offset points at its object."""
    assert data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF")
    start = int(data.rsplit(b"startxref", 1)[1].split()[0])
    assert data[start:].startswith(b"xref")
    lines = data[start:].split(b"\n")
    count = int(lines[1].split()[1])
    for i in range(1, count):
        off = int(lines[2 + i].split()[0])
        assert data[off:].startswith(b"%d 0 obj" % i)
    return int(re.search(rb"/Count (\d+)", data).group(1))


def test_text_is_escaped_and_transliterated():
    assert to_pdf_text("a(b)c\\") == b"a\\(b\\)c\\\\"
    assert to_pdf_text("Ç → 中") == "Ç » ?".encode("cp1252")
    assert to_pdf_text("Ł") == b"L"


def test_document_structure():
    doc = Document("T (1)")
    doc.page().text(10, 10, "hello")
    doc.page().rect(0, 0, 10, 10, fill=(1, 0, 0))
    assert check_pdf(doc.bytes()) == 2


def test_products_build_every_planner_and_a_bundle(data_dir, tmp_path):
    out = tmp_path / "products"
    stats = build_products(Config(), data_dir, out, 2027)
    assert stats["planners"] == 2
    pdf = (out / "2027" / "germany-2027-leave-planner.pdf").read_bytes()
    assert check_pdf(pdf) == 17
    assert b"Germany 2027 leave and holiday planner" in pdf
    catalog = stats["catalog"].read_text()
    assert "germany-2027-leave-planner" in catalog and "Egypt 2027 Leave Planner" in catalog
    with zipfile.ZipFile(stats["bundle"]) as z:
        assert sorted(z.namelist()) == [
            "egypt-2027-leave-planner.pdf",
            "germany-2027-leave-planner.pdf",
        ]


def test_slug_matches_shopify_handles():
    assert slug("Bosnia and Herzegovina 2027 Leave Planner") == (
        "bosnia-and-herzegovina-2027-leave-planner"
    )
    assert slug("Côte d'Ivoire") == "cote-d-ivoire"


def test_shop_config(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        '[shop]\nurl = "https://s.example/products/{slug}-{year}-leave-planner"\n'
        'price = "$4.99"\ncountries = ["de", "US"]\n'
    )
    shop = load(p).shop
    assert shop.sells("DE") and shop.sells("us") and not shop.sells("FR")
    assert shop.link("DE", 2027, "Germany") == (
        "https://s.example/products/germany-2027-leave-planner"
    )
    assert Shop(url="https://x.example/{cc}", countries=frozenset({"*"})).sells("FR")
    assert not Shop(countries=frozenset({"*"})).sells("FR")  # no url, nothing to sell


def test_shop_config_rejects_bad_values(tmp_path):
    import pytest

    p = tmp_path / "config.toml"
    for text in (
        '[shop]\nurl = "http://plain.example/{cc}"\n',
        '[shop]\nurl = "https://{slug}.example/"\n',
        '[shop]\nurl = "https://s.example/{cc}"\ncountries = ["Germany"]\n',
    ):
        p.write_text(text)
        with pytest.raises(ConfigError):
            load(p)
