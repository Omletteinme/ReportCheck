from demo.server import static_file


def make(tmp_path):
    (tmp_path / "vendor" / "three").mkdir(parents=True)
    (tmp_path / "assets").mkdir()
    (tmp_path / "vendor" / "three" / "a.js").write_text("export {}")
    (tmp_path / "assets" / "m.glb").write_bytes(b"glTF")
    (tmp_path / "assets" / "notes.exe").write_bytes(b"x")
    (tmp_path / "secret.json").write_text("{}")
    (tmp_path / "body3d.js").write_text("//")
    return {"vendor": tmp_path / "vendor", "assets": tmp_path / "assets"}, {"/body3d.js": tmp_path / "body3d.js"}


def test_serves_allowed_files_with_mime_types(tmp_path):
    roots, files = make(tmp_path)
    assert static_file("/vendor/three/a.js", roots, files)[1].startswith("text/javascript")
    assert static_file("/assets/m.glb", roots, files)[1] == "model/gltf-binary"
    assert static_file("/body3d.js?v=2", roots, files)[1].startswith("text/javascript")


def test_blocks_traversal_unknown_folders_and_extensions(tmp_path):
    roots, files = make(tmp_path)
    for bad in ["/vendor/../secret.json", "/vendor/%2e%2e/secret.json", "/vendor//../secret.json",
                "/assets/notes.exe", "/assets/missing.glb", "/other/x.js", "/vendor", "/vendor/", "/", "/assets/"]:
        assert static_file(bad, roots, files) is None, bad
