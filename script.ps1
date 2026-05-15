# ui-reset-phase-1.ps1
$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding

Write-Host "== SkogsKvitto UI reset phase 1 ==" -ForegroundColor Cyan

New-Item -ItemType Directory -Force templates\layouts | Out-Null
New-Item -ItemType Directory -Force templates\partials | Out-Null
New-Item -ItemType Directory -Force templates\account | Out-Null
New-Item -ItemType Directory -Force templates\legal | Out-Null
New-Item -ItemType Directory -Force templates\receipts\partials | Out-Null
New-Item -ItemType Directory -Force static\src | Out-Null
New-Item -ItemType Directory -Force static\css | Out-Null
New-Item -ItemType Directory -Force static\js | Out-Null

Remove-Item templates\layouts\app.html -Force -ErrorAction SilentlyContinue

Set-Content templates\layouts\base.html @'
<!doctype html>
<html lang="sv">
<head>
  {% load static %}
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}SkogsKvitto{% endblock %}</title>
  <meta name="description" content="{% block meta_description %}SkogsKvitto hjälper skogsägare att samla kvitton, granska underlag och exportera till bokföring.{% endblock %}">
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

    {% include "partials/mobile_nav.html" %}
    {% include "partials/cookie_banner.html" %}
    {% include "partials/footer.html" %}
  </div>

  <script defer src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js"></script>
  <script defer src="{% static 'js/mobile-nav.js' %}"></script>
  <script defer src="{% static 'js/cookie-banner.js' %}"></script>
  <script defer src="{% static 'js/receipt-upload.js' %}"></script>
  <script defer src="{% static 'js/correction-suggestion.js' %}"></script>
  {% block extra_scripts %}{% endblock %}
</body>
</html>
'@ -Encoding utf8

Set-Content templates\partials\header.html @'
<header class="site-header">
  <nav class="site-header-inner" aria-label="Huvudnavigering">
    {% with current_url_name=request.resolver_match.url_name %}
    <a href="{% url 'scan' %}" class="brand-link" aria-label="Gå till SkogsKvitto">
      <span class="brand-mark" aria-hidden="true">♲</span>
      <span>SkogsKvitto</span>
    </a>

    {% if user.is_authenticated %}
      <div class="desktop-nav">
        <a href="{% url 'scan' %}" class="nav-link {% if current_url_name == 'scan' %}nav-link-active{% endif %}">Scanna</a>
        <a href="{% url 'dashboard' %}" class="nav-link {% if current_url_name == 'dashboard' and request.GET.nav != 'export' %}nav-link-active{% endif %}">Granska</a>
        <a href="{% url 'dashboard' %}?nav=export#dashboard-export" class="nav-link {% if current_url_name == 'dashboard' and request.GET.nav == 'export' %}nav-link-active{% endif %}">Exportera</a>
        <a href="{% url 'profile' %}" class="nav-link {% if current_url_name == 'profile' %}nav-link-active{% endif %}">Profil</a>
      </div>

      <button
        type="button"
        class="menu-button"
        data-mobile-menu-button
        aria-expanded="false"
        aria-controls="mobile-menu"
      >
        Meny
      </button>

      <div id="mobile-menu" class="mobile-menu" data-mobile-menu-panel hidden>
        <a href="{% url 'scan' %}" class="mobile-menu-link">Scanna</a>
        <a href="{% url 'dashboard' %}" class="mobile-menu-link">Granska</a>
        <a href="{% url 'dashboard' %}?nav=export#dashboard-export" class="mobile-menu-link">Exportera</a>
        <a href="{% url 'profile' %}" class="mobile-menu-link">Profil</a>
        <a href="{% url 'account_logout' %}" class="mobile-menu-link">Logga ut</a>
      </div>
    {% else %}
      <a href="{% url 'account_login' %}" class="nav-link">Logga in</a>
    {% endif %}
    {% endwith %}
  </nav>
</header>
'@ -Encoding utf8

Set-Content templates\partials\footer.html @'
<footer class="site-footer">
  <div class="site-footer-inner">
    <div>
      <p class="font-semibold text-forest-950">SkogsKvitto</p>
      <p class="mt-1 text-sm text-stone-600">Kvitton, underlag och export för svenska skogsägare.</p>
    </div>

    <nav class="footer-links" aria-label="Juridiska länkar">
      <a href="{% url 'privacy_policy' %}">Integritet</a>
      <a href="{% url 'terms_of_service' %}">Villkor</a>
      <a href="{% url 'cookies' %}">Cookies</a>
    </nav>
  </div>
</footer>
'@ -Encoding utf8

Set-Content templates\partials\mobile_nav.html @'
{% if user.is_authenticated %}
{% with current_url_name=request.resolver_match.url_name %}
<nav class="mobile-bottom-nav" aria-label="Bottennavigering">
  <a href="{% url 'scan' %}" class="mobile-bottom-link {% if current_url_name == 'scan' %}mobile-bottom-link-active{% endif %}">
    <span aria-hidden="true">＋</span>
    <span>Scanna</span>
  </a>
  <a href="{% url 'dashboard' %}" class="mobile-bottom-link {% if current_url_name == 'dashboard' and request.GET.nav != 'export' %}mobile-bottom-link-active{% endif %}">
    <span aria-hidden="true">✓</span>
    <span>Granska</span>
  </a>
  <a href="{% url 'dashboard' %}?nav=export#dashboard-export" class="mobile-bottom-link {% if current_url_name == 'dashboard' and request.GET.nav == 'export' %}mobile-bottom-link-active{% endif %}">
    <span aria-hidden="true">↓</span>
    <span>Exportera</span>
  </a>
