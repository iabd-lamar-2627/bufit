"""Conocimiento · RAG. Indexa los .md de documentos/ y busca los trozos más parecidos a una pregunta.

- GET  /salud       cuántos documentos y trozos hay indexados
- POST /buscar      {"texto": "...", "k": 3, "modo": "hibrida"} → los k trozos más parecidos, con fuente y puntuación
- POST /reindexar   vuelve a leer los .md (después de editarlos); ?completo=true lo rehace todo

Los embeddings los calcula el contenedor de Ollama con un modelo multilingüe (bge-m3).
Los vectores se guardan con Chroma en /app/vectores y se reutilizan al arrancar: solo se
recalculan los documentos nuevos o cambiados (cada trozo guarda la huella de su documento).

Búsqueda híbrida (MODO_BUSQUEDA):
- semántica: embeddings (bge-m3). Entiende el sentido aunque se use otras palabras.
- por palabras: BM25. Acierta nombres y palabras exactas ("cuarenta", "PIN", "giraboix").
- híbrida (por defecto): hace las dos y mezcla las listas con Reciprocal Rank Fusion.
La "puntuacion" que se devuelve es siempre el parecido semántico (0 a 1), porque el llm la
compara con su UMBRAL. Si un trozo sale también entre los primeros por palabras, los dos
métodos están de acuerdo y se le suma BONUS_ACUERDO.
"""
import hashlib
import logging
import math
import os
import re
import time
import unicodedata
from collections import Counter

import chromadb
import numpy as np
from fastapi import FastAPI
from ollama import Client, ResponseError
from pydantic import BaseModel

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODELO_EMBEDDINGS = os.getenv("MODELO_EMBEDDINGS", "bge-m3")
DIR_DOCUMENTOS = os.getenv("DIR_DOCUMENTOS", "/app/documentos")
DIR_VECTORES = os.getenv("DIR_VECTORES", "/app/vectores")
TAM_TROZO = int(os.getenv("TAM_TROZO", "800"))   # caracteres aproximados por trozo
COLECCION = "documentos"
MODO_BUSQUEDA = os.getenv("MODO_BUSQUEDA", "hibrida")    # hibrida, semantica o palabras
CANDIDATOS = int(os.getenv("CANDIDATOS", "10"))         # cuántos trozos trae cada búsqueda antes de mezclar
RRF_K = 60                                              # constante habitual de Reciprocal Rank Fusion
PUESTOS_ACUERDO = int(os.getenv("PUESTOS_ACUERDO", "3"))  # entre los N primeros por palabras = "de acuerdo"
BONUS_ACUERDO = float(os.getenv("BONUS_ACUERDO", "0.1"))  # se suma a la puntuación si los dos coinciden

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


# ------------------------------------------------------------ búsqueda por palabras (BM25)

# Palabras tan comunes que no dicen nada del tema
VACIAS = set("""a al algo como con cual cuando de del donde el en es esa ese eso esta este esto
estos ha hay la las le les lo los me mi mis muy nada no nos o para pero por que quiero se
si sin sobre su sus te tu tus un una unas uno unos y ya yo""".split())


def palabras(texto: str) -> list[str]:
    """Minúsculas, sin tildes, sin palabras vacías y sin la s del plural ("fichas" → "ficha")."""
    texto = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                    if unicodedata.category(c) != "Mn")
    resultado = []
    for p in re.findall(r"\w+", texto):
        if p in VACIAS:
            continue
        if len(p) > 4 and p.endswith("s"):
            p = p[:-1]
        resultado.append(p)
    return resultado


