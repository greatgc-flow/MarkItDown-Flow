"""PURE sniff decisions; structural evidence is supplied by the IO stage."""


def detect_format(header: bytes, ext: str, *, members: tuple = (),
                  streams: tuple = (), encrypted: bool = False) -> dict:
    raise NotImplementedError


def sniff_result(data: bytes, path: str, root: str, detection: dict) -> dict:
    raise NotImplementedError
