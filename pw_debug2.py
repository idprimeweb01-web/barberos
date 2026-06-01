import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 480, "height": 850})
        await page.goto("http://127.0.0.1:5000/login")
        await page.wait_for_load_state("networkidle")
        await page.fill("#email", "caio@barbearia.com")
        await page.fill("#senha", "senhaerrada")
        await page.click("#btn-entrar")
        await page.wait_for_timeout(2000)
        display = await page.evaluate("document.getElementById('msg-erro').style.display")
        txt = await page.evaluate("document.getElementById('msg-erro-texto').textContent")
        print("Display:", repr(display))
        print("Texto:", repr(txt))
        await page.screenshot(path="screenshot_erro.png", full_page=True)
        await browser.close()

asyncio.run(main())