class BM25:
    """BM25 escrito a mano (sin librerías) para que se vea cómo funciona.

    Puntuación de un trozo = suma, por cada palabra de la pregunta que aparece en él, de
        rareza(palabra) × frecuencia saturada en el trozo, corregida por la longitud del trozo
    """
    K1 = 1.5    # saturación: a partir de unas pocas apariciones, repetir la palabra casi no suma
    B = 0.75    # cuánto se penaliza a los trozos largos (0 = nada, 1 = del todo)

    def construir(self, col):
        datos = col.get(include=["documents"])
        self.ids = datos["ids"]
        self.frecuencias = [Counter(palabras(t)) for t in datos["documents"]]
        self.longitudes = [sum(f.values()) for f in self.frecuencias]
        self.media = (sum(self.longitudes) / len(self.longitudes)) if self.longitudes else 0
        n = len(self.ids)
        en_cuantos = Counter(p for f in self.frecuencias for p in f)     # en cuántos trozos sale cada palabra
        # Rareza (IDF): las palabras que salen en pocos trozos valen mucho; las de todos, casi nada
        self.rareza = {p: math.log(1 + (n - df + 0.5) / (df + 0.5)) for p, df in en_cuantos.items()}

    def buscar(self, texto: str, n: int) -> list[tuple[str, float]]:
        """Los n trozos con más puntuación (solo los que tienen alguna palabra de la pregunta)."""
        pregunta = set(palabras(texto))
        puntos = []
        for id_, frec, largo in zip(self.ids, self.frecuencias, self.longitudes):
            p = 0.0
            for palabra in pregunta:
                tf = frec.get(palabra, 0)
                if tf:
                    p += self.rareza[palabra] * tf * (self.K1 + 1) / (
                        tf + self.K1 * (1 - self.B + self.B * largo / self.media))
            if p > 0:
                puntos.append((id_, p))
        return sorted(puntos, key=lambda x: -x[1])[:n]


bm25 = BM25()


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

    bm25.construir(col)

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
    modo: str | None = None     # hibrida, semantica o palabras; si no se dice, MODO_BUSQUEDA


@app.get("/salud")
def salud():
    fuentes = sorted({m["fuente"] for m in coleccion().get(include=["metadatas"])["metadatas"]})
    return {"ok": True, "modelo": MODELO_EMBEDDINGS, "trozos": coleccion().count(), "documentos": fuentes}


@app.post("/buscar")
def buscar(busqueda: Busqueda):
    col = coleccion()
    if col.count() == 0:
        return {"resultados": []}
    modo = busqueda.modo or MODO_BUSQUEDA
    n = min(max(CANDIDATOS, busqueda.k), col.count())
    vector = embeber([busqueda.texto])[0]

    # 1. Búsqueda semántica: los n trozos con el vector más parecido
    r = col.query(query_embeddings=[vector], n_results=n, include=[])
    puesto_sem = {id_: i + 1 for i, id_ in enumerate(r["ids"][0])}

    # 2. Búsqueda por palabras (BM25)
    por_palabras = bm25.buscar(busqueda.texto, n)
    puesto_pal = {id_: i + 1 for i, (id_, _) in enumerate(por_palabras)}
    puntos_pal = dict(por_palabras)

    # 3. Ordenar según el modo. Híbrida: Reciprocal Rank Fusion, cada lista da 1/(60 + puesto)
    if modo == "semantica":
        orden = list(puesto_sem)
    elif modo == "palabras":
        orden = list(puesto_pal)
    else:
        rrf = Counter()
        for puestos in (puesto_sem, puesto_pal):
            for id_, puesto in puestos.items():
                rrf[id_] += 1 / (RRF_K + puesto)
        orden = [id_ for id_, _ in rrf.most_common()]
    orden = orden[:busqueda.k]
    if not orden:
        return {"resultados": []}

    # 4. Parecido semántico de cada elegido (también de los que solo encontró BM25)
    elegidos = col.get(ids=orden, include=["documents", "metadatas", "embeddings"])
    por_id = dict(zip(elegidos["ids"], zip(elegidos["documents"], elegidos["metadatas"],
                                            elegidos["embeddings"])))
    q = np.asarray(vector)
    resultados = []
    for id_ in orden:
        texto, meta, emb = por_id[id_]
        e = np.asarray(emb)
        semantica = float(q @ e / (np.linalg.norm(q) * np.linalg.norm(e)))
        acuerdo = modo == "hibrida" and puesto_pal.get(id_, 99) <= PUESTOS_ACUERDO
        resultados.append({
            "texto": texto,
            "fuente": meta["fuente"],
            "titulo": meta["titulo"],
            # Lo que usa el llm con su UMBRAL: el parecido semántico, con premio si las dos búsquedas coinciden
            "puntuacion": round(min(1.0, semantica + (BONUS_ACUERDO if acuerdo else 0)), 3),
            "semantica": round(semantica, 3),
            "bm25": round(puntos_pal.get(id_, 0.0), 2),
            "puesto_semantica": puesto_sem.get(id_),
            "puesto_palabras": puesto_pal.get(id_),
        })
    return {"modo": modo, "resultados": resultados}


@app.post("/reindexar")
def reindexar(completo: bool = False):
    return indexar(completo)
