"""Own-work PDF with bookmarks (outline), built from stdlib bytes only (R41 tests).

``outline_pdf(pages, titles)``: ``pages`` is a list of ``("text", str)`` or ``("image", None)``; ``titles[i]`` (or
``None``) is the bookmark that points at page ``i``. The result has no dates or ids, so it is byte-stable.
"""

import random

PAGE_TEXT = ("Alpha body paragraph on the first page.", "Beta body paragraph on the second page.",
             "Gamma body paragraph on the third page.")


TITLES = ("Chapter One", "Chapter Two", "Chapter Three")


def outline_pdf(pages=(("text", (TITLES[0], PAGE_TEXT[0])), ("text", (TITLES[1], PAGE_TEXT[1]))), titles=TITLES[:2],
                action=False):
    count = len(pages)
    marked = [i for i, title in enumerate(titles) if title]
    first_page_id = 5
    page_id = {i: first_page_id + 2 * i for i in range(count)}      # page object ids; contents follow at +1
    last = first_page_id + 2 * count
    item_id = {i: last + n for n, i in enumerate(marked)}
    pixels = random.Random(41).randbytes(48 * 48 * 3)
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R /Outlines 3 0 R /PageMode /UseOutlines >>",
        2: ("<< /Type /Pages /Count %d /Kids [%s] >>" % (count, " ".join("%d 0 R" % page_id[i] for i in range(count)))).encode(),
        3: (b"<< /Type /Outlines /First %d 0 R /Last %d 0 R /Count %d >>"
            % (item_id[marked[0]], item_id[marked[-1]], len(marked))) if marked else b"<< /Type /Outlines /Count 0 >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for i, (kind, text) in enumerate(pages):
        objects[page_id[i]] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> "
                               b"/XObject << /Im %d 0 R >> >> /Contents %d 0 R >>" % (last + len(marked), page_id[i] + 1))
        if kind == "text":
            lines = [text] if isinstance(text, str) else list(text)
            # the first line is drawn large (a heading-looking title that the bookmark points at), the rest as body
            content = b"BT 50 700 Td /F1 20 Tf (%s) Tj /F1 12 Tf" % lines[0].encode()
            content += b"".join(b" 0 -30 Td (%s) Tj" % line.encode() for line in lines[1:]) + b" ET"
        else:
            content = b"q 400 0 0 400 100 200 cm /Im Do Q"
        objects[page_id[i] + 1] = b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"
    for n, i in enumerate(marked):
        destination = b"[%d 0 R /XYZ 0 792 0]" % page_id[i]
        parts = [b"/Title (%s)" % titles[i].encode(), b"/Parent 3 0 R",
                 (b"/A << /S /GoTo /D %s >>" if action else b"/Dest %s") % destination, b"/Count 0"]
        if n:
            parts.append(b"/Prev %d 0 R" % item_id[marked[n - 1]])
        if n + 1 < len(marked):
            parts.append(b"/Next %d 0 R" % item_id[marked[n + 1]])
        objects[item_id[i]] = b"<< " + b" ".join(parts) + b" >>"
    objects[last + len(marked)] = (b"<< /Type /XObject /Subtype /Image /Width 48 /Height 48 /ColorSpace /DeviceRGB "
                                   b"/BitsPerComponent 8 /Length %d >>\nstream\n" % len(pixels) + pixels + b"\nendstream")
    out, offsets = bytearray(b"%PDF-1.4\n"), {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    size = max(objects) + 1
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size + b"".join(b"%010d 00000 n \n" % offsets[n] for n in range(1, size))
    return bytes(out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref))
