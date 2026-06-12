"""One-shot diagnostic: test PDF pipeline on a Render backend."""
import json
import sys
import urllib.request
import http.cookiejar

API_BASE = sys.argv[1] if len(sys.argv) > 1 else "https://cv-tailor-pxyo.onrender.com/api"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def req(method: str, path: str, data: dict | None = None) -> tuple[int, bytes, dict]:
    headers: dict[str, str] = {}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    with opener.open(request, timeout=120) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def main() -> None:
    print(f"Target: {API_BASE}\n")

    _, raw, hdrs = req("GET", "/health")
    health = json.loads(raw)
    print("=== HEALTH ===")
    print(json.dumps(health, indent=2))
    print("libreoffice_available field:", "libreoffice_available" in health)
    print("x-render-origin-server:", hdrs.get("x-render-origin-server"))

    payload = {
        "cover_letter": (
            "Madame, Monsieur,\n\n"
            "Je vous propose ma candidature pour un poste de test diagnostic PDF.\n\n"
            "Cordialement,\nTest"
        ),
        "company_name": "Diagnostic Render",
        "job_title": "Test PDF",
    }
    _, raw, _ = req("POST", "/application/cover-letter/docx", payload)
    export = json.loads(raw)
    print("\n=== COVER LETTER EXPORT ===")
    print(json.dumps(export, indent=2))

    pdf_url = export.get("download_url_pdf")
    if not pdf_url:
        print("\nVERDICT: PDF not generated — export_docx_to_pdf failed completely.")
        sys.exit(1)

    _, pdf_bytes, pdf_hdrs = req("GET", pdf_url)
    print("\n=== PDF DOWNLOAD ===")
    print("bytes:", len(pdf_bytes), "content-type:", pdf_hdrs.get("Content-Type"))

    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    print("pages:", doc.page_count)
    page = doc[0]
    text = page.get_text("text")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    print("text lines on page 1:", len(lines))

    xs: list[float] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                xs.append(round(span["bbox"][0], 1))
    xs_unique = sorted(set(xs))
    print("distinct x-positions:", xs_unique)

    if len(xs_unique) <= 2 and xs_unique and all(x < 100 for x in xs_unique):
        print("\nVERDICT: LINEAR_FALLBACK_LIKELY — LibreOffice probably not used.")
    elif len(xs_unique) >= 3 or (xs_unique and max(xs_unique) > 200):
        print("\nVERDICT: STRUCTURED_PDF — LibreOffice (or rich converter) likely used.")
    else:
        print("\nVERDICT: INCONCLUSIVE — inspect PDF manually.")


if __name__ == "__main__":
    main()
