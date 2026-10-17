"""Retired migration: accession equality cannot establish sequence provenance.

Rebuild legacy caches with `python -m tardiscreen.embed`; entries with matching
existing hashes are reused, while unverifiable entries are recomputed.
"""


def main() -> int:
    print("Refusing to assign current sequence hashes to unverifiable legacy vectors.")
    print("Run python -m tardiscreen.embed to build a verified cache.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
