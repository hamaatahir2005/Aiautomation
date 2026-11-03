import json, ssl, smtplib, shutil, subprocess
from email.message import EmailMessage
import httpx
from sqlalchemy import select
from .db import Session, Record, Job, DATA
from .security import get_secret


def setting(name, default=None):
    with Session() as s:
        r = s.scalar(select(Record).where(Record.kind == "setting:" + name))
        return json.loads(r.payload) if r else default


def save_setting(name, value):
    with Session.begin() as s:
        r = s.scalar(select(Record).where(Record.kind == "setting:" + name))
        if r:
            r.payload = json.dumps(value)
        else:
            s.add(Record(kind="setting:" + name, payload=json.dumps(value)))


def audit(event, details):
    with Session.begin() as s:
        s.add(
            Record(
                kind="audit", payload=json.dumps({"event": event, "details": details})
            )
        )


def smtp_connect(address, password):
    smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
    try:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(address, password)
        return smtp
    except Exception:
        smtp.close()
        raise


def send_email(to, subject, body):
    cfg = setting("gmail", {})
    secret = get_secret("gmail")
    if not cfg.get("address") or not secret:
        raise RuntimeError("Configure Gmail App Password first")
    msg = EmailMessage()
    msg["From"] = cfg["address"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtp_connect(cfg["address"], secret) as smtp:
        smtp.send_message(msg)


def ai(objective, department):
    cfg = setting("ai", {})
    base = cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    key = get_secret("ai")
    if not cfg.get("model"):
        raise RuntimeError("Configure an AI model in Settings")
    with httpx.Client(timeout=120, trust_env=True) as c:
        response = c.post(
            base + "/chat/completions",
            headers={"Authorization": "Bearer " + (key or "ollama")},
            json={
                "model": cfg["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are the {department} of AI Company OS. Produce actionable work. Never claim external actions, verified facts, revenue or sending unless supplied evidence. All outbound content is a draft requiring human approval. Support English, Arabic and Kurdish Sorani.",
                    },
                    {"role": "user", "content": objective},
                ],
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def update_job(job_id, **values):
    with Session.begin() as s:
        job = s.get(Job, job_id)
        for k, v in values.items():
            setattr(job, k, v)


def write_srt(path, segments):
    def stamp(seconds):
        ms = round(float(seconds) * 1000)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        sec, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"

    path.write_text(
        "\n\n".join(
            f"{i + 1}\n{stamp(segment['start'])} --> {stamp(segment['end'])}\n{segment['text']}"
            for i, segment in enumerate(segments)
        ),
        encoding="utf-8",
    )


def video(job):
    opts = json.loads(job.options)
    source = DATA / "media" / opts["file"]
    if not source.is_file():
        raise RuntimeError("Input video missing")
    outdir = DATA / "exports"
    outdir.mkdir(exist_ok=True)
    output = outdir / f"video-{job.id}.mp4"
    start, duration = float(opts.get("start", 0)), float(opts.get("duration", 30))
    transcript = []
    if opts.get("transcribe"):
        from faster_whisper import WhisperModel

        model = WhisperModel(
            opts.get("model", "small"), device="cpu", compute_type="int8"
        )
        segments, info = model.transcribe(
            str(source), language=opts.get("language") or None, vad_filter=True
        )
        transcript = [
            {"start": s.start, "end": s.end, "text": s.text} for s in segments
        ]
        (outdir / f"video-{job.id}.json").write_text(
            json.dumps(transcript, ensure_ascii=False), encoding="utf-8"
        )
    scenes = []
    if opts.get("detect_scenes"):
        from scenedetect import detect, ContentDetector

        scenes = [
            [a.get_seconds(), b.get_seconds()]
            for a, b in detect(str(source), ContentDetector())
        ]
    if opts.get("highlight") and transcript:
        candidates = [seg for seg in transcript if seg["end"] - seg["start"] > 2]
        if candidates:
            start = max(
                candidates,
                key=lambda seg: (
                    len(seg["text"].split()) / max(seg["end"] - seg["start"], 1)
                ),
            )["start"]
    clipped = [
        {
            "start": max(0, seg["start"] - start),
            "end": min(duration, seg["end"] - start),
            "text": seg["text"],
        }
        for seg in transcript
        if seg["end"] > start and seg["start"] < start + duration
    ]
    if clipped:
        write_srt(outdir / f"video-{job.id}.srt", clipped)
    update_job(job.id, progress=20)
    size = "1080:1920" if opts.get("format", "short") == "short" else "1920:1080"
    w, h = size.split(":")
    filters = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    )
    if opts.get("fade"):
        filters += f",fade=t=in:st=0:d=0.3,fade=t=out:st={max(0, duration - 0.3)}:d=0.3"
    if opts.get("burn_subtitles") and clipped:
        # Relative export filename keeps the FFmpeg filter path portable on Windows.
        filters += f",subtitles=video-{job.id}.srt"
    audio = "loudnorm=I=-16:TP=-1.5:LRA=11"
    if opts.get("trim_silence") and clipped:
        expression = "+".join(
            f"between(t,{seg['start']:.3f},{seg['end']:.3f})" for seg in clipped
        )
        filters += f",select='{expression}',setpts=N/FRAME_RATE/TB"
        audio = f"aselect='{expression}',asetpts=N/SR/TB," + audio
    command = [
        ffmpeg(),
        "-y",
        "-ss",
        str(start),
        "-i",
        str(source),
        "-t",
        str(duration),
        "-vf",
        filters,
        "-af",
        audio,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output),
    ]
    if opts.get("music"):
        music = DATA / "media" / opts["music"]
        # Music is explicitly owner-licensed; mix at a conservative background level.
        command = [
            ffmpeg(),
            "-y",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-stream_loop",
            "-1",
            "-i",
            str(music),
            "-t",
            str(duration),
            "-vf",
            filters,
            "-filter_complex",
            f"[0:a]{audio}[voice];[1:a]volume=0.12[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[mix]",
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output),
        ]
    with (outdir / f"video-{job.id}.log").open("w") as log:
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=log, text=True, cwd=outdir
        )
        for line in proc.stdout:
            with Session() as s:
                state = s.get(Job, job.id).status
            if state == "cancelled":
                proc.terminate()
                proc.wait()
                output.unlink(missing_ok=True)
                return None
            if line.startswith("out_time_us="):
                try:
                    update_job(
                        job.id,
                        progress=min(
                            95, 20 + int(int(line.split("=")[1]) / 1e6 / duration * 75)
                        ),
                    )
                except ValueError:
                    pass
        if proc.wait() != 0:
            raise RuntimeError("FFmpeg failed; inspect local export log")
    return json.dumps(
        {
            "file": output.name,
            "transcript": clipped,
            "scenes": scenes,
            "subtitles": f"video-{job.id}.srt" if clipped else None,
        }
    )


