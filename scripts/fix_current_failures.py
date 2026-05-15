from pathlib import Path

ROOT = Path.cwd()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


# 1. Ensure root templates directory is registered.
settings_path = ROOT / "config" / "settings" / "base.py"
settings = read(settings_path)

settings = settings.replace(
    '"DIRS": [],',
    '"DIRS": [BASE_DIR / "templates"],',
)

if '"DIRS": [BASE_DIR / "templates"],' not in settings:
    settings = settings.replace(
        '"APP_DIRS": True,',
        '"DIRS": [BASE_DIR / "templates"],\n        "APP_DIRS": True,',
    )

write(settings_path, settings)


# 2. Restore transactional email templates in root templates/email.
write(
    ROOT / "templates" / "email" / "kvitto_mottaget.txt",
    """Hej {{ user_name }},

Vi har tagit emot ditt kvitto och sparat det sÃ¤kert i SkogsKvitto.

Detaljer:
  LeverantÃ¶r : {{ vendor|default:"â€“" }}
  Datum      : {{ receipt_date|default:"â€“" }}
  Belopp     : {{ total_amount|default:"â€“" }} kr

Du hittar kvittot i din dashboard nÃ¤r du loggar in.

Med vÃ¤nliga hÃ¤lsningar,
SkogsKvitto
""",
)

write(
    ROOT / "templates" / "email" / "tack_for_betalningen.txt",
    """Hej {{ user_name }},

Tack fÃ¶r din betalning. Din prenumeration pÃ¥ SkogsKvitto Ã¤r nu aktiv.

Plan        : {{ plan_name|default:"â€“" }}
Giltig t.o.m.: {{ period_end|default:"â€“" }}

Du kan nÃ¤r som helst hantera din prenumeration via din profil.

Med vÃ¤nliga hÃ¤lsningar,
SkogsKvitto
""",
)

write(
    ROOT / "templates" / "email" / "valkommen.txt",
    """Hej {{ user_name }},

VÃ¤lkommen till SkogsKvitto. Ditt konto Ã¤r nu aktiverat.

Du kan bÃ¶rja ladda upp och granska kvitton direkt.

Logga in hÃ¤r: {{ login_url }}

Med vÃ¤nliga hÃ¤lsningar,
SkogsKvitto
""",
)


# 3. Product decision: bottom nav is 3 buttons, profile stays in header.
test_profile_path = ROOT / "tests" / "test_profile_navigation.py"
test_profile = read(test_profile_path)
test_profile = test_profile.replace(
    '    assert "Profil" in bottom_template\n',
    "",
)
write(test_profile_path, test_profile)


# 4. Fix exact dashboard text that test expects.
dashboard_path = ROOT / "templates" / "receipts" / "dashboard.html"
dashboard = read(dashboard_path)
dashboard = dashboard.replace("Export och nedladdning ingÃƒÂ¥r i betalplanen.", "Export och nedladdning ingÃ¥r i betalplanen.")
dashboard = dashboard.replace("Uppgradera fÃƒÂ¶r att ladda ner Excel/PDF.", "Uppgradera fÃ¶r att ladda ner Excel/PDF.")
dashboard = dashboard.replace("Total utlÃƒÂ¤gg", "Totala utlÃ¤gg")
dashboard = dashboard.replace("KÃƒÂ¶rjournal", "KÃ¶rjournal")
dashboard = dashboard.replace("Ãƒâ€¦rsrapport", "Ã…rsrapport")
dashboard = dashboard.replace("OkÃƒÂ¤nd", "OkÃ¤nd")
dashboard = dashboard.replace("Inga kvitton ÃƒÂ¤nnu. BÃƒÂ¶rja scanna!", "Inga kvitton Ã¤nnu. BÃ¶rja scanna!")
dashboard = dashboard.replace("FÃƒÂ¶regÃƒÂ¥ende", "FÃ¶regÃ¥ende")
dashboard = dashboard.replace("NÃƒÂ¤sta", "NÃ¤sta")
dashboard = dashboard.replace("ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“", "â€“")
write(dashboard_path, dashboard)


# 5. Remove old helper script from lint scope if it only exists as a one-off repair tool.
repair_script = ROOT / "scripts" / "repair_ui_cleanup.py"
if repair_script.exists():
    repair_script.unlink()


print("Fix complete.")
