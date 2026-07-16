import os

import pytest

from brain_mcp.errors import InvalidPath
from brain_mcp.paths import VaultJail


@pytest.fixture
def jail(vault):
    return VaultJail(vault)


def test_normal_path_resolves_inside_vault(jail, vault):
    p = jail.resolve("10 Companies/Acme.md")
    assert p == vault / "10 Companies" / "Acme.md"


def test_leading_slash_treated_as_vault_relative_for_dirs(jail, vault):
    # list_directory("/") means the vault root
    assert jail.resolve_dir("/") == vault
    assert jail.resolve_dir("") == vault


def test_absolute_paths_rejected(jail):
    with pytest.raises(InvalidPath):
        jail.resolve("/etc/passwd")
    with pytest.raises(InvalidPath):
        jail.resolve("/var/run/docker.sock")


def test_dotdot_traversal_rejected(jail):
    with pytest.raises(InvalidPath):
        jail.resolve("../outside.md")
    with pytest.raises(InvalidPath):
        jail.resolve("10 Companies/../../outside.md")


def test_hidden_and_blocked_segments_rejected(jail):
    for bad in [".git/config", ".obsidian/workspace.json", ".env", "10 Companies/.hidden.md"]:
        with pytest.raises(InvalidPath):
            jail.resolve(bad)


def test_disallowed_extension_rejected(jail):
    for bad in ["script.sh", "binary.exe", "10 Companies/img.png"]:
        with pytest.raises(InvalidPath):
            jail.resolve(bad)


def test_allowed_text_extensions_accepted(jail):
    for ok in ["a.md", "b.txt", "c.csv", "d.json", "e.yaml", "f.canvas"]:
        assert jail.resolve(ok)


def test_symlink_escaping_vault_rejected(jail, vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("secret")
    os.symlink(outside, vault / "10 Companies" / "link")
    with pytest.raises(InvalidPath):
        jail.resolve("10 Companies/link/secret.md")


def test_unicode_and_spaces_work(jail, vault):
    p = jail.resolve("20 People/José Müller — 日本語.md")
    assert p.parent == vault / "20 People"
