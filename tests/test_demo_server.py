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


class _FakeT5:
    """Answers each sentence prompt with a canned rewrite (greedy for n=1, samples otherwise)."""

    def generate(self, prompt, n=1, temperature=0.0, max_new_tokens=128):
        sentence = prompt.split("simplify: ", 1)[-1].strip()
        rewrites = {"There is no pleural effusion or pneumothorax.": ["No fluid around the lungs or air outside the lungs."]}
        found = rewrites.get(sentence, [])
        return found[:1] if temperature == 0 else found


def test_run_returns_the_hybrid_next_to_the_rules_with_the_shape_the_page_expects(monkeypatch):
    from demo import server
    from src.verify import Verifier

    verifier = Verifier(entail_fn=lambda premise, hypotheses: [0.95] * len(hypotheses))
    monkeypatch.setattr(server, "models", lambda: (_FakeT5(), verifier))
    report = "FINDINGS: There is no pleural effusion or pneumothorax. Heart size is within normal limits."
    out = server.run(report, "quick")           # the old mode names are still accepted and ignored
    assert out["mode"] == "hybrid" and out["source"] == report
    assert out["selected"]["text"].startswith("No fluid around the lungs or air outside the lungs.")   # the model's sentence passed
    assert out["plain"]["text"] == "There is no fluid around the lungs or air leak around the lung. Heart size is normal."   # rules only
    assert out["units"] == {"model": 1, "rules": 1, "total": 2}
    for side in ("plain", "selected"):
        assert {"score", "sentences", "summary", "source_sentences"} <= set(out[side]["explain"])
