import json, subprocess
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.db import Session, Delivery, Campaign, Job, Record, DATA, engine
from app.services import execute, ffmpeg
import app.main as main


def contact(client, email="customer@example.com", consent=True):
    r = client.post(
        "/contacts",
        json={
            "name": "Customer",
            "email": email,
            "consent": consent,
            "consent_evidence": "Opt-in form 2026-11-03" if consent else "",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def campaign(client, cid, **extra):
    payload = {
        "name": "Campaign",
        "subject": "Hi {{name}}",
        "body": "An approved offer",
        "recipient_ids": [cid],
        "scheduled": (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat(),
        "daily_limit": 100,
        **extra,
    }
    return client.post("/campaigns", json=payload)


def test_auth_and_origin(client):
    assert client.get("/health", headers={"Authorization": "bad"}).status_code == 401
    assert client.get("/stats").status_code == 423
    assert client.post("/auth/setup", json={"password": "short"}).status_code == 422
    assert (
        client.post("/auth/setup", json={"password": "long-test-password"}).status_code
        == 200
    )
    assert (
        client.get("/stats", headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert client.post("/auth/lock").status_code == 200
    assert (
        client.post(
            "/auth/unlock", json={"password": "wrong-long-password"}
        ).status_code
        == 401
    )
    assert (
        client.post("/auth/unlock", json={"password": "long-test-password"}).status_code
        == 200
    )


def test_contact_import_and_consent(owner):
    data = b"name,email,country\nAlpha,alpha@example.com,IQ\nDuplicate,alpha@example.com,IQ\nInvalid,broken,IQ\n"
    result = owner.post(
        "/contacts/import", files={"file": ("contacts.csv", data, "text/csv")}
    )
    assert result.json() == {"added": 1, "duplicates": 1, "invalid_rows": [4]}
    cid = owner.get("/contacts").json()[0]["id"]
    assert campaign(owner, cid).status_code == 422
    assert (
        owner.post(
            "/contacts",
            json={"name": "No evidence", "email": "other@example.com", "consent": True},
        ).status_code
        == 422
    )
    assert owner.get("/stats").json()["eligible_contacts"] == 0


def test_campaign_requires_approval_rechecks_unsubscribe(owner, monkeypatch):
    cid = contact(owner)
    campaign_id = campaign(owner, cid).json()["id"]
    sent = []
    monkeypatch.setattr(main, "send_email", lambda *args: sent.append(args))
    assert not main.dispatch_one()
    assert not sent
    assert owner.post(f"/campaigns/{campaign_id}/approve").status_code == 200
    owner.post(f"/contacts/{cid}/unsubscribe")
    assert main.dispatch_one()
    assert not sent
    with Session() as s:
        assert s.scalar(select(Delivery)).status == "suppressed"


def test_send_records_only_confirmed_and_errors_pause(owner, monkeypatch):
    cid = contact(owner)
    campaign_id = campaign(owner, cid).json()["id"]
    sent = []
    owner.post(f"/campaigns/{campaign_id}/approve")
    monkeypatch.setattr(main, "send_email", lambda *args: sent.append(args))
    assert main.dispatch_one()
    assert len(sent) == 1
    assert "UNSUBSCRIBE" in sent[0][2]
    assert owner.get("/stats").json()["emails_sent"] == 1
    cid2 = contact(owner, "second@example.com")
    c2 = campaign(owner, cid2).json()["id"]
    owner.post(f"/campaigns/{c2}/approve")

    def fail(*args):
        raise RuntimeError("sensitive-provider-response")

    monkeypatch.setattr(main, "send_email", fail)
    main.save_setting("last_email_attempt", "")
    main.dispatch_one()
    with Session() as s:
        assert s.get(Campaign, c2).status == "paused"
    assert owner.get("/stats").json()["emails_failed"] == 1
    assert "sensitive-provider-response" not in owner.get("/campaigns").text


def test_daily_global_cap(owner, monkeypatch):
    cid = contact(owner)
    campaign_id = campaign(owner, cid).json()["id"]
    owner.post(f"/campaigns/{campaign_id}/approve")
    with Session.begin() as s:
        for _ in range(300):
            s.add(Delivery(campaign_id=campaign_id, contact_id=cid, status="sent"))
    monkeypatch.setattr(
        main,
        "send_email",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not send")),
    )
    assert not main.dispatch_one()


def test_finance_precise_separate_currencies_persists(owner):
    for direction, amount, currency in [
        ("revenue", 10001, "USD"),
        ("expense", 299, "USD"),
        ("revenue", 5000000, "IQD"),
    ]:
        assert (
            owner.post(
                "/finance",
                json={
                    "direction": direction,
                    "amount_minor": amount,
                    "currency": currency,
                    "description": "Payment",
                    "evidence": "receipt #1",
                    "confirmed": True,
                },
            ).status_code
            == 200
        )
    engine.dispose()
    stats = owner.get("/stats").json()
    assert stats["finance"]["USD"]["net_minor"] == 9702
    assert stats["finance"]["IQD"]["revenue_minor"] == 5000000
    assert stats["finance"]["USD"]["revenue_minor"] == 10001


def test_export_formula_and_secret_isolation(owner):
    contact(owner)
    owner.post(
        "/contacts", json={"name": '=HYPERLINK("bad")', "email": "formula@example.com"}
    )
    r = owner.get("/export/contacts")
    assert "'=HYPERLINK" in r.text
    assert owner.get("/records/setting:owner").status_code == 403
    assert (
        owner.post(
            "/settings/ai", json={"base_url": "http://example.com/v1", "model": "model"}
        ).status_code
        == 422
    )
    assert (
        owner.post(
            "/settings/ai",
            json={"base_url": "http://127.0.0.1:11434/v1", "model": "model"},
        ).status_code
        == 200
    )
    assert owner.get("/export/contacts?format=xlsx").content[:2] == b"PK"


def test_job_state_machine_and_missing_ai(owner):
    jid = owner.post(
        "/jobs", json={"department": "Sales Agent", "objective": "Draft a proposal"}
    ).json()["id"]
    assert owner.post(f"/jobs/{jid}/pause").status_code == 200
    assert owner.post(f"/jobs/{jid}/retry").status_code == 409
    assert owner.post(f"/jobs/{jid}/resume").status_code == 200
    execute(jid)
    with Session() as s:
        assert s.get(Job, jid).status == "failed"
    assert owner.post(f"/jobs/{jid}/retry").status_code == 200
    owner.post(f"/jobs/{jid}/cancel")
    execute(jid)
    with Session() as s:
        assert s.get(Job, jid).status == "cancelled"


def test_video_real_mp4_and_path_validation(owner, tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            ffmpeg(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-t",
            "1.2",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    with source.open("rb") as f:
        r = owner.post("/media", files={"file": ("source.mp4", f, "video/mp4")})
    assert r.status_code == 200, r.text
    jid = owner.post(
        "/jobs",
        json={
            "department": "Video Editor",
            "objective": "Export test clip",
            "options": {"file": r.json()["file"], "duration": 1, "format": "wide"},
        },
    ).json()["id"]
    execute(jid)
    with Session() as s:
        job = s.get(Job, jid)
        assert job.status == "completed", job.result
        result = json.loads(job.result)
    output = DATA / "exports" / result["file"]
    assert output.stat().st_size > 1000
    probe = subprocess.run(
        [ffmpeg(), "-i", str(output), "-f", "null", "-"], capture_output=True
    )
    assert probe.returncode == 0
    assert owner.get("/exports/" + result["file"]).status_code == 200
    assert (
        owner.post(
            "/jobs",
            json={
                "department": "Video Editor",
                "objective": "bad",
                "options": {"file": "../../secret.mp4"},
            },
        ).status_code
        == 422
    )


def test_smtp_tls_and_gmail_secret_not_in_db(owner, monkeypatch):
    import app.services as services

    events = []

    class SMTP:
        def __init__(self, *a, **kw):
            events.append(("connect", a))

        def ehlo(self):
            events.append("ehlo")

        def starttls(self, context):
            events.append("tls")
            assert context.check_hostname

        def login(self, *a):
            events.append("login")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(services.smtplib, "SMTP", SMTP)
    services.smtp_connect("sender@gmail.com", "1234567890123456")
    assert events[1:] == ["ehlo", "tls", "ehlo", "login"]
    saved = {}
    monkeypatch.setattr(main, "set_secret", lambda k, v: saved.update({k: v}))
    r = owner.post(
        "/gmail/save",
        json={"address": "sender@gmail.com", "app_password": "1234567890123456"},
    )
    assert r.status_code == 200
    with Session() as s:
        assert all(
            "1234567890123456" not in r.payload for r in s.scalars(select(Record))
        )
    assert saved["gmail"] == "1234567890123456"


def test_manager_plan_requires_human_approval_and_valid_tasks(owner, monkeypatch):
    import app.services as services

    monkeypatch.setattr(
        services,
        "ai",
        lambda *args: json.dumps(
            {
                "summary": "Launch service",
                "tasks": [
                    {"department": "Sales Agent", "objective": "Draft a quote"},
                    {
                        "department": "Marketing Agent",
                        "objective": "Draft Sorani captions",
                    },
                ],
            }
        ),
    )
    jid = owner.post(
        "/jobs",
        json={"department": "AI Manager", "objective": "Launch a digital service"},
    ).json()["id"]
    execute(jid)
    assert len(owner.get("/jobs").json()) == 1
    assert (
        owner.post(f"/plans/{jid}/approve", json={"task_indices": [0, 1]}).json()[
            "delegated"
        ]
        == 2
    )
    assert len(owner.get("/jobs").json()) == 3
    assert (
        owner.post(f"/plans/{jid}/approve", json={"task_indices": [0]}).status_code
        == 409
    )


def test_permissions_and_pacing_survive_restart(owner, monkeypatch):
    assert (
        owner.put("/permissions", json={"enabled": ["Sales Agent"]}).status_code == 200
    )
    assert (
        owner.post(
            "/jobs", json={"department": "Marketing Agent", "objective": "Disabled"}
        ).status_code
        == 403
    )
    assert (
        owner.post(
            "/jobs", json={"department": "Sales Agent", "objective": "Allowed"}
        ).status_code
        == 200
    )
    cid = contact(owner)
    campaign_id = campaign(owner, cid).json()["id"]
    owner.post(f"/campaigns/{campaign_id}/approve")
    sent = []
    monkeypatch.setattr(main, "send_email", lambda *args: sent.append(args))
    assert main.dispatch_one()
    engine.dispose()
    cid2 = contact(owner, "next@example.com")
    c2 = campaign(owner, cid2).json()["id"]
    owner.post(f"/campaigns/{c2}/approve")
    assert not main.dispatch_one()
    assert len(sent) == 1


def test_subtitle_edit_validation_and_invoice_escaping(owner):
    with Session.begin() as s:
        job = Job(
            department="Video Editor",
            objective="existing export",
            status="completed",
            result="{}",
        )
        s.add(job)
        s.flush()
        jid = job.id
    (DATA / "exports").mkdir(exist_ok=True)
    assert (
        owner.put(
            f"/videos/{jid}/subtitles",
            json={"segments": [{"start": 0, "end": 1.2, "text": "سڵاو hello"}]},
        ).status_code
        == 200
    )
    srt = owner.get(f"/exports/video-{jid}.srt")
    assert "00:00:01,200" in srt.text
    assert "سڵاو" in srt.text
    assert (
        owner.put(
            f"/videos/{jid}/subtitles",
            json={"segments": [{"start": 5, "end": 2, "text": "bad"}]},
        ).status_code
        == 422
    )
    rid = owner.post(
        "/records/invoice",
        json={
            "title": "<script>alert(1)</script>",
            "detail": "Service",
            "amount_minor": 12345,
            "currency": "USD",
        },
    ).json()["id"]
    html = owner.get(f"/invoices/{rid}/print").text
    assert "<script>" not in html
    assert "123.45 USD" in html


def test_research_deduplicates_keeps_sources_and_never_creates_contacts(
    owner, monkeypatch
):
    import app.services as services

    monkeypatch.setattr(services, "get_secret", lambda name: "test-search-key")

    class Result:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "web": {
                    "results": [
                        {
                            "url": "https://business.example/about",
                            "title": "Example business",
                            "description": "Public business listing",
                        }
                    ]
                }
            }

    monkeypatch.setattr(services.httpx, "get", lambda *a, **kw: Result())
    options = {"country": "Iraq", "industry": "Retail"}
    assert len(json.loads(services.research(options))) == 1
    assert json.loads(services.research(options)) == []
    lead = owner.get("/records/lead").json()[0]["data"]
    assert lead["source_url"] == "https://business.example/about"
    assert lead["research_date"]
    assert owner.get("/contacts").json() == []


def test_music_requires_explicit_license(owner):
    assert (
        owner.post(
            "/music?licensed=false", files={"file": ("music.mp3", b"123", "audio/mpeg")}
        ).status_code
        == 422
    )
    assert (
        owner.post(
            "/music?licensed=true", files={"file": ("music.mp3", b"123", "audio/mpeg")}
        ).status_code
        == 200
    )
    assert owner.post("/gmail/sync").status_code == 403


def test_windows_credential_manager_roundtrip():
    import sys, uuid, pytest

    if sys.platform != "win32":
        pytest.skip("Windows Credential Manager acceptance requires Windows")
    from app.security import set_secret, get_secret, delete_secret

    name = "acceptance-" + uuid.uuid4().hex
    try:
        set_secret(name, "non-production-acceptance-value")
        assert get_secret(name) == "non-production-acceptance-value"
    finally:
        delete_secret(name)
    assert get_secret(name) is None


def test_analytics_filters_and_money(owner):
    owner.post(
        "/finance",
        json={
            "direction": "revenue",
            "amount_minor": 9876,
            "currency": "USD",
            "description": "Filtered payment",
            "evidence": "receipt",
            "confirmed": True,
        },
    )
    today = datetime.now(timezone.utc).date().isoformat()
    points = owner.get("/analytics", params={"start": today, "end": today}).json()
    assert len(points) == 1
    assert points[0]["USD_revenue_minor"] == 9876
    assert owner.get("/analytics?start=2025-01-01&end=2026-12-31").status_code == 422
    assert owner.get("/analytics?start=bad").status_code == 422


def test_official_social_publication_requires_approval(owner, monkeypatch):
    import app.services as services
    from app.services import publish_marketing, save_setting

    save_setting("mastodon", {"base_url": "https://social.example", "account": "owner"})
    monkeypatch.setattr(services, "get_secret", lambda name: "test-token")
    monkeypatch.setattr(main, "get_secret", lambda name: "test-token")
    rid = owner.post(
        "/records/marketing",
        json={
            "title": "Campaign post",
            "detail": "Owner-approved content",
            "status": "draft",
        },
    ).json()["id"]
    requests = []

    class Result:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "verified-status-1", "url": "https://social.example/@owner/1"}

    monkeypatch.setattr(
        services.httpx,
        "post",
        lambda *args, **kwargs: requests.append((args, kwargs)) or Result(),
    )
    publish_marketing(rid)
    assert not requests
    assert (
        owner.post(
            f"/marketing/{rid}/approve",
            json={
                "publish_at": (
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                ).isoformat()
            },
        ).status_code
        == 200
    )
    publish_marketing(rid)
    assert len(requests) == 1
    assert requests[0][1]["headers"]["Idempotency-Key"] == f"aios-marketing-{rid}"
    assert owner.get("/records/marketing").json()[0]["data"]["status"] == "published"
    publish_marketing(rid)
    assert len(requests) == 1


def test_reply_sending_needs_exact_human_approval_and_prevents_duplicate(
    owner, monkeypatch
):
    with Session.begin() as s:
        reply = Record(
            kind="reply",
            payload=json.dumps(
                {
                    "sender": "customer@example.com",
                    "subject": "Customer request",
                    "text": "Help please",
                }
            ),
        )
        s.add(reply)
        s.flush()
        rid = reply.id
    sent = []
    monkeypatch.setattr(main, "send_email", lambda *args: sent.append(args))
    payload = {
        "subject": "Re: Customer request",
        "body": "A reviewed response",
        "approved": False,
    }
    assert owner.post(f"/gmail/replies/{rid}/send", json=payload).status_code == 422
    assert not sent
    payload["approved"] = True
    assert owner.post(f"/gmail/replies/{rid}/send", json=payload).status_code == 200
    assert len(sent) == 1
    assert owner.post(f"/gmail/replies/{rid}/send", json=payload).status_code == 409


def test_campaign_costs_and_revenue_are_only_linked_recorded_transactions(owner):
    cid = contact(owner)
    campaign_id = campaign(owner, cid).json()["id"]
    assert (
        owner.get(f"/campaigns/{campaign_id}/finance").json()["USD"]["revenue_minor"]
        == 0
    )
    owner.post(
        "/finance",
        json={
            "direction": "revenue",
            "amount_minor": 10000,
            "currency": "USD",
            "description": "Customer payment",
            "evidence": "receipt",
            "confirmed": True,
            "campaign_id": campaign_id,
        },
    )
    owner.post(
        "/finance",
        json={
            "direction": "expense",
            "amount_minor": 1500,
            "currency": "USD",
            "description": "API cost",
            "evidence": "usage invoice",
            "confirmed": True,
            "campaign_id": campaign_id,
            "category": "API cost",
        },
    )
    assert (
        owner.get(f"/campaigns/{campaign_id}/finance").json()["USD"]["net_minor"]
        == 8500
    )
