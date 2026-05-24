"""Adaptador Playwright para o RenderProtocol — produção."""

from __future__ import annotations


class PlaywrightRender:
    """Renderiza HTML para PNG usando Chromium headless via Playwright.

    Requer `playwright>=1.40` instalado e `playwright install chromium`
    rodado uma vez. Em ambientes sem chromium, vai levantar erro do
    próprio Playwright na primeira chamada — o `.env.example` documenta.
    """

    def render_png(self, html: str, width: int, height: int) -> bytes:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(html, wait_until="load")
            png: bytes = page.screenshot(full_page=False)
            browser.close()
            return png
