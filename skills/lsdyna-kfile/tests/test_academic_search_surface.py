import ast
import importlib.util
import logging
import unittest
from pathlib import Path


SERVER_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor"
    / "academic-search-mcp"
    / "academic_search_server.py"
)


class AcademicSearchToolSurfaceTests(unittest.TestCase):
    def test_only_search_tools_are_exposed(self):
        tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
        exposed = []
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "mcp"
                    and decorator.func.attr == "tool"
                ):
                    exposed.append(node.name)

        self.assertEqual(
            exposed,
            ["search_papers", "search_scopus", "search_sciencedirect"],
        )

    def test_source_classes_only_expose_search_operations(self):
        source_dir = SERVER_PATH.parent / "sources"
        public_methods = {}
        for source_path in sorted(source_dir.glob("*.py")):
            if source_path.name in {"__init__.py", "elsevier_common.py"}:
                continue
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or not node.name.endswith("Source"):
                    continue
                public_methods[node.name] = [
                    child.name
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not child.name.startswith("_")
                ]

        self.assertEqual(
            public_methods,
            {
                "ArxivSource": ["search"],
                "CrossRefSource": ["search"],
                "PubMedSource": ["search"],
                "ScienceDirectSource": ["search"],
                "ScopusSource": ["search"],
            },
        )

    def test_logging_setup_is_idempotent(self):
        logging_path = SERVER_PATH.parent / "utils" / "logging.py"
        spec = importlib.util.spec_from_file_location("academic_search_logging", logging_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        logger = logging.getLogger("academic-search")
        original_handlers = list(logger.handlers)
        self.addCleanup(setattr, logger, "handlers", original_handlers)
        logger.handlers = []

        module.setup_logging()
        module.setup_logging()

        managed = [
            handler
            for handler in logger.handlers
            if getattr(handler, "_kagent_academic_search", False)
        ]
        self.assertEqual(len(managed), 1)
        self.assertFalse(logger.propagate)


if __name__ == "__main__":
    unittest.main()
