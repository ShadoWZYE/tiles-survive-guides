import json,unittest
from pathlib import Path
from audit_replay_authority import build
from render_reconstruction_report import render
class ReconstructionEvidenceTests(unittest.TestCase):
    def test_replay_trace_cannot_be_reused_on_unknown_native_artifacts(self):
        with self.assertRaisesRegex(ValueError,'Unverified'):build(b'unknown',b'unknown',b'unknown')
    def test_saved_error_tables_and_replay_findings_render_reproducibly(self):
        root=Path(__file__).resolve().parents[2]
        r=json.loads((root/'outputs/hero-report/Retrospective-Damage-Reconstruction.json').read_text(encoding='utf-8'))
        text=render(r)
        self.assertEqual(text,(root/'docs/research/RETROSPECTIVE-RECONSTRUCTION-2026-11-07.md').read_text(encoding='utf-8'))
        self.assertIn('24.1%',text);self.assertIn('1.2%',text);self.assertIn('42.2%',text)
        audit=json.loads((root/'outputs/hero-report/Replay-Authority-Audit.json').read_text(encoding='utf-8'))
        self.assertEqual(len(audit['methods']),13)
        self.assertTrue(any(m['type']=='HeroPropertyComponent' and m['name']=='SupplyBattleReportProperty' for m in audit['methods']))
if __name__=='__main__':unittest.main()