def research(options):
    key = get_secret("search")
    if not key:
        raise RuntimeError("Configure Brave Search API key in Settings")
    query = " ".join(
        str(options.get(k, ""))
        for k in [
            "industry",
            "business_type",
            "city",
            "country",
            "service",
            "language",
            "company_size",
        ]
    )
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": 10},
        headers={"X-Subscription-Token": key},
        timeout=30,
    )
    response.raise_for_status()
    from .db import now

    results = []
    with Session.begin() as s:
        existing = {
            json.loads(r.payload).get("source_url")
            for r in s.scalars(select(Record).where(Record.kind == "lead"))
        }
        for item in response.json().get("web", {}).get("results", []):
            if item["url"] in existing:
                continue
            lead = {
                "name": item["title"],
                "website": item["url"],
                "source_url": item["url"],
                "description": item.get("description", ""),
                "country": options.get("country", ""),
                "industry": options.get("industry", ""),
                "research_date": now(),
                "relevance_score": None,
                "verification": "search result; owner review required",
                "contact_channels": [],
            }
            if setting("ai", {}).get("model"):
                try:
                    scored = ai(
                        'Return JSON only: {"score":integer 0 to 100,"reason":"brief reasoning"}. Assess relevance for '
                        + query
                        + " using ONLY this search evidence: "
                        + json.dumps(lead),
                        "Worldwide Lead Finder",
                    ).strip()
                    if scored.startswith("```"):
                        scored = scored.split("\n", 1)[1].rsplit("```", 1)[0]
                    scored = json.loads(scored)
                    score = scored["score"]
                    if isinstance(score, int) and 0 <= score <= 100:
                        lead["relevance_score"] = score
                        lead["relevance_reason"] = str(scored.get("reason", ""))[:1000]
                except Exception:
                    lead["relevance_status"] = (
                        "AI scoring unavailable; review source manually"
                    )
            s.add(Record(kind="lead", payload=json.dumps(lead)))
            results.append(lead)
            existing.add(item["url"])
    return json.dumps(results)


