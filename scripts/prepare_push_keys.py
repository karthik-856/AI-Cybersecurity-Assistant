"""Create stable VAPID secrets for private import into hosting settings."""
import argparse
import base64
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/push/render.env")
    parser.add_argument("--subject", default="https://zuka-soc.onrender.com")
    args = parser.parse_args()
    if not args.subject.startswith(("https://", "mailto:")) or any(c in args.subject for c in "\r\n"):
        parser.error("Use an HTTPS contact URL or mailto contact address.")
    key = ec.generate_private_key(ec.SECP256R1())
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    public = encode(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
    private = encode(key.private_numbers().private_value.to_bytes(32, "big"))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(f"VAPID_PUBLIC_KEY={public}\nVAPID_PRIVATE_KEY={private}\nVAPID_SUBJECT={args.subject}\n")
    print(f"Created {target}. Contains a private signing key; import privately into hosting settings and keep out of Git.")


if __name__ == "__main__":
    main()
