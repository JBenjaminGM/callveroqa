"""
Tests del almacenamiento de grabaciones.

El disco de Render es **efímero**: cada despliegue se lleva los audios, y ya
pasó en producción (una llamada ya subida dejó de poder reproducirse). Por eso
S3 no es un extra, es el modo de producción. Estos tests cubren ese camino sin
tocar AWS, que es justamente lo que nadie prueba hasta que falla en vivo.
"""

import pytest

from app.config import settings
from app.services import storage_service
from app.services.storage_service import (
    LocalStorageProvider,
    S3StorageProvider,
    get_storage_provider,
)


class _ClienteS3Falso:
    """Lo mínimo del cliente de boto3 que usa el proveedor."""

    def __init__(self):
        self.objetos: dict[tuple[str, str], bytes] = {}

    def put_object(self, Bucket, Key, Body):  # noqa: N803 (firma de boto3)
        self.objetos[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):  # noqa: N803
        contenido = self.objetos[(Bucket, Key)]
        return {"Body": type("_Body", (), {"read": lambda self: contenido})()}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objetos.pop((Bucket, Key), None)


@pytest.fixture
def s3(monkeypatch):
    """Proveedor S3 con un cliente falso y la configuración completa."""
    cliente = _ClienteS3Falso()
    monkeypatch.setattr(settings, "aws_s3_bucket", "grabaciones-banco", raising=False)
    monkeypatch.setattr(settings, "aws_access_key_id", "clave", raising=False)
    monkeypatch.setattr(settings, "aws_secret_access_key", "secreto", raising=False)

    import boto3

    monkeypatch.setattr(boto3, "client", lambda *a, **k: cliente)
    return S3StorageProvider(), cliente


# ===============================================================
# Ciclo completo en S3
# ===============================================================
def test_guardar_leer_y_borrar_en_s3(s3):
    proveedor, cliente = s3

    url = proveedor.save(b"audio de la llamada", "llamada.mp3")
    assert url.startswith("s3://grabaciones-banco/audios/")
    assert url.endswith(".mp3")
    assert proveedor.load(url) == b"audio de la llamada"

    proveedor.delete(url)
    assert cliente.objetos == {}


def test_cada_audio_tiene_su_propia_clave(s3):
    proveedor, _ = s3
    primera = proveedor.save(b"a", "misma.mp3")
    segunda = proveedor.save(b"b", "misma.mp3")
    assert primera != segunda
    assert proveedor.load(primera) == b"a"
    assert proveedor.load(segunda) == b"b"


def test_una_ruta_de_otro_bucket_se_rechaza(s3):
    proveedor, _ = s3
    with pytest.raises(ValueError, match="no pertenece al bucket"):
        proveedor.load("s3://otro-bucket/audios/abc.mp3")


# ===============================================================
# Configuración
# ===============================================================
def test_s3_sin_configurar_falla_con_un_mensaje_claro(monkeypatch):
    monkeypatch.setattr(settings, "aws_s3_bucket", "", raising=False)
    monkeypatch.setattr(settings, "aws_access_key_id", "", raising=False)
    monkeypatch.setattr(settings, "aws_secret_access_key", "", raising=False)

    with pytest.raises(ValueError) as exc:
        S3StorageProvider()
    mensaje = str(exc.value)
    assert "AWS_S3_BUCKET" in mensaje and "STORAGE_PROVIDER=local" in mensaje


def test_la_factory_respeta_la_configuracion(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_provider", "local", raising=False)
    monkeypatch.setattr(settings, "storage_path", str(tmp_path), raising=False)
    assert isinstance(get_storage_provider(), LocalStorageProvider)

    monkeypatch.setattr(settings, "storage_provider", "vhs", raising=False)
    with pytest.raises(ValueError, match="desconocido"):
        get_storage_provider()


# ===============================================================
# Almacenamiento local
# ===============================================================
def test_local_guarda_lee_y_borra(tmp_path):
    proveedor = LocalStorageProvider(str(tmp_path))
    url = proveedor.save(b"audio", "llamada.wav")

    assert proveedor.load(url) == b"audio"
    proveedor.delete(url)
    assert list(tmp_path.iterdir()) == []
    # Borrar algo que ya no está no debe reventar: la purga de retención lo hace.
    proveedor.delete(url)
