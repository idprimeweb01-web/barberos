import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ── 1. Login admin → /admin/dashboard ─────────────────────
        page = await browser.new_page(viewport={"width": 480, "height": 850})
        await page.goto("http://127.0.0.1:5000/login")
        await page.wait_for_load_state("networkidle")
        await page.fill("#email", "caio@barbearia.com")
        await page.fill("#senha", "senha123")
        await page.click("#btn-entrar")
        await page.wait_for_url("**/admin/dashboard", timeout=5000)
        url_admin = page.url
        await page.screenshot(path="screenshot_admin.png", full_page=True)
        print(f"1. Admin redirect: {url_admin}")
        await page.close()

        # ── 2. Login barbeiro → /barbeiro/agenda ──────────────────
        page2 = await browser.new_page(viewport={"width": 480, "height": 850})
        await page2.goto("http://127.0.0.1:5000/login")
        await page2.wait_for_load_state("networkidle")
        await page2.fill("#email", "joao@barbearia.com")
        await page2.fill("#senha", "senha123")
        await page2.click("#btn-entrar")
        await page2.wait_for_url("**/barbeiro/agenda", timeout=5000)
        url_barb = page2.url
        await page2.screenshot(path="screenshot_barbeiro.png", full_page=True)
        print(f"2. Barbeiro redirect: {url_barb}")
        await page2.close()

        # ── 3. Senha errada → mensagem de erro ────────────────────
        page3 = await browser.new_page(viewport={"width": 480, "height": 850})
        await page3.goto("http://127.0.0.1:5000/login")
        await page3.wait_for_load_state("networkidle")
        await page3.fill("#email", "caio@barbearia.com")
        await page3.fill("#senha", "senhaerrada")
        await page3.click("#btn-entrar")
        await page3.wait_for_selector("#msg-erro", state="visible", timeout=5000)
        erro_txt = await page3.inner_text("#msg-erro-texto")
        await page3.screenshot(path="screenshot_erro.png", full_page=True)
        print(f"3. Senha errada → erro: '{erro_txt}'")
        await page3.close()

        # ── 4. Toggle senha ───────────────────────────────────────
        page4 = await browser.new_page(viewport={"width": 480, "height": 850})
        await page4.goto("http://127.0.0.1:5000/login")
        await page4.wait_for_load_state("networkidle")
        tipo_antes = await page4.get_attribute("#senha", "type")
        await page4.click("#toggle-senha")
        tipo_depois = await page4.get_attribute("#senha", "type")
        print(f"4. Toggle senha: {tipo_antes} → {tipo_depois}")
        await page4.close()

        await browser.close()

asyncio.run(main())
