#!/usr/bin/env python3
"""Generate local VPS secrets once, without displaying or replacing them."""

import argparse
import os
from pathlib import Path
import re
import secrets


def create_config(path, domain):
    if not re.fullmatch(
        r"(?=.{1,253}$)[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,63}", domain
    ):
        raise ValueError("Use a DNS hostname without a scheme, port or path")
    values = {
        "APASA_DOMAIN": domain,
        "APASA_SECRET_KEY": secrets.token_urlsafe(60),
        "APASA_DB_PASSWORD": secrets.token_urlsafe(32),
        "APASA_POLICYMAKER_PASSWORD": secrets.token_urlsafe(24),
        "APASA_DISTRICT_PASSWORD": secrets.token_urlsafe(24),
        "WEB_CONCURRENCY": "1",
        "NVIDIA_API_KEY": "",
        "NVDIA_API_KEY": "",
    }
    # O_EXCL refuses to overwrite existing DB credentials or account passwords.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(
            "# Private VPS settings. Keep this file out of Git and backups shared in chat.\n"
        )
        output.write("\n".join(f"{k}={v}" for k, v in values.items()) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="apasa.inzuyange.com")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / ".env.vps",
    )
    args = parser.parse_args()
    try:
        create_config(args.output, args.domain)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Configuration was not written: {exc}\n")
    print(
        f"Private settings created at {args.output} (mode 600). No secret values printed."
    )
    print(
        "Edit this file locally to add the NVIDIA key and retrieve the initial role passwords."
    )


if __name__ == "__main__":
    main()
