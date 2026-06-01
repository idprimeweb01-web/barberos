import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Senha errada
        page3 = await browser.new_page(viewport={"width": 480, "height": 850})
        await page3.goto("http://127.0.0.1:5000/login")
        await page3.wait_for_load_state("networkidle")
        await page3.fill("#email", "caio@barbearia.com")
        await page3.fill("#senha", "senhaerrada")

        async with page3.expect_response("**/auth/login") as resp_info:
            await page3.click("#btn-entrar")
        await resp_info.value

        await page3.wait_for_function("document.getElementById('msg-erro').style.display !== 'none'", timeout=5000)
        erro_txt = await page3.inner_text("#msg-erro-texto")
        await page3.screenshot(path="screenshot_erro.png", full_page=True)
        print("3. Erro:", erro_txt)
        await page3.close()

        # Toggle senha
        page4 = await browser.new_page(viewport={"width": 480, "height": 850})
        await page4.goto("http://127.0.0.1:5000/login")
        await page4.wait_for_load_state("networkidle")
        tipo_antes = await page4.get_attribute("#senha", "type")
        await page4.click("#toggle-senha")
        tipo_depois = await page4.get_attribute("#senha", "type")
        print("4. Toggle:", tipo_antes, "->", tipo_depois)
        await page4.close()

        await browser.close()

asyncio.run(main())
