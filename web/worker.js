// Worker de la versión web: carga Pyodide y el creador y atiende las acciones de la página, de una en una.
// Pyodide 0.29 necesita un worker de tipo módulo (https://pyodide.org/en/0.29.3/usage/webworker.html).
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/pyodide.mjs";

const HASH = new URL(self.location.href).searchParams.get("h") || "";
const RAIZ = "/home/pyodide/app";
// Paquetes del usuario: en IndexedDB, para que sigan ahí al volver (creador/nucleo/rutas.py, directorio_personal).
const PERSONAL = "/home/pyodide/.creador-personajes";
const NECESITAN_PDF = new Set(["pdf", "oficial"]);
const ESCRIBEN_PAQUETES = new Set(["importar_paquete", "quitar_paquete"]);

let pyodide = null;
let llamarPython = null;
let persistente = false;
let extras = null; // reportlab y pypdf: se cargan tras arrancar, en segundo plano
let cola = Promise.resolve();

const avisar = (tipo, datos = {}) => postMessage({ tipo, ...datos });

function descargar(ruta, tipo) {
  return fetch(`${ruta}?h=${HASH}`).then((respuesta) => {
    if (!respuesta.ok) throw new Error(`No se ha podido descargar ${ruta} (${respuesta.status})`);
    return tipo === "json" ? respuesta.json() : respuesta.arrayBuffer();
  });
}

function sincronizar(cargar) {
  return new Promise((resolver, rechazar) => pyodide.FS.syncfs(cargar, (error) => (error ? rechazar(error) : resolver())));
}

async function cargarExtras(ruedas) {
  await pyodide.loadPackage(["micropip", "pillow"]);
  const micropip = pyodide.pyimport("micropip");
  await micropip.install(ruedas.map((rueda) => new URL(`ruedas/${rueda}`, self.location.href).href));
  avisar("extras");
}

async function arrancar() {
  avisar("progreso", { texto: "Cargando Python…", paso: 1 });
  const [py, manifiesto, codigo] = await Promise.all([loadPyodide(), descargar("version.json", "json"), descargar("creador.zip")]);
  pyodide = py;
  avisar("progreso", { texto: "Preparando el creador…", paso: 2 });
  pyodide.unpackArchive(new Uint8Array(codigo), "zip", { extractDir: RAIZ });
  try {
    pyodide.FS.mkdirTree(PERSONAL);
    pyodide.FS.mount(pyodide.FS.filesystems.IDBFS, {}, PERSONAL);
    await sincronizar(true);
    persistente = true;
  } catch (error) {
    avisar("aviso", { texto: "Este navegador no deja guardar paquetes: los que importes se perderán al cerrar la página." });
  }
  avisar("progreso", { texto: "Leyendo los libros…", paso: 3 });
  pyodide.runPython(`
import sys
sys.path.insert(0, ${JSON.stringify(RAIZ)})
from creador.web.sesion import Sesion
sesion = Sesion()
`);
  llamarPython = pyodide.globals.get("sesion").llamar_json;
  extras = cargarExtras(manifiesto.ruedas);
  extras.catch((error) => avisar("aviso", { texto: `No se han podido cargar las librerías de PDF: ${error.message || error}` }));
  avisar("listo", { version: manifiesto.version });
}

async function atender(id, accion, args) {
  try {
    if (accion === "exportar" && NECESITAN_PDF.has(args.formato)) {
      if (!extras) throw new Error("El creador todavía está arrancando");
      await extras;
    }
    const texto = llamarPython(accion, JSON.stringify(args || {}));
    if (persistente && ESCRIBEN_PAQUETES.has(accion)) await sincronizar(false);
    avisar("respuesta", { id, texto });
  } catch (error) {
    avisar("respuesta", { id, error: String((error && error.message) || error) });
  }
}

const arranque = arrancar().catch((error) => avisar("fallo", { texto: String((error && error.message) || error) }));

self.onmessage = ({ data }) => {
  const { id, accion, args } = data;
  cola = cola.then(() => arranque).then(() => atender(id, accion, args));
};