</nav>
{% endwith %}
{% endif %}
'@ -Encoding utf8

Set-Content templates\partials\messages.html @'
{% if messages %}
<section class="mb-5 space-y-2" aria-label="Meddelanden">
  {% for message in messages %}
    <div class="notice">
      {{ message }}
    </div>
  {% endfor %}
</section>
{% endif %}
'@ -Encoding utf8

Set-Content templates\partials\cookie_banner.html @'
<div
  data-cookie-banner
  hidden
  class="cookie-banner"
  role="dialog"
  aria-label="Cookie-information"
>
  <div>
    <p class="text-sm font-semibold text-forest-950">Nödvändiga cookies</p>
    <p class="mt-1 text-sm leading-relaxed text-stone-600">
      SkogsKvitto använder bara cookies som krävs för inloggning, CSRF-skydd och sessionshantering.
      Vi använder inga spårnings- eller marknadsföringscookies.
      <a href="{% url 'cookies' %}" class="text-link">Läs mer</a>.
    </p>
  </div>
  <button type="button" data-cookie-accept class="btn-primary shrink-0">Förstått</button>
</div>
'@ -Encoding utf8

Set-Content templates\account\login.html @'
{% extends "layouts/base.html" %}
{% load socialaccount %}

{% block title %}Logga in | SkogsKvitto{% endblock %}

{% block content %}
<section class="auth-card">
  <div class="auth-icon" aria-hidden="true">♲</div>

  <div class="text-center">
    <p class="eyebrow">SkogsKvitto</p>
    <h1 class="mt-2 text-3xl font-bold tracking-tight text-forest-950">Logga in</h1>
    <p class="mt-3 text-sm leading-relaxed text-stone-600">
      Fortsätt med ditt Google-konto för att scanna, granska och exportera dina skogskvitton.
    </p>
  </div>

  <a href="{% provider_login_url 'google' process='login' %}" class="btn-primary w-full justify-center">
    Fortsätt med Google
  </a>

  <p class="text-center text-xs leading-relaxed text-stone-500">
    Endast nödvändiga cookies används för inloggning och säkerhet.
  </p>
</section>
{% endblock %}
'@ -Encoding utf8

Set-Content templates\account\profile.html @'
{% extends "layouts/base.html" %}

{% block title %}Min profil | SkogsKvitto{% endblock %}

{% block content %}
<section class="page-stack">
  <header class="hero-card">
    <p class="eyebrow">Konto</p>
    <h1 class="hero-title">Min profil</h1>
    <p class="hero-text">Hantera konto, plan och åtkomst till export.</p>
  </header>

  <div class="grid gap-4 md:grid-cols-3">
    <article class="card md:col-span-2">
      <h2 class="card-title">Kontouppgifter</h2>
      <dl class="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <dt class="detail-label">E-post</dt>
          <dd class="detail-value">{{ user.email }}</dd>
        </div>
        {% if full_name %}
        <div>
          <dt class="detail-label">Namn</dt>
          <dd class="detail-value">{{ full_name }}</dd>
        </div>
        {% endif %}
        <div>
          <dt class="detail-label">Skapad</dt>
          <dd class="detail-value">{{ user.date_joined|date:"Y-m-d" }}</dd>
        </div>
        <div>
          <dt class="detail-label">Status</dt>
          <dd class="detail-value">
            {% if is_testpilot %}
              Testpilot
            {% else %}
              {{ plan_label }}
            {% endif %}
          </dd>
        </div>
      </dl>
    </article>

    <article class="card">
      <h2 class="card-title">Plan</h2>
      <p class="mt-3 text-2xl font-bold text-forest-950">{{ plan_label }}</p>
      <p class="mt-2 text-sm leading-relaxed text-stone-600">{{ plan_description }}</p>
    </article>
  </div>

  <article class="card">
    <h2 class="card-title">Användning</h2>
    <div class="mt-4 grid gap-4 sm:grid-cols-3">
      <div class="metric-tile">
        <p class="metric-label">Sparade kvitton</p>
        <p class="metric-value">{{ receipt_count }}</p>
      </div>
      <div class="metric-tile">
        <p class="metric-label">Gratisgräns</p>
        <p class="metric-value">{{ free_receipt_limit }}</p>
      </div>
      <div class="metric-tile">
        <p class="metric-label">Export</p>
        <p class="metric-value">{% if export_enabled %}Aktiv{% else %}Låst{% endif %}</p>
      </div>
    </div>
  </article>

  <article class="card">
    <h2 class="card-title">Åtgärder</h2>
    <div class="mt-4 grid gap-3 sm:grid-cols-2">
      {% if export_enabled %}
        <a href="{% url 'dashboard' %}?nav=export#dashboard-export" class="btn-primary justify-center">Gå till export</a>
      {% else %}
        <a href="{% url 'start_checkout' %}?plan=yearly" class="btn-primary justify-center">Uppgradera</a>
      {% endif %}
      <a href="{% url 'account_logout' %}" class="btn-secondary justify-center">Logga ut</a>
    </div>
  </article>
