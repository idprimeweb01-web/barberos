import asyncio, json
from playwright.async_api import async_playwright

async def injetar_auth(ctx, email, senha):
    page = await ctx.new_page()
    await page.goto('http://127.0.0.1:5000/login')
    r = await page.evaluate(f'''async () => {{
        const res = await fetch('/auth/login', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body: JSON.stringify({{email: '{email}', senha: '{senha}'}})
        }});
        return res.json();
    }}''')
    token = r.get('token','')
    user  = json.dumps(r.get('usuario', {})).replace('"', '\\"').replace("'", "\\'")
    await page.evaluate(f"localStorage.setItem('barberos_token', '{token}')")
    await page.evaluate(f'''localStorage.setItem('barberos_user', JSON.stringify({json.dumps(r['usuario'])}))''')
    await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 480, "height": 860})

        # Reseta agendamento para 'agendado' antes do teste
        import sys, os; sys.path.insert(0, os.getcwd())
        from app import create_app, db
        from app.models import Agendamento, Atendimento, AtendimentoItem, Pagamento
        app_inst = create_app()
        with app_inst.app_context():
            ag = Agendamento.query.filter_by(id=6).first()
            ag.status = 'agendado'
            # Remove atendimentos existentes
            for at in Atendimento.query.filter_by(agendamento_id=6).all():
                AtendimentoItem.query.filter_by(atendimento_id=at.id).delete()
                Pagamento.query.filter_by(atendimento_id=at.id).delete()
                db.session.delete(at)
            db.session.commit()
        print("Reset OK")

        # Autentica
        await injetar_auth(ctx, 'barbeiro@barbearia.com', 'senha123')

        # 1. Tela de agenda
        pg = await ctx.new_page()
        await pg.goto('http://127.0.0.1:5000/barbeiro/agenda')
        await pg.wait_for_load_state('networkidle')
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path='screenshot_b_agenda.png', full_page=False)
        print("Screenshot agenda OK")

        # 2. Clica em "Iniciar atendimento"
        btn = await pg.wait_for_selector('button.btn-iniciar', timeout=5000)
        await btn.click()
        await pg.wait_for_url('**/caixa/**', timeout=8000)
        await pg.wait_for_load_state('networkidle')
        await pg.wait_for_timeout(2000)
        await pg.screenshot(path='screenshot_b_caixa.png', full_page=False)
        print("Screenshot caixa OK")

        # 3. Abre modal de produto
        await pg.click('button.cx-add-btn')
        await pg.wait_for_selector('#modalProduto.visible', timeout=3000)
        await pg.wait_for_timeout(1000)
        await pg.screenshot(path='screenshot_b_modal_produto.png', full_page=False)
        print("Screenshot modal produto OK")

        # 4. Adiciona produto (se disponivel)
        btn_add = pg.locator('.prod-item-btn').first
        count = await btn_add.count()
        if count:
            await btn_add.click()
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path='screenshot_b_caixa_produto.png', full_page=False)
            print("Screenshot caixa com produto OK")
        else:
            print("Sem produtos disponiveis")

        # 5. Seleciona PIX
        await pg.click('button[data-forma="pix"]')
        await pg.wait_for_timeout(400)
        await pg.screenshot(path='screenshot_b_pagto.png', full_page=False)
        print("Screenshot pagto OK")

        # 6. Confirma pagamento
        await pg.click('#btnConfirmar')
        await pg.wait_for_url('**/barbeiro/agenda', timeout=6000)
        await pg.wait_for_load_state('networkidle')
        await pg.wait_for_timeout(2000)
        await pg.screenshot(path='screenshot_b_agenda_final.png', full_page=False)
        print("Screenshot agenda final OK")

        await browser.close()

asyncio.run(main())
