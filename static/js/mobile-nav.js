(() => {
        document.addEventListener('DOMContentLoaded', () => {
            const btn = document.querySelector('[data-mobile-menu-button]');
            const panel = document.querySelector('[data-mobile-menu-panel]');
            if (btn && panel) btn.onclick = () => panel.classList.toggle('hidden');
        });
    })();