def execute(job_id):
    with Session() as s:
        job = s.get(Job, job_id)
    if job.status != "queued":
        return
    if job.department not in setting(
        "agent_permissions",
        [
            "AI Manager",
            "Video Editor",
            "Worldwide Lead Finder",
            "Gmail Email Agent",
            "Sales Agent",
            "Marketing Agent",
            "Customer Support",
            "Finance Agent",
            "Analytics Agent",
            "Operations Agent",
        ],
    ):
        update_job(job.id, status="paused", result="Department disabled by owner")
        return
    with Session.begin() as s:
        from sqlalchemy import update

        if (
            s.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "queued")
                .values(status="running", progress=1)
            ).rowcount
            != 1
        ):
            return
    try:
        result = (
            video(job)
            if job.department == "Video Editor"
            else research(json.loads(job.options))
            if job.department == "Worldwide Lead Finder"
            else manager_plan(job.objective)
            if job.department == "AI Manager"
            else ai(job.objective, job.department)
        )
        with Session() as s:
            state = s.get(Job, job.id).status
        if state not in ("cancelled", "paused"):
            update_job(job.id, status="completed", progress=100, result=result or "")
    except Exception as exc:
        # Deliberately exclude provider responses, authentication details and raw exception text.
        reason = f"{type(exc).__name__}: processing failed. Check configured dependencies and provider access."
        if isinstance(exc, ModuleNotFoundError):
            reason = f"Missing dependency: {exc.name}. Install the video requirements or use a complete Windows build."
        elif isinstance(exc, httpx.HTTPStatusError):
            reason = f"Provider returned HTTP {exc.response.status_code}. Verify credentials, model, quota and endpoint."
        elif isinstance(exc, RuntimeError) and str(exc) in (
            "Configure an AI model in Settings",
            "Configure Brave Search API key in Settings",
            "Input video missing",
            "FFmpeg failed; inspect local export log",
        ):
            reason = str(exc)
        update_job(job.id, status="failed", result=reason)
        audit("job_failed", {"id": job.id, "error_type": type(exc).__name__})


def manager_plan(objective):
    instruction = (
        'Create a structured JSON plan only, without markdown fences. Schema: {"summary":"...","tasks":[{"department":"Sales Agent|Marketing Agent|Customer Support|Gmail Email Agent|Finance Agent|Analytics Agent|Operations Agent","objective":"specific draft or analysis task"}]}. Maximum 10 tasks. No sending, purchases, shell commands or fabricated evidence. Objective: '
        + objective
    )
    raw = ai(instruction, "AI Manager").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    plan = json.loads(raw)
    allowed = {
        "Sales Agent",
        "Marketing Agent",
        "Customer Support",
        "Gmail Email Agent",
        "Finance Agent",
        "Analytics Agent",
        "Operations Agent",
    }
    if not isinstance(plan.get("tasks"), list) or not 1 <= len(plan["tasks"]) <= 10:
        raise ValueError("Invalid plan")
    for task in plan["tasks"]:
        if (
            task.get("department") not in allowed
            or not isinstance(task.get("objective"), str)
            or not task["objective"]
        ):
            raise ValueError("Invalid task")
    return json.dumps(plan, ensure_ascii=False)


def publish_marketing(record_id):
    from .db import now

    config = setting("mastodon", {})
    secret = get_secret("mastodon")
    if not config.get("base_url") or not secret:
        with Session.begin() as s:
            record = s.get(Record, record_id)
            if record:
                data = json.loads(record.payload)
                data["status"] = "needs review"
                data["error_type"] = "Mastodon credential unavailable"
                record.payload = json.dumps(data)
        return
    with Session.begin() as s:
        record = s.get(Record, record_id)
        if not record or record.kind != "marketing":
            return
        data = json.loads(record.payload)
        if data.get("status") != "approved" or data.get("publish_at", "9999") > now():
            return
        data["status"] = "publishing"
        record.payload = json.dumps(data)
    try:
        response = httpx.post(
            config["base_url"].rstrip("/") + "/api/v1/statuses",
            headers={
                "Authorization": "Bearer " + secret,
                "Idempotency-Key": f"aios-marketing-{record_id}",
            },
            json={"status": data["detail"], "visibility": "public"},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        data["status"] = "published"
        data["published_at"] = now()
        data["platform_id"] = str(result["id"])
        data["platform_url"] = result.get("url", "")
    except Exception as exc:
        data["status"] = "needs review"
        data["error_type"] = type(exc).__name__
    with Session.begin() as s:
        s.get(Record, record_id).payload = json.dumps(data)
    audit(
        "social_publish_attempt",
        {"record": record_id, "status": data["status"], "platform": "Mastodon"},
    )
