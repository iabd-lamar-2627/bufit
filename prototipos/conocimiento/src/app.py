"""Conocimiento · RAG. Indexa los .md de documentos/ y busca los trozos más parecidos a una pregunta.

- GET  /salud       cuántos documentos y trozos hay indexados
- POST /buscar      {"texto": "...", "k": 3} → los k trozos más parecidos, con fuente y puntuación
- POST /reindexar   vuelve a leer los .md (después de editarlos); ?completo=true lo rehace todo

Los embeddings los calcula el contenedor de Ollama con un modelo multilingüe (bge-m3).
Los vectores se guardan con Chroma en /app/vectores y se reutilizan al arrancar: solo se
recalculan los documentos nuevos o cambiados (cada trozo guarda la huella de su documento).
"""
import hashlib
import logging
import os
import re
import time

import chromadb
from fastapi import FastAPI
from ollama import Client, ResponseError
from pydantic import BaseModel

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODELO_EMBEDDINGS = os.getenv("MODELO_EMBEDDINGS", "bge-m3")
DIR_DOCUMENTOS = os.getenv("DIR_DOCUMENTOS", "/app/documentos")
DIR_VECTORES = os.getenv("DIR_VECTORES", "/app/vectores")
TAM_TROZO = int(os.getenv("TAM_TROZO", "800"))   # caracteres aproximados por trozo
COLECCION = "documentos"

# Chroma intenta enviar estadísticas de uso y llena el log de errores inofensivos: los silenciamos
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

app = FastAPI(title="Bufit Conocimiento")
cliente = Client(host=OLLAMA_HOST)
chroma = chromadb.PersistentClient(path=DIR_VECTORES)


# ------------------------------------------------------------ documentos

def leer_documentos():
    """Devuelve (ruta relativa, texto) de cada .md, incluidas las subcarpetas."""
    for raiz, _, ficheros in os.walk(DIR_DOCUMENTOS):
        for fichero in sorted(ficheros):
            if fichero.endswith(".md"):
                ruta = os.path.join(raiz, fichero)
                with open(ruta, encoding="utf-8") as f:
                    yield os.path.relpath(ruta, DIR_DOCUMENTOS), f.read()


def titulo_de(texto: str, fuente: str) -> str:
    """El título es la primera línea que empieza por '# '. Si no hay, el nombre del fichero."""
    for linea in texto.splitlines():
        if linea.startswith("# "):
            return linea[2:].strip()
    return os.path.splitext(os.path.basename(fuente))[0]


def trocear(texto: str, titulo: str) -> list[str]:
    """Parte el documento en trozos de unos TAM_TROZO caracteres sin cortar ningún párrafo.

    Cada trozo lleva delante el título del documento, para que no pierda el contexto:
    un trozo que solo dice "Añade el arroz" no sirve si no se sabe que es de la paella.
    """
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    parrafos = [p for p in parrafos if p != f"# {titulo}"]     # el título ya va en cada trozo
    trozos, actual = [], ""
    for parrafo in parrafos:
        if actual and len(actual) + len(parrafo) > TAM_TROZO:
            trozos.append(actual)
            actual = ""
        actual = f"{actual}\n\n{parrafo}" if actual else parrafo
    if actual:
        trozos.append(actual)
    return [f"# {titulo}\n\n{t}" for t in trozos]


# ------------------------------------------------------------ embeddings e índice

def embeber(textos: list[str]) -> list[list[float]]:
    """Convierte cada texto en un vector que representa su significado."""
    return cliente.embed(model=MODELO_EMBEDDINGS, input=textos).embeddings


def coleccion():
    return chroma.get_or_create_collection(
        COLECCION,
        embedding_function=None,                 # los embeddings los calculamos nosotros con Ollama
        metadata={"hnsw:space": "cosine",         # similitud por coseno
                  "modelo": MODELO_EMBEDDINGS},   # con otro modelo, los vectores guardados no sirven
    )


def huella(texto: str) -> str:
    """Resumen del documento y de cómo se trocea: si cambia algo, cambia la huella."""
    return hashlib.sha1(f"{TAM_TROZO}\n{texto}".encode("utf-8")).hexdigest()


