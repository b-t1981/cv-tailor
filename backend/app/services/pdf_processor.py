import fitz

from app.models.schemas import ParagraphInfo


def extract_paragraphs_from_pdf(path: str) -> list[ParagraphInfo]:
    doc = fitz.open(path)
    paragraphs: list[ParagraphInfo] = []
    index = 0

    for page in doc:
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) < 5:
                continue
            text = block[4].strip()
            if not text:
                continue

            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for line in lines:
                is_heading = len(line) < 60 and line.isupper()
                paragraphs.append(
                    ParagraphInfo(
                        id=f"p_{index}",
                        text=line,
                        style="PDF Extract",
                        is_heading=is_heading,
                    )
                )
                index += 1

    doc.close()
    return paragraphs
