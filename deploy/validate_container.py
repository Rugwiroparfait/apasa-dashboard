"""Disposable-image smoke test; pipe into `docker run --rm -i IMAGE python -`."""

import os, secrets, subprocess, time, re, http.client
from http.cookies import SimpleCookie

assert os.geteuid() != 0, "The deployment image must run as a non-root user"
if os.environ.get("APASA_DB_NAME") or os.environ.get("DATABASE_URL"):
    raise SystemExit("Use a disposable container without a production database binding")
os.environ["APASA_SQLITE_PATH"] = "/app/runtime/smoke.sqlite3"
os.environ.update(
    APASA_SECRET_KEY=secrets.token_urlsafe(60),
    APASA_TRUST_PROXY="true",
    APASA_POLICYMAKER_PASSWORD=secrets.token_urlsafe(24),
    APASA_DISTRICT_PASSWORD=secrets.token_urlsafe(24),
)
subprocess.run(
    ["python", "manage.py", "migrate", "--noinput"],
    check=True,
    stdout=subprocess.DEVNULL,
)
subprocess.run(["python", "manage.py", "provision_accounts"], check=True)
subprocess.run(
    ["python", "manage.py", "check", "--deploy", "--fail-level", "WARNING"], check=True
)
server = subprocess.Popen(
    [
        "gunicorn",
        "apasa.wsgi:application",
        "--bind",
        "127.0.0.1:8000",
        "--workers",
        "2",
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)


def request(path, method="GET", data=None, cookies=None):
    conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=5)
    headers = {
        "Host": "localhost",
        "X-Forwarded-Proto": "https",
        "Referer": "https://localhost/accounts/login/",
    }
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    if data:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    conn.request(method, path, body=data, headers=headers)
    response = conn.getresponse()
    body = response.read()
    headers = response.getheaders()
    status = response.status
    conn.close()
    return status, headers, body


