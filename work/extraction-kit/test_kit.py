import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

import kit


class KitTests(unittest.TestCase):
    def fixture(self, root):
        # Synthetic SOS pack: name-slot indirection plus one active entry.
        data = bytearray(4096 * 272)
        data[:4] = b"\0SOS"
        struct.pack_into("<III", data, 4, 4096, 4096, 1)
        struct.pack_into("<III", data, 16, 2, 271, 4)
        position = 16 + 4096 * 12 + 2 * 256
        data[position:position + 5] = b"\x04demo"
        data[271 * 4096:271 * 4096 + 4] = b"test"
        source = root / "game" / "pack.ss"
        source.parent.mkdir()
        source.write_bytes(data)
        return source

    def test_relocated_extraction_records_hashes_and_preserves_source(self):
        with tempfile.TemporaryDirectory(prefix="kit path with spaces ") as temp:
            root = Path(temp)
            source = self.fixture(root)
            before = kit.sha256(source)
            output = root / "private" / "run one"
            args = kit.parser().parse_args(["config", "--pack", str(source), "--output", str(output)])
            with contextlib.redirect_stdout(io.StringIO()):
                kit.run(args)
            report = json.loads((output / "run.json").read_text())
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["inputs"][0]["sha256"], before)
            self.assertEqual(kit.sha256(source), before)
            self.assertEqual((output / "tables/0000_demo.cfg").read_bytes(), b"test")
            with self.assertRaises(FileExistsError):
                kit.run(args)

    def test_output_cannot_be_inside_game(self):
        with tempfile.TemporaryDirectory() as temp:
            source = self.fixture(Path(temp))
            output = source.parent / "extract"
            args = kit.parser().parse_args(["config", "--pack", str(source), "--output", str(output)])
            with self.assertRaisesRegex(ValueError, "separate"):
                kit.run(args)
            self.assertFalse(output.exists())

    def test_bad_pack_records_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            source = self.fixture(Path(temp))
            source.write_bytes(b"broken")
            output = Path(temp) / "result"
            args = kit.parser().parse_args(["config", "--pack", str(source), "--output", str(output)])
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                kit.run(args)
            self.assertEqual(json.loads((output / "run.json").read_text())["status"], "failed")

    def test_discovery_reports_all_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for version in ("old", "new"):
                directory = root / version
                directory.mkdir()
                (directory / "BinaryConfigPack.ss").write_bytes(b"example")
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                kit.discover(root)
            result = json.loads(stream.getvalue())
            self.assertEqual(len(result["candidates"]["**/BinaryConfigPack.ss"]), 2)


if __name__ == "__main__":
    unittest.main()