</section>
{% endblock %}
'@ -Encoding utf8

Set-Content templates\receipts\scan.html @'
{% extends "layouts/base.html" %}

{% block title %}Scanna kvitto | SkogsKvitto{% endblock %}

{% block content %}
<section class="page-stack">
  <header class="hero-grid">
    <div>
      <p class="eyebrow">SkogsKvitto</p>
      <h1 class="hero-title">Scanna, granska och exportera skogskvitton.</h1>
      <p class="hero-text">
        Ta en bild på kvittot, kontrollera tolkningen och bygg ett tydligt underlag för bokföring och revisor.
      </p>
      <div class="mt-6 flex flex-col gap-3 sm:flex-row">
        <a href="#scan-upload" class="btn-primary justify-center">Scanna kvitto</a>
        <a href="{% url 'dashboard' %}" class="btn-secondary justify-center">Visa underlag</a>
      </div>
    </div>

    <div class="hero-panel" aria-hidden="true">
      <div class="mini-receipt">
        <div class="mini-receipt-tree">♲</div>
        <div class="mini-line w-3/4"></div>
        <div class="mini-line w-1/2"></div>
        <div class="mini-line w-2/3"></div>
      </div>
      <div class="hero-stat-card">
        <p>Redo för export</p>
        <strong>Excel</strong>
      </div>
    </div>
  </header>

  {% include "receipts/partials/upload_form.html" %}
</section>
{% endblock %}
'@ -Encoding utf8

Set-Content templates\receipts\partials\upload_form.html @'
<section id="scan-upload" class="card" data-receipt-upload>
  <div class="section-header">
    <div>
      <p class="eyebrow">Steg 1</p>
      <h2 class="section-title">Ladda upp kvitto</h2>
      <p class="section-text">Välj en bild från mobilen eller datorn. JPG, PNG och WEBP stöds.</p>
    </div>
    {% if gates.is_pilot %}
      {% include "partials/pilot_badge.html" %}
    {% endif %}
  </div>

  <form
    hx-post="/api/receipts/scan"
    hx-encoding="multipart/form-data"
    hx-target="#scan-result"
    hx-swap="innerHTML"
    hx-indicator="#scan-loading-indicator"
    class="mt-6 space-y-4"
  >
    {% csrf_token %}

    <input
      id="receipt-image-input"
      name="image"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      capture="environment"
      class="sr-only"
      data-receipt-file
      required
    >

    <div class="grid gap-3 sm:grid-cols-2">
      <button type="button" class="btn-primary justify-center" data-upload-trigger>
        Scanna med kamera
      </button>
      <button type="button" class="btn-secondary justify-center" data-upload-trigger>
        Välj bild
      </button>
    </div>

    <div class="upload-preview" data-upload-empty>
      <p class="font-semibold text-forest-950">Ingen bild vald ännu</p>
      <p class="mt-1 text-sm text-stone-600">När du väljer en bild visas förhandsvisningen här.</p>
    </div>

    <figure class="hidden overflow-hidden rounded-3xl border border-stone-200 bg-white" data-upload-preview-wrap>
      <img src="" alt="Förhandsvisning av kvitto" class="max-h-[32rem] w-full object-contain" data-receipt-preview>
      <figcaption class="border-t border-stone-200 px-4 py-3 text-sm text-stone-600" data-file-name></figcaption>
    </figure>

    <button type="submit" class="btn-primary w-full justify-center">
      Starta skanning
    </button>

    <div id="scan-loading-indicator" class="htmx-indicator items-center gap-2 text-sm font-semibold text-emerald-900">
      <span class="h-4 w-4 animate-spin rounded-full border-2 border-emerald-900 border-t-transparent"></span>
      <span>Analyserar kvittot...</span>
    </div>
  </form>

  <section id="scan-result" class="mt-6"></section>
</section>
'@ -Encoding utf8

Set-Content templates\partials\pilot_badge.html @'
<span class="status-pill">Pilotåtkomst</span>
'@ -Encoding utf8

Set-Content templates\partials\premium_badge.html @'
<span class="status-pill">Premium</span>
'@ -Encoding utf8

Set-Content templates\partials\premium_cta.html @'
<div class="premium-box">
  <p class="font-semibold text-forest-950">Aktivera Premium</p>
  <p class="mt-1 text-sm text-stone-600">Lås upp export, körjournal och årsunderlag.</p>
  <div class="mt-4 grid gap-2 sm:grid-cols-2">
    <a href="{% url 'start_checkout' %}?plan=yearly" class="btn-primary justify-center">499 kr/år</a>
    <a href="{% url 'start_checkout' %}?plan=monthly" class="btn-secondary justify-center">49 kr/mån</a>
  </div>
</div>
'@ -Encoding utf8