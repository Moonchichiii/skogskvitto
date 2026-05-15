(() => {
        document.addEventListener('DOMContentLoaded', () => {
            const banner = document.querySelector('[data-cookie-banner]');
            const btn = document.querySelector('[data-cookie-accept]');
            if (!banner || !btn || localStorage.getItem('cookie_consent')) return;
            banner.classList.remove('hidden');
            btn.onclick = () => { localStorage.setItem('cookie_consent', 'true'); banner.classList.add('hidden'); };
        });
    })();