import asyncio, json
from playwright.async_api import async_playwright

async def injetar(ctx, email, senha):
    pg = await ctx.new_page()
    await pg.goto('http://127.0.0.1:5000/login')
    r = await pg.evaluate(f"""async () => {{
        const res = await fetch('/auth/login', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify({{email:'{email}', senha:'{senha}'}})
        }});
        return res.json();
    }}""")
    await pg.evaluate(f"""() => {{
        localStorage.setItem('barberos_token', '{r["token"]}');
        localStorage.setItem('barberos_user', JSON.stringify({json.dumps(r["usuario"])}));
    }}""")
    await pg.close()

async def shot(ctx, url, nome, wait=2000):
    pg = await ctx.new_page()
    await pg.goto(url)
    await pg.wait_for_load_state('networkidle')
    await pg.wait_for_timeout(wait)
    await pg.screenshot(path=f'screenshot_{nome}.png')
    print(f'OK  {nome}')
    await pg.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Super admin (desktop 1280px)
        ctx_sa = await browser.new_context(viewport={"width": 1280, "height": 800})
        await injetar(ctx_sa, 'adm@barbearia.com', 'senha123')
        await shot(ctx_sa, 'http://127.0.0.1:5000/super/dashboard',  'super_dashboard')
        await shot(ctx_sa, 'http://127.0.0.1:5000/super/barbearias', 'super_barbearias')
        await shot(ctx_sa, 'http://127.0.0.1:5000/super/gestores',   'super_gestores')

        # Público (mobile 480px)
        ctx_pub = await browser.new_context(viewport={"width": 480, "height": 860})
        await shot(ctx_pub, 'http://127.0.0.1:5000/b/caio/', 'pub_index', wait=2500)
        await shot(ctx_pub, 'http://127.0.0.1:5000/b/caio/agendar', 'pub_agendar', wait=2000)

        # Booking flow passo a passo
        ctx_ag = await browser.new_context(viewport={"width": 480, "height": 860})
        pg = await ctx_ag.new_page()
        await pg.goto('http://127.0.0.1:5000/b/caio/agendar')
        await pg.wait_for_load_state('networkidle')
        await pg.wait_for_timeout(2000)
        await pg.click('.barb-card')
        await pg.wait_for_timeout(300)
        await pg.click('#btnNext')
        await pg.wait_for_timeout(1800)
        await pg.screenshot(path='screenshot_pub_step2.png')
        print('OK  pub_step2')
        await pg.click('.sv-card')
        await pg.wait_for_timeout(300)
        await pg.click('#btnNext')
        await pg.wait_for_timeout(1000)
        await pg.screenshot(path='screenshot_pub_step3.png')
        print('OK  pub_step3')
        await pg.close()

        await browser.close()

asyncio.run(main())