try:
    sessions = {}
    for _ in range(30):
        try:
            if request("/health/")[0] == 200:
                break
        except OSError:
            pass
        time.sleep(0.2)
    else:
        raise AssertionError("Gunicorn did not become ready")
    status, headers, body = request("/")
    assert status == 200 and b"Better planning" in body
    asset = re.search(rb'href="(/static/[^"]+\.css)"', body).group(1).decode()
    assert request(asset)[0] == 200, asset
    assert request("/national-policy-evidence/")[0] == 302
    for name, variable, destination in [
        ("policymaker", "APASA_POLICYMAKER_PASSWORD", "/national-policy-evidence/"),
        ("district_officer", "APASA_DISTRICT_PASSWORD", "/district-crop-statistics/"),
    ]:
        status, headers, body = request("/accounts/login/")
        assert status == 200
        cookie = {}
        for key, value in headers:
            if key.lower() == "set-cookie":
                parsed = SimpleCookie()
                parsed.load(value)
                for k, m in parsed.items():
                    cookie[k] = m.value
                    assert m["secure"]
        token = (
            re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', body)
            .group(1)
            .decode()
        )
        from urllib.parse import urlencode

        status, headers, body = request(
            "/accounts/login/",
            "POST",
            urlencode(
                {
                    "username": name,
                    "password": os.environ[variable],
                    "csrfmiddlewaretoken": token,
                }
            ),
            cookie,
        )
        assert status == 302, (name, status, body[:150])
        for key, value in headers:
            if key.lower() == "set-cookie":
                parsed = SimpleCookie()
                parsed.load(value)
                for k, m in parsed.items():
                    cookie[k] = m.value
                    assert m["secure"]
        sessions[name] = dict(cookie)
        status, headers, body = request("/workspace/", cookies=cookie)
        assert status == 302 and dict(headers)["Location"] == destination
        for path, expected in [
            ("/national-policy-evidence/?record=1", b"122370.3260885097"),
            ("/workbook-evidence/?crop=Maize", b"Table 6!I6"),
            ("/workbook-evidence/?mock=1&download=csv", b"MOCKED"),
            (
                "/district-crop-statistics/?province=1&district=11&crop=Maize",
                b"574.4233",
            ),
        ]:
            status, headers, body = request(path, cookies=cookie)
            assert status == 200 and expected in body, (path, status)
        status, _, chart_body = request("/workspace/overview/", cookies=cookie)
        assert status == 200 and chart_body.count(b"<svg") == 2
        assert b"AHS Research Evidence" not in chart_body
        status, _, chart_body = request("/workbook-evidence/", cookies=cookie)
        assert status == 200 and chart_body.count(b"<svg") == 2
        print(
            name,
            "production HTTPS-proxy session, role redirect and evidence journeys passed",
        )
    # Exercise publication controls in the disposable smoke DB only, never real evidence.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apasa.settings")
    import django

    django.setup()
    import json
    from decimal import Decimal
    from django.contrib.auth import get_user_model
    from planning.models import (
        SourceBatch,
        IndicatorVersion,
        Assessment,
        ForecastModel,
        ScenarioRun,
        ActionBrief,
        FollowUp,
        AIExplanation,
        AIRequestLog,
        State,
    )
    from planning.services import transition
    from planning.calculations import fit_forecast
    from planning.validation import fingerprint
    from planning.briefs import draft_brief
    from planning.ai import key_binding

    assert (
        key_binding()[1] is None
    ), "Never supply real AI credentials to the disposable smoke test"
    author = get_user_model().objects.get(username="policymaker")
    reviewer = get_user_model().objects.get(username="district_officer")
    rows = [
        dict(
            measure="production",
            crop="Maize",
            unit="MT",
            period=str(2019 + i),
            geography_code="RW",
            geography="Rwanda",
            population="All farmer types",
            value=str(100 + 10 * i),
            standard_error="",
            is_mocked=False,
            source_reference="DISPOSABLE SMOKE FIXTURE — not real evidence",
        )
        for i in range(8)
    ]
    source = SourceBatch.objects.create(
        title="Disposable smoke fixture",
        source_url="https://example.invalid/smoke",
        source_reference="DISPOSABLE SMOKE FIXTURE",
        methodology="smoke-v1",
        content_sha256=fingerprint(json.dumps(rows).encode()),
        rows=rows,
        created_by=author,
    )
    target = IndicatorVersion.objects.create(
        framework="PSTA5",
        code="SMOKE-FIXTURE",
        version=1,
        name="Disposable smoke target",
        measure="production",
        crop="Maize",
        unit="MT",
        population="All farmer types",
        geography_code="RW",
        geography="Rwanda",
        methodology="smoke-v1",
        baseline_period="2019",
        baseline_value=100,
        target_period="2028",
        target_value=200,
        direction="higher",
        source_url="https://example.invalid/smoke-policy",
        source_reference="DISPOSABLE SMOKE FIXTURE",
        created_by=author,
    )

    def approve(kind, record):
        transition(
            kind,
            record.pk,
            author,
            "submit",
            "Disposable smoke test submission, not real evidence.",
        )
        transition(
            kind,
            record.pk,
            reviewer,
            "approve",
            "Disposable smoke test review of mechanics only.",
            True,
        )
        record.refresh_from_db()

    approve("source", source)
    approve("indicator", target)
    assessment = Assessment.objects.create(
        indicator=target,
        dataset=source,
        row_index=7,
        mapping_notes="Disposable smoke test with deliberately aligned dimensions.",
        methodology_confirmed=True,
        created_by=author,
    )
    approve("assessment", assessment)
    assert assessment.result_snapshot["gap"] == 30
    spec = fit_forecast(assessment, Decimal(0))
    model = ForecastModel.objects.create(
        assessment=assessment,
        created_by=author,
        acceptable_rmse=0,
        specification=spec,
        training_sha256=fingerprint(
            json.dumps(spec["points"], sort_keys=True).encode()
        ),
    )
    approve("model", model)
    author_cookies = sessions["policymaker"]

    def post(path, data):
        return request(
            path,
            "POST",
            urlencode(dict(data, csrfmiddlewaretoken=author_cookies["csrftoken"])),
            author_cookies,
        )

    status, headers, body = post(
        f"/planning/models/{model.pk}/scenario/", {"years": 2, "adjustment": 5}
    )
    assert status == 302, (status, body[:100])
    scenario_path = dict(headers)["Location"]
    assert request(scenario_path, cookies=author_cookies)[0] == 200
    run = ScenarioRun.objects.get(model=model)
    assert abs(run.output["adjusted"] - 209.475) < 0.0001
    approve("scenario", run)
    content, method, notice, metadata = draft_brief(
        assessment, "Review feasible actions with a domain specialist.", False, run
    )
    brief = ActionBrief.objects.create(
        assessment=assessment,
        scenario=run,
        created_by=author,
        content=content,
        method=method,
        proposed_action="Review feasible actions with a domain specialist.",
        ai_metadata=metadata,
    )
    approve("brief", brief)
    status, _, body = post(
        f"/planning/comparisons/{assessment.pk}/followup/",
        {
            "owner": author.pk,
            "action": "Disposable smoke follow-up",
            "due_date": "2026-12-01",
            "status": "planned",
            "outcome_notes": "",
            "outcome_source_url": "",
            "observed_value": "",
        },
    )
    assert status == 302 and FollowUp.objects.filter(assessment=assessment).exists()
    status, headers, body = post(
        f"/planning/comparisons/{assessment.pk}/ask/",
        {"question": "What does this disposable target gap mean?"},
    )
    assert status == 302, (status, body[:100])
    answer = AIExplanation.objects.get(assessment=assessment)
    assert answer.method == "template" and "NOT AN AI RESPONSE" in answer.answer
    assert not AIRequestLog.objects.exists()
    assert request("/planning/ai/", cookies=author_cookies)[0] == 200
    assert (
        request(
            f"/planning/comparisons/{assessment.pk}/?download=text",
            cookies=author_cookies,
        )[0]
        == 200
    )
    print(
        "Production planning: source/target peer review, frozen comparison, validated model, saved/reviewed scenario, approved brief, follow-up, AI local fallback and report download passed"
    )
    print(
        "Production container: non-root runtime, migrations, provisioning, deployment checks, Gunicorn, secure cookies, CSRF login, hashed static assets and health passed"
    )
finally:
    server.terminate()
    server.wait(timeout=10)
