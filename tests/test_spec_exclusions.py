import os


def filter_linux_binaries(binaries):
    exclude_prefixes = ("libglib", "libgio", "libgobject", "libgmodule")
    return [
        x for x in binaries
        if not any(os.path.basename(x[0]).lower().startswith(p) for p in exclude_prefixes)
    ]


def test_filter_linux_binaries():
    sample_binaries = [
        ("libglib-2.0.so.0", "/usr/lib/libglib-2.0.so.0", "BINARY"),
        ("libgio-2.0.so.0", "/usr/lib/libgio-2.0.so.0", "BINARY"),
        ("libgobject-2.0.so.0", "/usr/lib/libgobject-2.0.so.0", "BINARY"),
        ("libgmodule-2.0.so.0", "/usr/lib/libgmodule-2.0.so.0", "BINARY"),
        ("libsqlite3.so.0", "/usr/lib/libsqlite3.so.0", "BINARY"),
        ("libcrypto.so.3", "/usr/lib/libcrypto.so.3", "BINARY"),
    ]

    filtered = filter_linux_binaries(sample_binaries)
    names = [x[0] for x in filtered]

    assert "libsqlite3.so.0" in names
    assert "libcrypto.so.3" in names
    assert "libglib-2.0.so.0" not in names
    assert "libgio-2.0.so.0" not in names
    assert "libgobject-2.0.so.0" not in names
    assert "libgmodule-2.0.so.0" not in names
