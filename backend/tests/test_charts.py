"""Chart uploads: storage, serving, setlist exposure, and project isolation."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models import Setlist, SetlistItem, Song, SongChart
from tests.test_project_isolation import _as, _h, iso  # noqa: F401  (fixture)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _song(db, title="Mr. Jones") -> int:
    song = Song(title=title, artist="Counting Crows", type="cover", status="learning", project="solo")
    db.add(song)
    db.commit()
    return song.id


def _upload(client, song_id, name="mr-jones.png", data=PNG, headers=None):
    return client.post(
        "/api/charts",
        data={"song_id": str(song_id)},
        files={"file": (name, data, "application/octet-stream")},
        headers=headers or {},
    )


def test_upload_list_and_serve(client, db):
    sid = _song(db)
    res = _upload(client, sid)
    assert res.status_code == 200, res.text
    chart = res.json()
    assert chart["file_type"] == "png"
    assert chart["original_filename"] == "mr-jones.png"

    assert [c["id"] for c in client.get(f"/api/charts?song_id={sid}").json()] == [chart["id"]]

    served = client.get(f"/api/charts/{chart['id']}/file")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == PNG


def test_rejects_unsupported_format(client, db):
    assert _upload(client, _song(db), name="chart.gp5").status_code == 400


def test_setlist_items_include_charts(client, db):
    sid = _song(db)
    chart_id = _upload(client, sid).json()["id"]
    sl = Setlist(name="Gig")
    db.add(sl)
    db.flush()
    db.add(SetlistItem(setlist_id=sl.id, song_id=sid, position=0))
    db.commit()
    item = client.get(f"/api/setlists/{sl.id}").json()["items"][0]
    assert [c["id"] for c in item["charts"]] == [chart_id]


def test_delete_removes_chart_from_song(client, db):
    sid = _song(db)
    chart_id = _upload(client, sid).json()["id"]
    assert client.delete(f"/api/charts/{chart_id}").status_code == 200
    assert client.get(f"/api/charts?song_id={sid}").json() == []


def test_cloud_backend_serves_bytes_from_storage(client, db, monkeypatch):
    sid = _song(db)
    db.add(SongChart(song_id=sid, identifier="CHTEST001", file_type="pdf"))
    db.commit()
    chart_id = db.query(SongChart).one().id
    fake = MagicMock()
    fake.read_bytes.return_value = b"%PDF-1.4 fake"
    monkeypatch.setattr("app.routers.charts.get_backend", lambda: fake)

    res = client.get(f"/api/charts/{chart_id}/file")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content == b"%PDF-1.4 fake"
    fake.read_bytes.assert_called_once_with("CHTEST001", "pdf")


def test_integrity_does_not_report_charts_as_orphans(client, db):
    _upload(client, _song(db))
    report = client.get("/api/integrity/recordings").json()
    assert report["orphan_objects"] == []


def test_charts_are_project_scoped(client, db, iso):  # noqa: F811
    _as(client, iso.ua)
    res = _upload(client, iso.sa, headers=_h(iso.pa))
    assert res.status_code == 200, res.text
    chart_id = res.json()["id"]
    db.expunge_all()
    assert db.query(SongChart).get(chart_id).project_id == iso.pa

    _as(client, iso.uc)  # viewer of PA: can read, can't upload
    assert client.get(f"/api/charts/{chart_id}/file", headers=_h(iso.pa)).status_code == 200
    assert _upload(client, iso.sa, headers=_h(iso.pa)).status_code == 403

    _as(client, iso.ub)  # owner of PB: can't see PA's chart or attach to PA's song
    assert client.get(f"/api/charts/{chart_id}/file", headers=_h(iso.pb)).status_code == 404
    assert _upload(client, iso.sa, headers=_h(iso.pb)).status_code == 404
