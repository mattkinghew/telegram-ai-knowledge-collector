from __future__ import annotations

import ast
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from business_knowledge_capture.cli import build_parser, main
from business_knowledge_capture.core import (
    DisabledSummarizer,
    create_inbox_note,
    extract_source,
    generate_progress_report,
    initialize_vault,
    load_protected_patterns,
)


class PythonCompatibilityTests(unittest.TestCase):
    def test_cli_parser_loads(self) -> None:
        parser = build_parser()
        vault_path = Path(tempfile.gettempdir()).resolve() / "example-vault"
        args = parser.parse_args(["validate", "--vault", str(vault_path)])
        self.assertEqual(args.command, "validate")

    def test_cli_reports_path_errors_without_traceback(self) -> None:
        temp_root = Path(tempfile.gettempdir()).resolve()
        vault_path = temp_root / "example-vault"
        external_path = temp_root / "external.md"
        error_output = StringIO()
        with redirect_stderr(error_output):
            result = main(
                [
                    "review",
                    "--vault",
                    str(vault_path),
                    "--note",
                    str(external_path),
                ]
            )
        self.assertEqual(result, 2)
        self.assertTrue(error_output.getvalue().startswith("ERROR:"))
        self.assertNotIn("Traceback", error_output.getvalue())

    def test_progress_report_flow_executes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory).resolve() / "vault"
            (vault / "00_Inbox").mkdir(parents=True)
            (vault / "10_Work" / "11_Projects").mkdir(parents=True)
            (vault / "90_System").mkdir()
            initialize_vault(vault)
            source = extract_source(
                vault=vault,
                patterns=load_protected_patterns(vault),
                text="Compatibility report input",
            )
            note = create_inbox_note(
                vault=vault,
                source=source,
                summarizer=DisabledSummarizer(),
            )
            report = generate_progress_report(
                vault=vault,
                completed_paths=[note],
                in_progress_paths=[],
                period_label="compatibility",
                report_type="daily",
            )
            self.assertTrue(report.is_file())

    def test_annotations_do_not_use_union_operator_syntax(self) -> None:
        source_root = Path(__file__).parents[1] / "src"
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                annotation = None
                if isinstance(node, ast.arg):
                    annotation = node.annotation
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    annotation = node.returns
                elif isinstance(node, ast.AnnAssign):
                    annotation = node.annotation
                if annotation is not None:
                    self.assertFalse(
                        any(
                            isinstance(child, ast.BinOp) and isinstance(child.op, ast.BitOr)
                            for child in ast.walk(annotation)
                        ),
                        f"Python 3.10 union syntax found in {path}",
                    )


if __name__ == "__main__":
    unittest.main()
