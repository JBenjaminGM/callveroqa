"""
Servicio de almacenamiento de audios.

Usa un patrón factory para soportar dos backends, seleccionables por la
variable STORAGE_PROVIDER:
- local: guarda los archivos en disco (en Render, /data/audios; OJO: sin disco
         persistente declarado es EFÍMERO — se pierde en cada redeploy).
- s3:    guarda los archivos en un bucket de Amazon S3 (persistente, para producción real).
"""

import os
import uuid
from abc import ABC, abstractmethod

from app.config import settings


class StorageProvider(ABC):
    """Interfaz común de los proveedores de almacenamiento."""

    @abstractmethod
    def save(self, content: bytes, filename: str) -> str:
        """Guarda el contenido y devuelve una URL/identificador para recuperarlo."""

    @abstractmethod
    def load(self, url: str) -> bytes:
        """Devuelve el contenido binario asociado a una URL/identificador."""

    @abstractmethod
    def delete(self, url: str) -> None:
        """Elimina el archivo asociado a una URL/identificador."""


class LocalStorageProvider(StorageProvider):
    """Almacenamiento en el sistema de archivos local."""

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, content: bytes, filename: str) -> str:
        # Se antepone un UUID para evitar colisiones de nombres.
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(self.base_path, unique_name)
        with open(path, "wb") as f:
            f.write(content)
        # La URL local es simplemente la ruta del archivo.
        return path

    def load(self, url: str) -> bytes:
        with open(url, "rb") as f:
            return f.read()

    def delete(self, url: str) -> None:
        if os.path.exists(url):
            os.remove(url)


class S3StorageProvider(StorageProvider):
    """Almacenamiento en Amazon S3."""

    def __init__(self) -> None:
        import boto3  # import perezoso: solo se necesita si se usa S3

        # Se comprueba al construir y no al primer audio: si falta la
        # configuración, es mejor que la API no arranque a que la primera
        # llamada del cliente se pierda con un error del SDK de AWS.
        faltan = [
            nombre
            for nombre, valor in (
                ("AWS_S3_BUCKET", settings.aws_s3_bucket),
                ("AWS_ACCESS_KEY_ID", settings.aws_access_key_id),
                ("AWS_SECRET_ACCESS_KEY", settings.aws_secret_access_key),
            )
            if not valor
        ]
        if faltan:
            raise ValueError(
                "STORAGE_PROVIDER=s3 pero falta: "
                + ", ".join(faltan)
                + ". Complétalo o vuelve a STORAGE_PROVIDER=local."
            )

        self.bucket = settings.aws_s3_bucket
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )

    def save(self, content: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1]
        key = f"audios/{uuid.uuid4().hex}{ext}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return f"s3://{self.bucket}/{key}"

    def _parse_key(self, url: str) -> str:
        """
        Extrae la 'key' de S3 a partir de una URL `s3://bucket/key`.

        Si la URL apunta a otro bucket se rechaza en vez de inventar una key:
        pasa al restaurar una copia de seguridad de otro entorno, y el fallo
        silencioso sería leer (o borrar) el objeto equivocado.
        """
        prefijo = f"s3://{self.bucket}/"
        if not url.startswith(prefijo):
            raise ValueError(
                f"La ruta {url!r} no pertenece al bucket configurado ({self.bucket})."
            )
        return url[len(prefijo):]

    def load(self, url: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=self._parse_key(url))
        return obj["Body"].read()

    def delete(self, url: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._parse_key(url))


def get_storage_provider() -> StorageProvider:
    """Factory: devuelve el proveedor de almacenamiento según la configuración."""
    if settings.storage_provider == "s3":
        return S3StorageProvider()
    if settings.storage_provider == "local":
        return LocalStorageProvider(settings.storage_path)
    raise ValueError(f"Proveedor de almacenamiento desconocido: {settings.storage_provider}")
