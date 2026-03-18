from playwright.async_api import Playwright
from playwright_stealth import Stealth
from config import Config

class BrowserFactory:
    @staticmethod
    async def configurar_navegador(playwright: Playwright):
        browser = await playwright.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent=Config.USER_AGENT,
            viewport={'width': 1280, 'height': 720},
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()
        
        # Script para evitar detecção
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return browser, page