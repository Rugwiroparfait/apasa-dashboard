"""Disposable-image smoke test; pipe into `docker run --rm -i IMAGE python -`."""

import os, secrets, subprocess, time, re, http.client
from http.cookies import SimpleCookie

assert os.geteuid() != 0, "The deployment image must run as a non-root user"
if os.environ.get("APASA_DB_NAME"):
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
        print(
            name,
            "production HTTPS-proxy session, role redirect and evidence journeys passed",
        )
    print(
        "Production container: non-root runtime, migrations, provisioning, deployment checks, Gunicorn, secure cookies, CSRF login, hashed static assets and health passed"
    )
finally:
    server.terminate()
    server.wait(timeout=10)
