import ast
import difflib
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Optional


MAX_FILE_SIZE_BYTES = 4_000
IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


@dataclass
class FileInfo:
    path: Path
    size: int
    skipped: bool
    reason: Optional[str] = None


@dataclass
class PatchPlan:
    target_file: Path
    old_code: str
    new_code: str
    reason: str


class DemoRepoCreator:
    def create(self, repo_path: Path) -> None:
        repo_path.mkdir(exist_ok=True)

        app_file = repo_path / "app.py"
        requirements_file = repo_path / "requirements.txt"
        large_file = repo_path / "large_notes.txt"

        if not app_file.exists():
            app_file.write_text(
                """
import requests


def greet(name):
    return "Hello " + name
""".strip()
                + "\n",
                encoding="utf-8",
            )

        if not requirements_file.exists():
            requirements_file.write_text(
                """
# requests is missing on purpose
""".strip()
                + "\n",
                encoding="utf-8",
            )

        if not large_file.exists():
            large_file.write_text("large file content\n" * 1000, encoding="utf-8")


class RepoReader:
    def scan(self, repo_path: Path) -> List[FileInfo]:
        files = []

        for path in repo_path.rglob("*"):
            if path.is_dir():
                continue

            if any(part in IGNORED_DIRS for part in path.parts):
                continue

            size = path.stat().st_size

            if size > MAX_FILE_SIZE_BYTES:
                files.append(
                    FileInfo(
                        path=path,
                        size=size,
                        skipped=True,
                        reason="Large file skipped",
                    )
                )
            else:
                files.append(
                    FileInfo(
                        path=path,
                        size=size,
                        skipped=False,
                    )
                )

        return files


class DependencyScanner:
    def get_python_imports(self, repo_path: Path) -> Set[str]:
        imports = set()

        for py_file in repo_path.rglob("*.py"):
            if any(part in IGNORED_DIRS for part in py_file.parts):
                continue

            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])

        return imports

    def get_declared_dependencies(self, repo_path: Path) -> Set[str]:
        req_file = repo_path / "requirements.txt"

        if not req_file.exists():
            return set()

        dependencies = set()

        for line in req_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            package = (
                line.split("==")[0]
                .split(">=")[0]
                .split("<=")[0]
                .split("~=")[0]
                .strip()
                .lower()
                .replace("_", "-")
            )

            dependencies.add(package)

        return dependencies

    def detect_hidden_dependencies(self, repo_path: Path) -> List[str]:
        imports = self.get_python_imports(repo_path)
        declared = self.get_declared_dependencies(repo_path)

        stdlib = set(sys.stdlib_module_names)
        local_modules = {p.stem for p in repo_path.rglob("*.py")}

        hidden = []

        for package in imports:
            normalized = package.lower().replace("_", "-")

            if package in stdlib:
                continue

            if package in local_modules:
                continue

            if normalized not in declared:
                hidden.append(package)

        return sorted(hidden)


class PatchPlanner:
    def plan(self, repo_path: Path) -> Optional[PatchPlan]:
        target = repo_path / "app.py"

        if not target.exists():
            return None

        old_code = target.read_text(encoding="utf-8")

        old_function = """
def greet(name):
    return "Hello " + name
""".strip()

        new_function = """
def greet(name: str) -> str:
    \"\"\"Return a greeting for a non-empty name.\"\"\"
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    return f"Hello, {name.strip()}"
""".strip()

        if old_function not in old_code:
            return None

        new_code = old_code.replace(old_function, new_function)

        return PatchPlan(
            target_file=target,
            old_code=old_code,
            new_code=new_code,
            reason="Improve greet() with typing, validation, and cleaner formatting.",
        )


class PatchValidator:
    def validate_python_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            print(f"Syntax validation failed: line {e.lineno}: {e.msg}")
            return False


class FileEditor:
    def apply_patch(self, plan: PatchPlan) -> None:
        backup_path = plan.target_file.with_suffix(plan.target_file.suffix + ".bak")
        temp_path = plan.target_file.with_suffix(plan.target_file.suffix + ".tmp")

        shutil.copy2(plan.target_file, backup_path)

        temp_path.write_text(plan.new_code, encoding="utf-8")
        shutil.move(str(temp_path), str(plan.target_file))

        print(f"Backup created: {backup_path}")
        print(f"Patched file: {plan.target_file}")


class RepoPatchAgent:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.reader = RepoReader()
        self.dependency_scanner = DependencyScanner()
        self.planner = PatchPlanner()
        self.validator = PatchValidator()
        self.editor = FileEditor()

    def show_diff(self, old_code: str, new_code: str) -> None:
        diff = difflib.unified_diff(
            old_code.splitlines(),
            new_code.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )

        print("\nPatch diff:")
        for line in diff:
            print(line)

    def run(self) -> None:
        print(f"Scanning repo: {self.repo_path}")

        files = self.reader.scan(self.repo_path)

        print("\nFiles:")
        for file in files:
            if file.skipped:
                print(f"- {file.path} ({file.size} bytes) SKIPPED: {file.reason}")
            else:
                print(f"- {file.path} ({file.size} bytes)")

        hidden_deps = self.dependency_scanner.detect_hidden_dependencies(self.repo_path)

        if hidden_deps:
            print("\nHidden dependencies detected:")
            for dep in hidden_deps:
                print(f"- {dep} imported but not listed in requirements.txt")
        else:
            print("\nNo hidden dependencies detected.")

        plan = self.planner.plan(self.repo_path)

        if not plan:
            print("\nNo safe patch plan found.")
            return

        print("\nPatch reason:")
        print(plan.reason)

        self.show_diff(plan.old_code, plan.new_code)

        if not self.validator.validate_python_syntax(plan.new_code):
            print("\nPatch rejected: new code has syntax errors.")
            return

        self.editor.apply_patch(plan)

        print("\nPatch applied successfully.")


if __name__ == "__main__":
    repo = Path("demo_repo")

    DemoRepoCreator().create(repo)

    agent = RepoPatchAgent(repo)
    agent.run()