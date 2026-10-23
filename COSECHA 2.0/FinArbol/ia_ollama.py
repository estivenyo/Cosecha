"""Cliente mínimo de Ollama (solo librería estándar): habla con el servidor local por HTTP.

Ollama escucha por defecto en http://localhost:11434. Este módulo no sabe nada de finanzas:
solo envía mensajes al modelo y devuelve la respuesta (completa, en JSON o por pedazos).
"""
import json
import os
import urllib.error
import urllib.request

URL_OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not URL_OLLAMA.startswith("http"):
    URL_OLLAMA = "http://" + URL_OLLAMA
MODELO = os.environ.get("COSECHA_MODELO", "llama3.2:1b")


class ErrorOllama(Exception):
    """Ollama no responde, no tiene el modelo o devolvió algo inválido."""


class ClienteOllama:
    def __init__(self, url=URL_OLLAMA, modelo=MODELO, tiempo_espera=120):
        self.url, self.modelo, self.tiempo_espera = url, modelo, tiempo_espera

    # ------------------------------------------------------------------
    def _pedir(self, ruta, carga=None, tiempo=None):
        datos = json.dumps(carga).encode("utf-8") if carga is not None else None
        peticion = urllib.request.Request(self.url + ruta, data=datos,
                                          headers={"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(peticion, timeout=tiempo or self.tiempo_espera)
        except urllib.error.HTTPError as error:
            cuerpo = error.read().decode("utf-8", "ignore")
            if error.code == 404:
                raise ErrorOllama(f"El modelo «{self.modelo}» no está instalado. "
                                  f"Ejecuta en una terminal:  ollama pull {self.modelo}") from error
            raise ErrorOllama(f"Ollama respondió con error {error.code}: {cuerpo[:200]}") from error
        except (urllib.error.URLError, OSError) as error:
            raise ErrorOllama("No puedo conectarme con Ollama. Abre la aplicación de Ollama "
                              "(o ejecuta «ollama serve») y vuelve a intentarlo.") from error

    def disponible(self):
        """True si el servidor responde y el modelo está instalado. Si no, lanza ErrorOllama."""
        with self._pedir("/api/tags", tiempo=4) as respuesta:
            modelos = [m.get("name", "") for m in json.load(respuesta).get("models", [])]
        base = self.modelo.split(":")[0]
        if not any(m == self.modelo or (":" not in self.modelo and m.split(":")[0] == base) for m in modelos):
            raise ErrorOllama(f"Ollama está activo, pero falta el modelo «{self.modelo}». "
                              f"Ejecuta en una terminal:  ollama pull {self.modelo}")
        return True

    # ------------------------------------------------------------------
    def _carga(self, mensajes, stream, formato=None, max_tokens=None, temperatura=0.3):
        carga = {"model": self.modelo, "messages": mensajes, "stream": stream,
                 "options": {"temperature": temperatura, "num_ctx": 8192}}
        if max_tokens:
            carga["options"]["num_predict"] = max_tokens
        if formato is not None:
            carga["format"] = formato
        return carga

    def json(self, mensajes, esquema):
        """Respuesta estructurada: el modelo debe devolver un JSON que cumpla el esquema."""
        try:
            respuesta = self._pedir("/api/chat", self._carga(mensajes, False, esquema, 120, 0.1))
        except ErrorOllama as error:
            if "error 400" not in str(error):
                raise
            # Versiones antiguas de Ollama no aceptan un esquema: se pide JSON "libre".
            respuesta = self._pedir("/api/chat", self._carga(mensajes, False, "json", 120, 0.1))
        with respuesta:
            texto = json.load(respuesta).get("message", {}).get("content", "")
        try:
            return json.loads(texto)
        except ValueError as error:
            raise ErrorOllama(f"La IA no devolvió un JSON válido: {texto[:120]!r}") from error

    def texto_en_vivo(self, mensajes, al_recibir, max_tokens=320, cancelado=lambda: False):
        """Genera texto y llama a al_recibir(pedazo) a medida que el modelo lo escribe."""
        completo = []
        with self._pedir("/api/chat", self._carga(mensajes, True, None, max_tokens, 0.5)) as respuesta:
            for linea in respuesta:
                if cancelado():
                    break
                if not linea.strip():
                    continue
                trozo = json.loads(linea)
                if "error" in trozo:
                    raise ErrorOllama(trozo["error"])
                pedazo = trozo.get("message", {}).get("content", "")
                if pedazo:
                    completo.append(pedazo)
                    al_recibir(pedazo)
                if trozo.get("done"):
                    break
        return "".join(completo)
