from pathlib import Path

from sqlalchemy import text

from app.models import Opportunity


def test_ingest_folder_endpoint(client, tmp_path: Path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "title,organization,deadline,url,tags,type\n"
        "Open Call,Org A,2026-05-01,https://example.com/a,art;grant,cfp\n",
        encoding="utf-8",
    )

    response = client.post(
        "/ingest/folder",
        json={"folder": str(tmp_path), "pattern": "*.csv"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows_read"] == 1
    assert body["rows_upserted"] == 1


def test_list_endpoint_filters(client, db_session):
    a = Opportunity(
        id="a" * 64,
        type="cfp",
        title="Art Opportunity",
        org="Org A",
        status="new",
        priority=2,
    )
    b = Opportunity(
        id="b" * 64,
        type="job",
        title="Engineering Job",
        org="Org B",
        status="applied",
        priority=5,
    )
    db_session.add_all([a, b])
    db_session.commit()

    resp = client.get("/opportunities", params={"type": "job", "status": "applied", "q": "Engineering"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert payload["items"][0]["type"] == "job"


def test_fts_search_when_available(client, db_session):
    db_session.execute(
        text("CREATE VIRTUAL TABLE opportunities_fts USING fts5(id UNINDEXED, title, org, location, description)")
    )

    item = Opportunity(
        id="c" * 64,
        type="cfp",
        title="Residency Fellowship",
        org="Test Org",
        description="An immersive arts residency",
        status="new",
        priority=1,
    )
    db_session.add(item)
    db_session.commit()

    db_session.execute(
        text(
            "INSERT INTO opportunities_fts (id, title, org, location, description) "
            "VALUES (:id, :title, :org, :location, :description)"
        ),
        {
            "id": item.id,
            "title": item.title,
            "org": item.org or "",
            "location": item.location or "",
            "description": item.description or "",
        },
    )
    db_session.commit()

    resp = client.get("/opportunities", params={"q": "fellowship"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == item.id
