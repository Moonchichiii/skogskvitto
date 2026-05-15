@'
from pathlib import Path

ROOT = Path.cwd()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


# Remove one-off repair script from lint scope.
one_off = ROOT / "scripts" / "fix_current_failures.py"
if one_off.exists():
    one_off.unlink()


# Make test settings explicitly use root templates.
test_settings_path = ROOT / "config" / "settings" / "test.py"
test_settings = read(test_settings_path)

line = 'TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]'

if line not in test_settings:
    test_settings = test_settings.rstrip() + "\n\n# Root-level templates are the source of truth.\n" + line + "\n"

write(test_settings_path, test_settings)


# If conftest.py has its own TEMPLATES config, patch that too.
conftest_path = ROOT / "tests" / "conftest.py"

if conftest_path.exists():
    conftest = read(conftest_path)
    changed = False

    if '"DIRS": []' in conftest:
        conftest = conftest.replace(
            '"DIRS": []',
            '"DIRS": [BASE_DIR / "templates"]',
        )
        changed = True

    if "'DIRS': []" in conftest:
        conftest = conftest.replace(
            "'DIRS': []",
            "'DIRS': [BASE_DIR / 'templates']",
        )
        changed = True

    if changed and "BASE_DIR = Path(__file__).resolve().parents[1]" not in conftest:
        if "from pathlib import Path" not in conftest:
            conftest = "from pathlib import Path\n" + conftest

        marker = "import os\n"
        if marker in conftest:
            conftest = conftest.replace(
                marker,
                marker + "\nBASE_DIR = Path(__file__).resolve().parents[1]\n",
                1,
            )
        else:
            conftest = (
                "BASE_DIR = Path(__file__).resolve().parents[1]\n\n"
                + conftest
            )

    write(conftest_path, conftest)


print("Test/template config fixed.")
'@ | Set-Content scripts\fix_test_template_config.py -Encoding utf8

uv run python scripts\fix_test_template_config.py