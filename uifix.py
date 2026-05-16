import os
from pathlib import Path
import unicodedata

ROOT = Path.cwd()
UTF8 = "utf-8"

def write(path_str: str, content: str) -> None:
    target = ROOT / path_str
    target.parent.mkdir(parents=True, exist_ok=True)
    # Vi trimmar och ser till att filen slutar med en newline
    final_content = content.strip() + "\n"
    target.write_text(final_content, encoding=UTF8, newline="\n")

# ---------------------------------------------------------------------
# 1. Base Layout med fixad metadata och scripts
# ---------------------------------------------------------------------
write("templates/layouts/base.html", """<!doctype html>
<html lang="sv">
<head>
    {% load static %}
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}SkogsKvitto{% endblock %}</title>
    <meta name="description" content="{% block meta_description %}SkogsKvitto hjälper skogsägare att samla kvitton och exportera underlag.{% endblock %}">
    <link rel="icon" href="{% static 'img/favicon.svg' %}" type="image/svg+xml">
    <link rel="stylesheet" href="{% static 'css/app.css' %}">
    {% block extra_head %}{% endblock %}
</head>
<body class="app-body">
    <div class="site-shell">
        {% include "partials/header.html" %}
        <main id="content" class="page-shell {% if user.is_authenticated %}page-shell-auth{% endif %}">
            {% include "partials/messages.html" %}
            {% block content %}{% endblock %}
        </main>
        {% include "partials/footer.html" %}
        {% include "partials/mobile_nav.html" %}
    </div>
    <script defer src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js"></script>
    <script defer src="{% static 'js/mobile-nav.js' %}"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>""")

# ---------------------------------------------------------------------
# 2. Billing & Accounts - Fixa svenska tecken i existerande filer
# ---------------------------------------------------------------------
def fix_mojibake(file_path: Path):
    if not file_path.exists():
        return
    content = file_path.read_text(encoding="utf-8-sig")
    replacements = {
        "kr?vs": "krävs",
        "niv?": "nivå",
        "Pilot?tkomst": "Särskild åtkomst",
        "betalplanen.": "betalplanen.",
        "tillg?nglig": "tillgänglig",
        "l?nk": "länk",
        "slutf?rd": "slutförd",
        "anv?ndare": "användare",
        "fr?n": "från",
        "Ã¥": "å", "Ã¤": "ä", "Ã¶": "ö",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    file_path.write_text(content, encoding=UTF8, newline="\n")

fix_mojibake(ROOT / "apps/billing/services.py")
fix_mojibake(ROOT / "apps/billing/views.py")

# ---------------------------------------------------------------------
# 3. API - Fixa saknad _get_authenticated_user
# ---------------------------------------------------------------------
api_path = ROOT / "apps/receipts/api.py"
if api_path.exists():
    content = api_path.read_text(encoding=UTF8)
    if "async def _get_authenticated_user" not in content:
        helper_code = """
async def _get_authenticated_user(request: HttpRequest) -> User | None:
    from asgiref.sync import sync_to_async
    def resolve():
        return cast(User, request.user) if request.user.is_authenticated else None
    return await sync_to_async(resolve, thread_sensitive=True)()
"""
        content = content.replace('from apps.billing.services import', 'from apps.core.models import User\nfrom apps.billing.services import')
        content += helper_code
        api_path.write_text(content, encoding=UTF8)

# ---------------------------------------------------------------------
# 4. CSS - Komplett Tailwind v4 kompatibel CSS
# ---------------------------------------------------------------------
# Vi använder f-string för att undvika problem med @apply och måsvingar
css_content = """@import "tailwindcss";

@theme {
  --color-forest: #003d2f;
  --color-forest-deep: #00291f;
  --color-skog-bg: #faf9f3;
}

@layer base {
  body {
    @apply min-h-screen bg-[#faf9f3] text-[#10231d];
    font-family: Inter, system-ui, sans-serif;
  }
}

@layer components {
  .btn-primary {
    @apply inline-flex min-h-14 items-center justify-center rounded-full bg-[#00291f] px-8 text-lg font-black text-white transition-all hover:bg-[#0f6b4f];
  }
  
  .btn-secondary {
    @apply inline-flex min-h-14 items-center justify-center rounded-full border border-forest/10 bg-white px-8 text-lg font-black text-forest transition-all hover:bg-emerald-50;
  }

  .card {
    @apply rounded-3xl border border-forest/10 bg-white/95 p-6 shadow-sm backdrop-blur-sm;
  }

  .nav-link-active {
    @apply bg-[#00291f] text-white;
  }
}"""
write("static/src/input.css", css_content)

# ---------------------------------------------------------------------
# 5. Global tecken-tvätt för alla filer
# ---------------------------------------------------------------------
common_sw_map = {
    "Ã¤": "ä", "Ã¥": "å", "Ã¶": "ö",
    "f?rhandsvisning": "förhandsvisning",
    "kr/?r": "kr/år",
    "kr/m?n": "kr/mån",
    "Ink?p": "Inköp",
    "K?rjournal": "Körjournal"
}

for folder in ["apps", "templates", "static/js"]:
    for p in (ROOT / folder).rglob("*"):
        if p.suffix in [".html", ".py", ".js"]:
            c = p.read_text(encoding="utf-8-sig")
            orig = c
            for k, v in common_sw_map.items():
                c = c.replace(k, v)
            if c != orig:
                p.write_text(c, encoding=UTF8)

print("✅ Phase 1 Repair Script slutfört.")