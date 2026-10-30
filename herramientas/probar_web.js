// Prueba de la versión web en Chromium, de punta a punta, con Playwright.
//
//   python herramientas/compilar_web.py && python -m http.server -d dist/web 8000 &
//   node herramientas/probar_web.js [http://localhost:8000] [homebrew.zip]
//
// Necesita Playwright con Chromium (npm install playwright; npx playwright install chromium). Recorre el
// cuestionario con historia, el asistente, las cuatro descargas, abrir el .json en otro navegador, el guardado
// local con recarga y, si se le pasa un .zip, importar y quitar un paquete. Comprueba en cada pantalla que no hay
// errores de JavaScript ni de Python y que en un móvil (390 px) nada se sale por la derecha. Sale con código 1 si
// algo falla.
const { chromium } = require("playwright");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const URL_BASE = process.argv[2] || "http://localhost:8000";
const HOMEBREW = process.argv[3];
const ARRANQUE = 120000; // la primera carga baja Python y los libros
const fallos = [];

function comprobar(condicion, mensaje) {
  if (!condicion) fallos.push(mensaje);
  console.log(`${condicion ? "✓" : "✗"} ${mensaje}`);
}

async function abrir(navegador, opciones = {}) {
  const contexto = await navegador.newContext({ acceptDownloads: true, ...opciones });
  const pagina = await contexto.newPage();
  pagina.on("pageerror", (e) => fallos.push(`Error de JavaScript: ${e.message}`));
  pagina.on("console", (m) => m.type() === "error" && fallos.push(`Consola: ${m.text()}`));
  await pagina.goto(URL_BASE);
  await pagina.waitForSelector("#app:not([hidden]) .portada", { timeout: ARRANQUE });
  const pintado = () => pagina.evaluate(() => Number(document.body.dataset.pintado || 0));
  // Hace algo y espera a que la página repinte con la respuesta de Python; ninguna respuesta debe traer un error.
  pagina.yEsperar = async (accion) => {
    const n = await pintado();
    await accion();
    await pagina.waitForFunction((n) => Number(document.body.dataset.pintado) > n, n, { timeout: 60000 });
    const error = await pagina.$(".aviso-flotante.error");
    if (error) fallos.push(`Error en la página: ${await error.textContent()}`);
  };
  pagina.sinDesbordar = async (donde) => {
    const [ancho, visible] = await pagina.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    if (ancho > visible) fallos.push(`${donde}: la página mide ${ancho} px de ancho en una pantalla de ${visible}`);
  };
  return pagina;
}

