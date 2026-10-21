#!/usr/bin/env python3
"""Generate a signed RFC 9116 security.txt file using GPG."""

import argparse
import datetime
import os
import subprocess
import sys


def get_pgp_fingerprint(key_id: str) -> str | None:
    """Query GPG for the primary fingerprint associated with key_id."""
    try:
        res = subprocess.run(
            ["gpg", "--batch", "--with-colons", "--list-keys", key_id],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in res.stdout.splitlines():
            parts = line.split(":")
            if parts[0] == "fpr" and len(parts) > 9 and parts[9]:
                return parts[9]
    except (subprocess.SubprocessError, OSError):
        return None
    return None


def generate_security_txt(
    key_id: str = "203B000478AD0EF1",
    domain: str = "nathan.woodburn.au",
    contact_email: str = "contact@nathan.woodburn.au",
    expiry_days: int = 365,
    output_path: str = ".well-known/security.txt",
    sign: bool = True,
) -> str:
    """Generate and optionally sign security.txt."""
    # RFC 9116 requires RFC 3339 formatted date/time in the future (recommended <= 1 year)
    now = datetime.datetime.now(datetime.UTC)
    expiry = (now + datetime.timedelta(days=expiry_days)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    fingerprint = get_pgp_fingerprint(key_id)

    lines = [
        f"Contact: mailto:{contact_email}",
        f"Expires: {expiry}",
        f"Encryption: https://{domain}/download/pgp",
    ]

    if fingerprint:
        lines.append(f"Encryption: openpgp4fpr:{fingerprint}")

    lines.extend(
        [
            f"Canonical: https://{domain}/.well-known/security.txt",
            "Preferred-Languages: en",
        ]
    )

    unsigned_content = "\n".join(lines) + "\n"

    if sign:
        print(f"Signing security.txt with GPG key {key_id}...")
        try:
            sign_proc = subprocess.run(
                [
                    "gpg",
                    "--batch",
                    "--yes",
                    "--armor",
                    "--clearsign",
                    "--local-user",
                    key_id,
                ],
                input=unsigned_content.encode("utf-8"),
                capture_output=True,
                check=True,
            )
            final_content = sign_proc.stdout.decode("utf-8")
        except subprocess.CalledProcessError as err:
            sys.stderr.write(
                f"Error during GPG signing: {err.stderr.decode('utf-8', errors='replace')}\n"
            )
            raise
    else:
        final_content = unsigned_content

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"Successfully generated {output_path}")

    if sign:
        # Verify the signature
        verify_proc = subprocess.run(
            ["gpg", "--batch", "--verify", output_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if verify_proc.returncode == 0:
            print("Signature successfully verified:")
            for line in verify_proc.stderr.splitlines():
                if "Good signature" in line or "Primary key fingerprint" in line:
                    print(f"  {line.strip()}")
        else:
            sys.stderr.write(
                f"Warning: Signature verification failed:\n{verify_proc.stderr}\n"
            )

    return final_content


def main():
    parser = argparse.ArgumentParser(
        description="Generate an RFC 9116 security.txt file signed with GPG."
    )
    parser.add_argument(
        "--key",
        default="203B000478AD0EF1",
        help="GPG key ID or fingerprint to sign with (default: 203B000478AD0EF1)",
    )
    parser.add_argument(
        "--domain",
        default="nathan.woodburn.au",
        help="Domain for Canonical and Encryption URLs (default: nathan.woodburn.au)",
    )
    parser.add_argument(
        "--contact",
        default="contact@nathan.woodburn.au",
        help="Contact email address (default: contact@nathan.woodburn.au)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days until expiry (default: 365, max recommended 365)",
    )
    parser.add_argument(
        "--output",
        default=".well-known/security.txt",
        help="Destination path (default: .well-known/security.txt)",
    )
    parser.add_argument(
        "--no-sign",
        action="store_true",
        help="Skip GPG cleartext signing",
    )

    args = parser.parse_args()

    generate_security_txt(
        key_id=args.key,
        domain=args.domain,
        contact_email=args.contact,
        expiry_days=args.days,
        output_path=args.output,
        sign=not args.no_sign,
    )


if __name__ == "__main__":
    main()
