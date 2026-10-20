#!/usr/bin/env python3
"""GhostRate PyPI Uploader.

Uploads distribution packages directly to PyPI using PyPI's official API
without requiring twine or external dependencies.
"""

import getpass
import hashlib
import mimetypes
import os
import sys
import tarfile
import urllib.request
import urllib.error
import zipfile


PYPI_UPLOAD_URL = "https://upload.pypi.org/legacy/"


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def md5_file(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def extract_metadata(filepath):
    """Extracts parsed email.Message object and raw metadata bytes from .whl or .tar.gz."""
    import email
    raw_meta = b""
    if filepath.endswith(".whl"):
        with zipfile.ZipFile(filepath, "r") as z:
            for name in z.namelist():
                if name.endswith(".dist-info/METADATA"):
                    raw_meta = z.read(name)
                    break
    elif filepath.endswith(".tar.gz"):
        with tarfile.open(filepath, "r:gz") as t:
            for member in t.getmembers():
                if member.name.endswith("/PKG-INFO"):
                    f = t.extractfile(member)
                    if f:
                        raw_meta = f.read()
                    break

    meta_str = raw_meta.decode("utf-8", errors="replace")
    msg = email.message_from_string(meta_str)
    return msg, raw_meta


def build_multipart_body(fields, files, boundary):
    lines = []
    for key, val in fields.items():
        if isinstance(val, (list, tuple)):
            for v in val:
                lines.append(f"--{boundary}".encode("utf-8"))
                lines.append(f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"))
                lines.append(b"")
                lines.append(str(v).encode("utf-8"))
        else:
            lines.append(f"--{boundary}".encode("utf-8"))
            lines.append(f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"))
            lines.append(b"")
            lines.append(str(val).encode("utf-8"))

    for key, (filename, file_bytes) in files.items():
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode("utf-8")
        )
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        lines.append(f"Content-Type: {content_type}".encode("utf-8"))
        lines.append(b"")
        lines.append(file_bytes)

    lines.append(f"--{boundary}--".encode("utf-8"))
    lines.append(b"")
    return b"\r\n".join(lines)


def upload_distribution(filepath, token):
    filename = os.path.basename(filepath)
    print(f"[*] Preparing {filename}...")

    file_type = "bdist_wheel" if filename.endswith(".whl") else "sdist"
    pyversion = "py3" if filename.endswith(".whl") else "source"

    msg, raw_meta = extract_metadata(filepath)
    meta_version = msg.get("Metadata-Version", "2.1")
    pkg_name = msg.get("Name", "ghostrate")
    pkg_version = msg.get("Version", "1.0.1")
    pkg_summary = msg.get("Summary", "Audio Steganography & Forensic Tool")
    description = msg.get_payload() or ""
    desc_content_type = msg.get("Description-Content-Type", "text/markdown")

    with open(filepath, "rb") as f:
        content = f.read()

    # PyPI Legacy API full specification
    fields = {
        ":action": "file_upload",
        "protocol_version": "1",
        "metadata_version": meta_version,
        "name": pkg_name,
        "version": pkg_version,
        "summary": pkg_summary,
        "description": description,
        "description_content_type": desc_content_type,
        "filetype": file_type,
        "pyversion": pyversion,
        "md5_digest": md5_file(filepath),
        "sha256_digest": sha256_file(filepath),
    }

    if msg.get("Home-page"):
        fields["home_page"] = msg.get("Home-page")
    if msg.get("Author"):
        fields["author"] = msg.get("Author")
    if msg.get("License"):
        fields["license"] = msg.get("License")
    if msg.get("Requires-Python"):
        fields["requires_python"] = msg.get("Requires-Python")
    if msg.get("Keywords"):
        fields["keywords"] = msg.get("Keywords")

    classifiers = msg.get_all("Classifier", [])
    if classifiers:
        fields["classifiers"] = classifiers

    project_urls = msg.get_all("Project-URL", [])
    if project_urls:
        fields["project_urls"] = project_urls

    files = {
        "content": (filename, content),
    }

    boundary = "----GhostRatePyPIBoundary" + hashlib.md5(filename.encode()).hexdigest()
    body = build_multipart_body(fields, files, boundary)

    # Basic auth with username '__token__' is standard for PyPI API tokens
    # Also provide Bearer token header for compatibility
    import base64
    auth_str = base64.b64encode(f"__token__:{token}".encode("utf-8")).decode("utf-8")

    req = urllib.request.Request(
        PYPI_UPLOAD_URL,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Basic {auth_str}",
            "User-Agent": "ghostrate-publisher/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[SUCCESS] Uploaded {filename}! (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] Failed uploading {filename}: HTTP {e.code} - {err_msg}")
        return False
    except Exception as e:
        print(f"[ERROR] Upload error: {e}")
        return False

    return True


def main():
    token = os.environ.get("PYPI_TOKEN", "").strip()
    if not token:
        if len(sys.argv) > 1 and sys.argv[1].startswith("pypi-"):
            token = sys.argv[1].strip()
        else:
            token = input("Enter your PyPI token (starts with pypi-...): ").strip()

    if not token.startswith("pypi-"):
        print("[WARNING] PyPI API tokens normally start with 'pypi-'. Proceeding anyway...")

    pkg_dir = "dist_pkg"
    files = [
        os.path.join(pkg_dir, f)
        for f in os.listdir(pkg_dir)
        if f.endswith(".whl") or f.endswith(".tar.gz")
    ]

    if not files:
        print("[ERROR] No distribution files found in dist_pkg/")
        sys.exit(1)

    print(f"[*] Found {len(files)} files to upload to PyPI:")
    for f in files:
        print(f"    - {f}")

    for f in sorted(files):
        success = upload_distribution(f, token)
        if not success:
            sys.exit(1)

    print("\n🎉 CONGRATULATIONS!")
    print("Your package is published and live on PyPI:")
    print("👉 https://pypi.org/project/ghostrate/")
    print("\nAnyone in the world can now install it:")
    print("   pip install ghostrate\n")


if __name__ == "__main__":
    main()
