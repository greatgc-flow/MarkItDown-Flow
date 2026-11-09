"""Source bytes are part of CT-03's exact report contract."""
from io import BytesIO
import random
import struct
import zipfile
import zlib

import pytest


@pytest.mark.req('REQ-GEN-10', 'REQ-TRI-04')
@pytest.mark.cov('S2', 'FM10')
@pytest.mark.fx('FX-09', 'FX-16', 'FX-23')
@pytest.mark.scope('schema')
def test_T_GEN_56_png_and_archives_do_not_depend_on_native_compressors(contract_data, monkeypatch):
    from PIL import Image

    def unexpected(*args, **kwargs):
        raise AssertionError('fixture bytes depend on a native encoder/compressor')

    monkeypatch.setattr(Image.Image, 'save', unexpected)
    monkeypatch.setattr(zlib, 'compress', unexpected)
    monkeypatch.setattr(zlib, 'compressobj', unexpected)
    for size in ((8, 8), (200, 200)):
        png = contract_data.image_bytes(size=size)
        # Independent decoder verifies dimensions and the original seeded RGB pixels.
        with Image.open(BytesIO(png)) as image:
            image.load()
            assert image.size == size and image.mode == 'RGB'
            assert image.tobytes() == random.Random(7).randbytes(size[0] * size[1] * 3)
        offset, chunks = 8, []
        while offset < len(png):
            length = struct.unpack_from('>I', png, offset)[0]
            payload = png[offset + 4:offset + 8 + length]
            assert zlib.crc32(payload) == struct.unpack_from('>I', png, offset + 8 + length)[0]
            chunks.append(payload[:4])
            offset += 12 + length
        assert offset == len(png) and chunks == [b'IHDR', b'IDAT', b'IEND']
        archive = contract_data.zip_bytes([('media/image.png', png)])
        with zipfile.ZipFile(BytesIO(archive)) as zipped:
            assert zipped.read('media/image.png') == png
    bomb = (contract_data.ROOT / 'engine/tests/fixtures/FX-46.zip').read_bytes()
    assert contract_data.digest(bomb) == '2ca96972d495cbcc53d1b59fadd556099a47736d445597ab01877631d45876d5'
    with zipfile.ZipFile(BytesIO(bomb)) as zipped:
        member, = zipped.infolist()
        assert member.filename == 'zeros.txt'
        assert member.compress_type == zipfile.ZIP_DEFLATED
        assert member.file_size / member.compress_size > 100
        assert zipped.read(member) == b'\0' * (11 * 1024**2)