def borrar_indice():
    try:
        chroma.delete_collection(COLECCION)
    except Exception:
        pass


def indexar(completo: bool = False) -> dict:
    """Pone el índice al día. Solo calcula los embeddings de los documentos nuevos o cambiados,
    y quita los que ya no están. Con completo=True borra el índice y lo rehace entero."""
    inicio = time.time()
    if completo or coleccion().metadata.get("modelo") != MODELO_EMBEDDINGS:
        borrar_indice()
    col = coleccion()

    # Huella de cada documento ya indexado (la llevan todos sus trozos)
    guardadas = {m["fuente"]: m.get("huella") for m in col.get(include=["metadatas"])["metadatas"]}

    nuevos = iguales = 0
    vistas = set()
    for fuente, texto in leer_documentos():
        vistas.add(fuente)
        h = huella(texto)
        if guardadas.get(fuente) == h:
            iguales += 1
            continue
        if fuente in guardadas:
            col.delete(where={"fuente": fuente})   # ha cambiado: fuera los trozos viejos
        titulo = titulo_de(texto, fuente)
        trozos = trocear(texto, titulo)
        if not trozos:
            continue
        col.add(
            ids=[f"{fuente}#{i}" for i in range(len(trozos))],
            documents=trozos,
            embeddings=embeber(trozos),
            metadatas=[{"fuente": fuente, "titulo": titulo, "huella": h}] * len(trozos),
        )
        nuevos += 1
        print(f"  {fuente}: {len(trozos)} trozos", flush=True)

    borrados = sorted(set(guardadas) - vistas)
    for fuente in borrados:
        col.delete(where={"fuente": fuente})
        print(f"  {fuente}: quitado (ya no está)", flush=True)

    resumen = {"documentos": len(vistas), "indexados": nuevos, "sin_cambios": iguales,
               "quitados": len(borrados), "trozos": col.count(),
               "segundos": round(time.time() - inicio, 1)}
    print(f"Índice al día: {nuevos} indexados, {iguales} sin cambios, {len(borrados)} quitados · "
          f"{resumen['trozos']} trozos ({resumen['segundos']} s)", flush=True)
    return resumen


@app.on_event("startup")
def preparar():
    """Espera a Ollama, descarga el modelo de embeddings si falta e indexa los documentos."""
    for intento in range(30):
        try:
            cliente.show(MODELO_EMBEDDINGS)
            break
        except ResponseError:
            print(f"Descargando {MODELO_EMBEDDINGS}...", flush=True)
            cliente.pull(MODELO_EMBEDDINGS)
            break
        except Exception:
            print(f"Esperando a Ollama ({intento + 1}/30)...", flush=True)
            time.sleep(2)
    else:
        raise RuntimeError(f"No se puede conectar con Ollama en {OLLAMA_HOST}")
    indexar()
    print("Conocimiento listo", flush=True)


# ------------------------------------------------------------ endpoints

class Busqueda(BaseModel):
    texto: str
    k: int = 3


@app.get("/salud")
def salud():
    fuentes = sorted({m["fuente"] for m in coleccion().get(include=["metadatas"])["metadatas"]})
    return {"ok": True, "modelo": MODELO_EMBEDDINGS, "trozos": coleccion().count(), "documentos": fuentes}


@app.post("/buscar")
def buscar(busqueda: Busqueda):
    col = coleccion()
    if col.count() == 0:
        return {"resultados": []}
    r = col.query(
        query_embeddings=embeber([busqueda.texto]),
        n_results=min(busqueda.k, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    resultados = [
        {
            "texto": texto,
            "fuente": meta["fuente"],
            "titulo": meta["titulo"],
            "puntuacion": round(1 - distancia, 3),   # distancia coseno → parecido de 0 a 1
        }
        for texto, meta, distancia in zip(r["documents"][0], r["metadatas"][0], r["distances"][0])
    ]
    return {"resultados": resultados}


@app.post("/reindexar")
def reindexar(completo: bool = False):
    return indexar(completo)
