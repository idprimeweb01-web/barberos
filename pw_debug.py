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

        async with page.expect_response("**/auth/login") as resp_info:
            await page.click("#btn-entrar")
        resp = await resp_info.value
        body = await resp.json()
        print("API response:", body)
        
        await page.wait_for_timeout(1500)
        display = await page.evaluate("document.getElementById('msg-erro').style.display")
        html = await page.evaluate("document.getElementById('msg-erro').innerHTML")
        txt = await page.evaluate("document.getElementById('msg-erro-texto').textContent")
        print("Display:", display)
        print("Text:", txt)
        print("HTML:", html[:200])
        await page.screenshot(path="screenshot_erro.png", full_page=True)
        await browser.close()

asyncio.run(main())
