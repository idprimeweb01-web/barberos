import asyncio, json
from playwright.async_api import async_playwright

PAGES = [
    ('dashboard',    '/gestor/dashboard'),
    ('barbeiros',    '/gestor/barbeiros'),
    ('servicos',     '/gestor/servicos'),
    ('produtos',     '/gestor/produtos'),
    ('agenda',       '/gestor/agenda'),
    ('esqueci_senha','/gestor/esqueci-senha'),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Autentica e salva estado
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()
        
        # Injeta token via localStorage
        await page.goto('http://127.0.0.1:5000/login')
        r = await page.evaluate('''async () => {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({email:'gestor@caio.com', senha:'senha123'})
            });
            return res.json();
        }''')
        await page.evaluate(f'''() => {{
            localStorage.setItem('barberos_token', '{r["token"]}');
            localStorage.setItem('barberos_user', JSON.stringify({json.dumps(r["usuario"])}));
        }}''')
        
        for nome, path in PAGES:
            pg = await ctx.new_page()
            await pg.goto(f'http://127.0.0.1:5000{path}')
            await pg.wait_for_load_state('networkidle')
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=f'screenshot_{nome}.png', full_page=False)
            print(f'OK  {nome}')
            await pg.close()
        
        await browser.close()

asyncio.run(main())
