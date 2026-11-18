"""Portable transcript writer regression checks (no macOS frameworks needed)."""
import ast
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'cj-meetings/teams-captions.py'
tree = ast.parse(SOURCE.read_text())
writer = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'write')
namespace = dict(os=os, tempfile=tempfile)
exec(compile(ast.Module(body=[writer], type_ignores=[]), str(SOURCE), 'exec'), namespace)


class TranscriptSecurity(unittest.TestCase):
    def test_private_atomic_replacement_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'transcript.md'
            victim = Path(directory) / 'victim.md'
            victim.write_text('unchanged')
            Path(str(path) + '.tmp').symlink_to(victim)
            previous = os.umask(0)
            try:
                namespace['write'](path, [('12:00', 'Alice', 'Hello')], 'today')
            finally:
                os.umask(previous)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn('Alice', path.read_text())
            self.assertEqual(victim.read_text(), 'unchanged')
            with patch.object(os, 'replace', side_effect=OSError('fake failure')):
                with self.assertRaises(OSError):
                    namespace['write'](path, [], 'today')
            self.assertEqual(list(Path(directory).glob('.teams-captions-*')), [])


class LintSecurity(unittest.TestCase):
    def test_shellcheck_temp_is_unique_and_cleaned_on_exit(self):
        source = (SOURCE.parents[1] / 'scripts/lint.sh').read_text()
        block = source.split('    shellcheck_err="$(mktemp)"', 1)[1].split('\nelse\n', 1)[0]
        for status in (0, 1):
            with tempfile.TemporaryDirectory() as directory:
                script = ('report() { :; }; shellcheck() { printf "%s" "$shellcheck_err" > "$TMPDIR/observed"; return ' + str(status) + '; }; shell_files=(fake.sh);\n'
                          + 'shellcheck_err="$(mktemp)"' + block)
                result = subprocess.run(['bash', '-c', script], env={**os.environ, 'TMPDIR': directory}, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                observed = Path(directory, 'observed').read_text()
                self.assertNotEqual(observed, '/tmp/skills-shellcheck.err')
                self.assertTrue(Path(observed).is_absolute())
                self.assertFalse(Path(observed).exists())


if __name__ == '__main__':
    unittest.main()