async function cuestionario(pagina) {
  await pagina.yEsperar(() => pagina.click('button:has-text("Crear con preguntas")'));
  await pagina.sinDesbordar("Cuestionario");
  await pagina.yEsperar(() => pagina.selectOption(".contenido .campo select", "4"));
  await pagina.yEsperar(() => pagina.click('.interruptor label:has-text("Multiclase")'));
  await pagina.yEsperar(() => pagina.click('.segmentado button:has-text("Rápido")'));
  await pagina.yEsperar(() => pagina.click('button:has-text("Empezar")'));
  await pagina.sinDesbordar("Pregunta");
  for (let i = 0; await pagina.$(".pantalla.pregunta"); i++) {
    await pagina.yEsperar(() => pagina.click(`.respuesta >> nth=${i % 3}`));
  }
  comprobar(await pagina.$(".pantalla.resultado"), "El cuestionario lleva al resultado");
  await pagina.sinDesbordar("Resultado");
  comprobar((await pagina.$$(".recomendaciones")).length === 3, "Hay propuestas de raza, clase y trasfondo");
  await pagina.yEsperar(() => pagina.click(".recomendaciones >> nth=1 >> .opcion >> nth=1"));
  await pagina.fill("input[type=text]", "Ñandú el Sabio");
  await pagina.yEsperar(() => pagina.press("input[type=text]", "Tab"));
  await pagina.yEsperar(() => pagina.click('button:has-text("Su historia")'));
  await pagina.sinDesbordar("Historia");
  const grupos = (await pagina.$$(".respuestas")).length;
  comprobar(grupos > 1, `La historia hasta nivel 4 trae preguntas (${grupos})`);
  for (let i = 0; i < grupos; i++) await pagina.yEsperar(() => pagina.click(`.respuestas >> nth=${i} >> .respuesta >> nth=0`));
  await pagina.yEsperar(() => pagina.click('button:has-text("Crear personaje")'));
  const cabecera = await pagina.textContent(".cabecera");
  comprobar(cabecera.startsWith("Ñandú el Sabio") && /\d \(/.test(cabecera), `Personaje creado: ${cabecera}`);
  await pagina.sinDesbordar("Resumen");
}

async function descargas(pagina, carpeta) {
  const esperados = { "Ficha en PDF": "%PDF", "Hoja oficial": "%PDF", "Nota y guía": "---", "Personaje (.json)": "{" };
  for (const [boton, inicio] of Object.entries(esperados)) {
    const [descarga] = await Promise.all([pagina.waitForEvent("download", { timeout: 120000 }),
                                          pagina.click(`button:has-text("${boton}")`)]);
    const ruta = path.join(carpeta, descarga.suggestedFilename());
    await descarga.saveAs(ruta);
    const datos = fs.readFileSync(ruta);
    comprobar(datos.length > 100 && datos.subarray(0, inicio.length).toString() === inicio,
              `${boton}: ${descarga.suggestedFilename()} (${datos.length} bytes)`);
  }
  return path.join(carpeta, fs.readdirSync(carpeta).find((n) => n.endsWith(".json")));
}

async function asistente(pagina) {
  await pagina.yEsperar(() => pagina.click('button:has-text("Crear paso a paso")'));
  for (const paso of ["Raza", "Clase", "Características", "Trasfondo", "Equipo", "Conjuros", "Detalles", "Resumen"]) {
    await pagina.yEsperar(() => pagina.click(`.lateral .paso:has-text("${paso}")`));
    await pagina.sinDesbordar(`Paso ${paso}`);
    if (paso === "Raza") await pagina.yEsperar(() => pagina.click('.lista-opciones >> nth=0 >> .opcion:text-is("Elfo")'));
    if (paso === "Clase") await pagina.yEsperar(() => pagina.click('.lista-opciones >> nth=0 >> .opcion:text-is("Mago")'));
    if (paso === "Características") await pagina.yEsperar(() => pagina.click('button:has-text("Repartir según mi clase")'));
  }
  comprobar((await pagina.textContent(".cabecera")).includes("Mago 1"), "El asistente crea un mago de nivel 1");
}

(async () => {
  const navegador = await chromium.launch({ env: { ...process.env, LANG: "C.UTF-8", LC_ALL: "C.UTF-8" } });
  const carpeta = fs.mkdtempSync(path.join(os.tmpdir(), "probar-web-"));
  for (const [nombre, opciones] of [["Escritorio", { viewport: { width: 1200, height: 900 } }],
                                    ["Móvil oscuro", { viewport: { width: 390, height: 844 }, colorScheme: "dark" }]]) {
    console.log(`— ${nombre}`);
    const pagina = await abrir(navegador, opciones);
    await pagina.sinDesbordar("Portada");
    await cuestionario(pagina);
    await asistente(await abrir(navegador, opciones));
    if (nombre !== "Escritorio") continue;
    const json = await descargas(pagina, carpeta);
    // Guardado en el navegador: recargar y seguir donde estaba.
    await pagina.reload();
    await pagina.waitForSelector("#app:not([hidden]) .recientes", { timeout: ARRANQUE });
    await pagina.yEsperar(() => pagina.click('.recientes button:has-text("Continuar")'));
    comprobar((await pagina.textContent(".cabecera")).startsWith("Ñandú el Sabio"), "Tras recargar, «Continuar» recupera el personaje");
    // El .json en otro navegador (sin nada guardado).
    const otra = await abrir(navegador);
    await otra.yEsperar(() => otra.setInputFiles('.archivo:has(button:has-text("Abrir personaje")) input', json));
    comprobar((await otra.textContent(".cabecera")).startsWith("Ñandú el Sabio"), "El .json descargado se abre en otro navegador");
    if (HOMEBREW) {
      pagina.once("dialog", (d) => d.accept());
      await pagina.yEsperar(() => pagina.click('.pie button:has-text("Inicio")'));
      await pagina.yEsperar(() => pagina.click('button:has-text("Paquetes")'));
      await pagina.yEsperar(() => pagina.setInputFiles(".archivo input", HOMEBREW));
      await pagina.reload();
      await pagina.waitForSelector("#app:not([hidden]) .portada", { timeout: ARRANQUE });
      const homebrew = await pagina.$$eval(".interruptor", (n) => n.filter((x) => x.textContent.includes("Homebrew")).length);
      comprobar(homebrew > 0, "El paquete importado sigue tras recargar");
      await pagina.yEsperar(() => pagina.click('button:has-text("Paquetes")'));
      pagina.once("dialog", (d) => d.accept());
      await pagina.yEsperar(() => pagina.click('button:has-text("Quitar")'));
      comprobar(!(await pagina.$('button:has-text("Quitar")')), "El paquete se quita");
    }
  }
  await navegador.close();
  fs.rmSync(carpeta, { recursive: true, force: true });
  console.log(fallos.length ? `\n${fallos.length} fallo(s):\n- ${fallos.join("\n- ")}` : "\nTodo correcto.");
  process.exit(fallos.length ? 1 : 0);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
