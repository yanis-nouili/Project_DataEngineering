from playwright.sync_api import sync_playwright, TimeoutError as PwTimeoutError

def fetch_rendered_html(url: str, wait_text: str | None = None, timeout_ms: int = 45000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )

        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        # Tentative de clic cookie (si présent)
        for label in ["Tout accepter", "Accepter", "J'accepte", "OK"]:
            try:
                page.locator(f"button:has-text('{label}')").first.click(timeout=1500)
                break
            except Exception:
                pass

        # Laisse le JS charger
        page.wait_for_timeout(3000)

        # Certains sites chargent le tableau après un délai / lazy loading
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(2000)

        if wait_text:
            try:
                page.wait_for_selector(f"text={wait_text}", timeout=timeout_ms)
            except PwTimeoutError:
                # On renvoie quand même le HTML pour debug
                pass

        html = page.content()
        browser.close()
        return html
