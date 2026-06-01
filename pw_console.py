import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 480, "height": 850})
        
        errors = []
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
        
        reqs = []
        page.on("response", lambda r: reqs.append(f"{r.status} {r.url}"))
        
        await page.goto("http://127.0.0.1:5000/login")
        await page.wait_for_load_state("networkidle")
        await page.fill("#email", "caio@barbearia.com")
        await page.fill("#senha", "senhaerrada")
        await page.click("#btn-entrar")
        await page.wait_for_timeout(3000)
        
        print("Console/errors:")
        for e in errors: print(" ", e)
        print("Responses:")
        for r in reqs: print(" ", r)
        
        display = await page.evaluate("document.getElementById('msg-erro').style.display")
        print("Display inline:", repr(display))
        await browser.close()

asyncio.run(main())
