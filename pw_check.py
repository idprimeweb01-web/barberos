import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 480, "height": 850})
        await page.goto("http://127.0.0.1:5000/login")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="screenshot_login.png", full_page=True)
        print("Screenshot salvo: screenshot_login.png")
        
        # Capture page title and key elements
        title = await page.title()
        print(f"Title: {title}")
        
        email_visible = await page.is_visible("#email")
        senha_visible = await page.is_visible("#senha")
        btn_visible = await page.is_visible("#btn-entrar")
        print(f"Campo email visivel: {email_visible}")
        print(f"Campo senha visivel: {senha_visible}")
        print(f"Botao ENTRAR visivel: {btn_visible}")
        
        await browser.close()

asyncio.run(main())
