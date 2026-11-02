import json
from pathlib import Path

import pytest


def hol(day, name, *, nationwide=True, types=("Public",), counties=None, local=None):
    return {
        "date": day,
        "name": name,
        "localName": local or name,
        "global": nationwide,
        "types": list(types),
        "counties": counties,
    }


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    (d / "2027").mkdir(parents=True)
    (d / "2028").mkdir()
    countries = [{"countryCode": "DE", "name": "Germany"}, {"countryCode": "EG", "name": "Egypt"}]
    (d / "countries.json").write_text(json.dumps(countries))
    de27 = [
        hol("2027-01-01", "New Year's Day", local="Neujahr"),
        hol("2027-05-06", "Ascension Day", local="Christi Himmelfahrt"),  # Thursday
        hol("2027-03-08", "Women's Day", nationwide=False, counties=["DE-BE"]),
        hol("2027-12-25", "Christmas Day"),
        hol("2027-12-26", "St. Stephen's Day"),
        hol("2027-10-31", "Reformation Day", types=("Observance",)),
    ]
    (d / "2027" / "DE.json").write_text(json.dumps(de27))
    (d / "2028" / "DE.json").write_text(json.dumps([hol("2028-01-01", "New Year's Day")]))
    eg27 = [hol("2027-07-01", "<script>alert(1)</script> Day")]  # a Thursday
    (d / "2027" / "EG.json").write_text(json.dumps(eg27))
    return d
