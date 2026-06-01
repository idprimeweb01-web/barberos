import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, request, jsonify
from app import db
from app.models import Barbearia, Barbeiro, Produto, Servico, Cliente
from app.utils import get_barbearia_atual
from app.routes.auth import gestor_required, barbeiro_required, super_admin_required

upload = Blueprint('upload', __name__)

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
)


def _erro(msg, code=400):
    return jsonify({'erro': msg}), code


admin_required = gestor_required

_TIPOS_PERMITIDOS = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
_MAX_BYTES        = 5 * 1024 * 1024  # 5 MB


def _validar(arquivo):
    if arquivo.mimetype not in _TIPOS_PERMITIDOS:
        return 'Tipo não permitido. Use JPG, PNG ou WebP.'
    arquivo.seek(0, 2)
    tam = arquivo.tell()
    arquivo.seek(0)
    if tam > _MAX_BYTES:
        return 'Arquivo muito grande. Máximo 5 MB.'
    return None


def _fazer_upload(arquivo, pasta, public_id):
    try:
        resultado = cloudinary.uploader.upload(
            arquivo.stream,
            folder=pasta,
            public_id=public_id,
            overwrite=True,
            unique_filename=False,
            invalidate=True,
            resource_type='image',
        )
    except Exception as exc:
        raise RuntimeError(f'Cloudinary: {exc}') from exc
    url = resultado.get('secure_url')
    if not url:
        raise RuntimeError('Cloudinary não retornou a URL da imagem.')
    return url


def _get_arquivo():
    if 'arquivo' not in request.files:
        return None, _erro('Campo "arquivo" é obrigatório.')
    arq = request.files['arquivo']
    if not arq.filename:
        return None, _erro('Nenhum arquivo enviado.')
    err = _validar(arq)
    if err:
        return None, _erro(err)
    return arq, None


# ── Barbearia — logo ───────────────────────────────────────────────────────────

@upload.post('/upload/barbearia/<int:barbearia_id>/logo')
@super_admin_required
def upload_logo_barbearia(barbearia_id):
    barbearia = db.session.get(Barbearia, barbearia_id)
    if not barbearia:
        return _erro('Barbearia não encontrada.', 404)
    arq, err = _get_arquivo()
    if err: return err
    try:
        url = _fazer_upload(arq, 'barberos/barbearias', f'barbearia_{barbearia_id}')
    except RuntimeError as exc:
        return _erro(str(exc), 502)
    barbearia.logo_url = url
    db.session.commit()
    return jsonify({'mensagem': 'Logo atualizada.', 'url': url})


# ── Barbeiro — foto ────────────────────────────────────────────────────────────

@upload.post('/upload/barbeiro/<int:barbeiro_id>/foto')
@admin_required
def upload_foto_barbeiro(barbeiro_id):
    barbearia_id = get_barbearia_atual()
    barbeiro = Barbeiro.query.filter_by(id=barbeiro_id, barbearia_id=barbearia_id).first()
    if not barbeiro:
        return _erro('Barbeiro não encontrado.', 404)
    arq, err = _get_arquivo()
    if err: return err
    try:
        url = _fazer_upload(arq, 'barberos/barbeiros', f'barbeiro_{barbeiro_id}')
    except RuntimeError as exc:
        return _erro(str(exc), 502)
    barbeiro.foto = url
    db.session.commit()
    return jsonify({'mensagem': 'Foto atualizada.', 'url': url})


# ── Serviço — foto ─────────────────────────────────────────────────────────────

@upload.post('/upload/servico/<int:servico_id>/foto')
@admin_required
def upload_foto_servico(servico_id):
    barbearia_id = get_barbearia_atual()
    servico = Servico.query.filter_by(id=servico_id, barbearia_id=barbearia_id).first()
    if not servico:
        return _erro('Serviço não encontrado.', 404)
    arq, err = _get_arquivo()
    if err: return err
    try:
        url = _fazer_upload(arq, 'barberos/servicos', f'servico_{servico_id}')
    except RuntimeError as exc:
        return _erro(str(exc), 502)
    servico.foto = url
    db.session.commit()
    return jsonify({'mensagem': 'Foto atualizada.', 'url': url})


# ── Produto — foto ─────────────────────────────────────────────────────────────

@upload.post('/upload/produto/<int:produto_id>/foto')
@admin_required
def upload_foto_produto(produto_id):
    barbearia_id = get_barbearia_atual()
    produto = Produto.query.filter_by(id=produto_id, barbearia_id=barbearia_id).first()
    if not produto:
        return _erro('Produto não encontrado.', 404)
    arq, err = _get_arquivo()
    if err: return err
    try:
        url = _fazer_upload(arq, 'barberos/produtos', f'produto_{produto_id}')
    except RuntimeError as exc:
        return _erro(str(exc), 502)
    produto.foto = url
    db.session.commit()
    return jsonify({'mensagem': 'Foto atualizada.', 'url': url})


# ── Cliente — foto ─────────────────────────────────────────────────────────────

@upload.post('/upload/cliente/<int:cliente_id>/foto')
@barbeiro_required
def upload_foto_cliente(cliente_id):
    barbearia_id = get_barbearia_atual()
    cliente = Cliente.query.filter_by(id=cliente_id, barbearia_id=barbearia_id).first()
    if not cliente:
        return _erro('Cliente não encontrado.', 404)
    arq, err = _get_arquivo()
    if err: return err
    try:
        url = _fazer_upload(arq, 'barberos/clientes', f'cliente_{cliente_id}')
    except RuntimeError as exc:
        return _erro(str(exc), 502)
    cliente.foto = url
    db.session.commit()
    return jsonify({'mensagem': 'Foto atualizada.', 'url': url})
