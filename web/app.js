// Página de la versión web: pinta las pantallas que describe Python (creador/web/sesion.py) y le manda lo que
// hace el usuario. Python corre en un worker (worker.js); aquí solo hay interfaz y guardado en el navegador.

const HASH = document.documentElement.dataset.hash || "";
const CLAVE_RECIENTES = "creador-personajes:recientes";
const CLAVE_PERSONAJE = (id) => `creador-personajes:pj:${id}`;
const CLAVE_TEMA = "creador-personajes:tema";
const MAX_RECIENTES = 40;
const ESPERA_OCUPADO = 300; // ms antes de enseñar que está trabajando
const OPCIONES_CON_FILTRO = 12; // listas largas: con un campo para filtrar

const $carga = document.getElementById("carga");
const $app = document.getElementById("app");
const $avisos = document.getElementById("avisos");

// ── worker ────────────────────────────────────────────────────────────────

const worker = new Worker(new URL(`worker.js?h=${HASH}`, import.meta.url), { type: "module" });
const pendientes = new Map();
let siguienteId = 1;
let enCurso = 0;
let temporizadorOcupado = null;

worker.onmessage = ({ data }) => {
  switch (data.tipo) {
    case "progreso":
      document.getElementById("carga-texto").textContent = data.texto;
      document.getElementById("carga-barra").value = data.paso;
      break;
    case "listo":
      document.getElementById("version").textContent = data.version;
      enviar("ir", { pantalla: "portada" }).then(() => {
        $carga.hidden = true;
        $app.hidden = false;
      });
      break;
    case "extras":
      break;
    case "aviso":
      aviso(data.texto, "aviso");
      break;
    case "fallo":
      fallo(data.texto);
      break;
    case "respuesta": {
      const promesa = pendientes.get(data.id);
      pendientes.delete(data.id);
      if (promesa) (data.error ? promesa.rechazar(new Error(data.error)) : promesa.resolver(JSON.parse(data.texto)));
      break;
    }
  }
};
worker.onerror = (evento) => fallo(evento.message || "El creador se ha detenido");

function fallo(texto) {
  $carga.hidden = false;
  $app.hidden = true;
  $carga.classList.add("con-fallo");
  document.getElementById("carga-texto").textContent = `No se ha podido arrancar: ${texto}`;
}

function llamar(accion, args = {}) {
  const id = siguienteId++;
  enCurso++;
  clearTimeout(temporizadorOcupado);
  temporizadorOcupado = setTimeout(() => document.body.classList.add("ocupado"), ESPERA_OCUPADO);
  return new Promise((resolver, rechazar) => {
    pendientes.set(id, { resolver, rechazar });
    worker.postMessage({ id, accion, args });
  }).finally(() => {
    if (--enCurso === 0) {
      clearTimeout(temporizadorOcupado);
      document.body.classList.remove("ocupado");
    }
  });
}

/** Manda una acción y pinta lo que vuelve: la vista, el archivo que descargar, el mensaje o el error. */
async function enviar(accion, args = {}) {
  let respuesta;
  try {
    respuesta = await llamar(accion, args);
  } catch (error) {
    console.error(error);
    aviso(`Algo ha fallado: ${error.message.split("\n").filter(Boolean).slice(-1)[0]}`, "error");
    return;
  }
  guardar(respuesta.estado);
  pintar(respuesta.vista);
  if (respuesta.archivo) descargarArchivo(respuesta.archivo);
  if (respuesta.mensaje) aviso(respuesta.mensaje, "exito");
  if (respuesta.error) aviso(respuesta.error, "error");
  return respuesta;
}

// ── guardado en el navegador ──────────────────────────────────────────────

function leerRecientes() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_RECIENTES)) || [];
  } catch {
    return [];
  }
}

let avisoSinGuardar = false;

function guardar(estado) {
  if (!estado || !estado.id) return;
  try {
    localStorage.setItem(CLAVE_PERSONAJE(estado.id), JSON.stringify(estado));
    const lista = leerRecientes().filter((r) => r.id !== estado.id);
    lista.unshift({ id: estado.id, titulo: estado.titulo, fecha: Date.now() });
    for (const sobrante of lista.splice(MAX_RECIENTES)) localStorage.removeItem(CLAVE_PERSONAJE(sobrante.id));
    localStorage.setItem(CLAVE_RECIENTES, JSON.stringify(lista));
  } catch (error) {
    if (!avisoSinGuardar) {
      avisoSinGuardar = true;
      aviso("Este navegador no deja guardar: descarga el personaje (.json) para no perderlo.", "aviso");
    }
  }
}

function leerPersonaje(id) {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_PERSONAJE(id)));
  } catch {
    return null;
  }
}

function borrarPersonaje(id) {
  try {
    localStorage.removeItem(CLAVE_PERSONAJE(id));
    localStorage.setItem(CLAVE_RECIENTES, JSON.stringify(leerRecientes().filter((r) => r.id !== id)));
  } catch {
    /* sin almacenamiento no hay nada que borrar */
  }
}

// ── utilidades de interfaz ───────────────────────────────────────────────

function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (clave === "class") nodo.className = valor;
    else if (clave in nodo && typeof valor !== "string") nodo[clave] = valor;
    else nodo.setAttribute(clave, valor === true ? "" : valor);
  }
  for (const hijo of hijos.flat()) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : String(hijo));
  }
  return nodo;
}

function icono(nombre, clase = "") {
  if (!nombre) return null;
  const nodo = el("span", { class: `icono ${clase}`, "aria-hidden": "true" });
  nodo.style.setProperty("--icono", `url("recursos/iconos/${nombre}.png")`);
  return nodo;
}

let contadorIds = 0;
const nuevoId = () => `c${++contadorIds}`;

/** Identifica un control entre repintados, para devolverle el foco. */
const claveDe = (componente, extra = "") => `${componente.accion}|${JSON.stringify(componente.args || {})}|${extra}`;

function campo(etiqueta, control, id) {
  if (!etiqueta) return control;
  return el("label", { class: "campo", for: id }, el("span", { class: "etiqueta" }, etiqueta), control);
}

const sinAcentos = (texto) => texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

const filtros = new Map(); // texto escrito en cada filtro o buscador, que sobrevive a los repintados

function aviso(texto, tipo = "") {
  const nodo = el("div", { class: `aviso-flotante ${tipo}`, role: tipo === "error" ? "alert" : "status" }, texto);
  nodo.addEventListener("click", () => nodo.remove());
  $avisos.append(nodo);
  setTimeout(() => nodo.remove(), tipo === "error" ? 9000 : 5000);
}

function descargarArchivo({ nombre, tipo, datos }) {
  const bytes = Uint8Array.from(atob(datos), (c) => c.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: tipo }));
  const enlace = el("a", { href: url, download: nombre });
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function leerBase64(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onload = () => resolver(String(lector.result).split(",", 2)[1] || "");
    lector.onerror = () => rechazar(lector.error);
    lector.readAsDataURL(archivo);
  });
}

function hace(fecha) {
  const minutos = Math.round((Date.now() - fecha) / 60000);
  if (minutos < 1) return "ahora mismo";
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  return new Date(fecha).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });
}

// ── componentes ──────────────────────────────────────────────────────────

const PINTORES = {
  titulo(c) {
    return el(`h${Math.min(c.nivel, 4)}`, { class: "titulo" }, icono(c.icono), el("span", {}, c.texto));
  },

  texto(c) {
    return el("p", { class: `texto ${c.estilo || ""}` }, c.texto);
  },

  fila(c) {
    return el("div", { class: "fila" }, c.hijos.map(pintarComponente));
  },

  caja(c) {
    return el("div", { class: `caja ${c.estilo || ""}` }, c.hijos.map(pintarComponente));
  },

  columnas(c) {
    return el("div", { class: "columnas" }, c.hijos.map(pintarComponente));
  },

  boton(c) {
    const boton = el("button", { type: "button", class: `boton ${c.estilo}`, disabled: c.desactivado,
                                 "data-clave": claveDe(c) }, icono(c.icono), c.texto);
    boton.addEventListener("click", () => {
      if (c.confirmar && !window.confirm(c.confirmar)) return;
      enviar(c.accion, c.args);
    });
    return boton;
  },

  interruptor(c) {
    const id = nuevoId();
    const casilla = el("input", { type: "checkbox", role: "switch", id, checked: c.activo, "data-clave": claveDe(c) });
    casilla.addEventListener("change", () => enviar(c.accion, { ...c.args, valor: casilla.checked }));
    return el("div", { class: "interruptor" },
      el("label", { for: id }, casilla, el("span", { class: "deslizador", "aria-hidden": "true" }),
         el("span", { class: "etiqueta" }, c.texto)),
      c.ayuda ? el("p", { class: "ayuda" }, c.ayuda) : null);
  },

  menu(c) {
    const id = nuevoId();
    const selector = el("select", { id, "data-clave": claveDe(c) });
    const valores = c.valores.map(([valor]) => valor);
    if (c.vacio !== null || !valores.includes(c.actual)) selector.append(el("option", { value: "" }, c.vacio ?? "—"));
    for (const [valor, texto] of c.valores) selector.append(el("option", { value: valor }, texto));
    selector.value = valores.includes(c.actual) ? c.actual : "";
    selector.addEventListener("change", () => enviar(c.accion, { ...c.args, valor: selector.value }));
    return campo(c.etiqueta, selector, id);
  },

  segmentado(c) {
    const grupo = el("div", { class: "segmentado", role: "group", "aria-label": c.etiqueta || null });
    for (const [valor, texto] of c.valores) {
      const boton = el("button", { type: "button", "aria-pressed": String(valor === c.actual),
                                   "data-clave": claveDe(c, valor) }, texto);
      boton.addEventListener("click", () => valor !== c.actual && enviar(c.accion, { ...c.args, valor }));
      grupo.append(boton);
    }
    return c.etiqueta ? el("div", { class: "campo" }, el("span", { class: "etiqueta" }, c.etiqueta), grupo) : grupo;
  },

  entrada(c) {
    const id = nuevoId();
    const control = c.multilinea ? el("textarea", { rows: 3 }) : el("input", { type: "text" });
    Object.assign(control, { id, value: c.valor ?? "", placeholder: c.marcador || "" });
    control.dataset.clave = claveDe(c);
    control.addEventListener("change", () => enviar(c.accion, { ...c.args, valor: control.value }));
    const caja = el("div", { class: `entrada ${c.ancho}` }, campo(c.etiqueta, control, id));
    if (c.sugerencias && c.sugerencias.length) {
      const sugerencias = el("select", { class: "sugerencias", "aria-label": `Sugerencias para ${c.etiqueta}` },
        el("option", { value: "" }, "Sugerencias de tu trasfondo…"),
        c.sugerencias.map((texto, i) => el("option", { value: String(i) }, texto)));
      sugerencias.addEventListener("change", () => {
        if (sugerencias.value === "") return;
        enviar(c.accion, { ...c.args, valor: c.sugerencias[Number(sugerencias.value)] });
      });
      caja.append(sugerencias);
    }
    return caja;
  },

  lista_opciones(c) {
    const clave = claveDe(c, "filtro");
    const lista = el("div", { class: "lista", role: "listbox", "aria-label": c.titulo });
    const botones = c.opciones.map((opcion) => {
      const elegida = opcion.id === c.seleccion;
      const boton = el("button", { type: "button", role: "option", class: "opcion", "aria-selected": String(elegida),
                                   "data-clave": claveDe(c, opcion.id), "data-texto": sinAcentos(opcion.nombre) },
                       opcion.nombre);
      boton.addEventListener("click", () => !elegida && enviar(c.accion, { ...c.args, valor: opcion.id }));
      return boton;
    });
    lista.append(...botones);
    const columna = el("div", { class: "columna-lista" });
    if (c.opciones.length > OPCIONES_CON_FILTRO) {
      const filtro = el("input", { type: "search", class: "filtro", placeholder: `Filtrar ${c.opciones.length} opciones…`,
                                   "aria-label": `Filtrar ${c.titulo}`, value: filtros.get(clave) || "",
                                   "data-clave": clave });
      const aplicar = () => {
        filtros.set(clave, filtro.value);
        const buscado = sinAcentos(filtro.value.trim());
        for (const boton of botones) boton.hidden = !boton.dataset.texto.includes(buscado);
      };
      filtro.addEventListener("input", aplicar);
      aplicar();
      columna.append(filtro);
    }
    columna.append(lista);
    requestAnimationFrame(() => {
      const elegida = lista.querySelector('[aria-selected="true"]');
      if (elegida) lista.scrollTop = elegida.offsetTop - lista.offsetTop - lista.clientHeight / 2 + elegida.clientHeight / 2;
    });
    const d = c.detalle;
    const detalle = d
      ? el("div", { class: "detalle" },
          el("h3", { class: "titulo" }, icono(d.icono, "grande"), el("span", {}, d.nombre)),
          el("p", { class: "texto gris" }, d.origen),
          d.perfil ? el("p", { class: "texto perfil" }, d.perfil) : null,
          d.descripcion ? el("p", { class: "texto" }, d.descripcion) : null)
      : el("div", { class: "detalle vacio" }, el("p", { class: "texto gris" }, "Elige una opción de la lista para ver su descripción."));
    return el("section", { class: "lista-opciones" }, el("h3", { class: "titulo" }, c.titulo),
              el("div", { class: "lista-cuerpo" }, columna, detalle));
  },

  casillas(c) {
    const rejilla = el("div", { class: "casillas", style: `--columnas:${c.columnas}` });
    for (const opcion of c.opciones) {
      const casilla = el("input", { type: "checkbox", checked: opcion.marcada, disabled: opcion.bloqueada && !opcion.marcada,
                                    "data-clave": claveDe(c, opcion.id) });
      casilla.addEventListener("change", () => enviar(c.accion, { ...c.args, id: opcion.id, marcada: casilla.checked }));
      rejilla.append(el("label", { class: "casilla" }, casilla, el("span", {}, opcion.nombre)));
    }
    return rejilla;
  },

  avisos(c) {
    if (!c.mensajes.length) return el("div", { class: "avisos exito" }, el("p", { class: "texto" }, "✓ Paso completo"));
    return el("div", { class: `avisos ${c.completo ? "exito" : ""}` }, el("p", { class: "texto negrita" }, c.titulo),
              el("ul", {}, c.mensajes.map((m) => el("li", {}, m))));
  },

  barra(c) {
    return el("div", { class: "barra" }, el("progress", { max: 1, value: c.valor, "aria-label": c.etiqueta || "Progreso" }),
              c.etiqueta ? el("span", { class: "texto gris" }, c.etiqueta) : null);
  },

  respuestas(c) {
    const rejilla = el("div", { class: "respuestas", style: `--columnas:${c.columnas}` });
    for (const opcion of c.opciones) {
      const boton = el("button", { type: "button", class: `respuesta ${opcion.propuesta ? "propuesta" : ""}`,
                                   "aria-pressed": String(opcion.elegida), "data-clave": claveDe(c, opcion.id) },
                       el("span", { class: "respuesta-texto" }, opcion.texto),
                       opcion.detalle ? el("span", { class: "respuesta-detalle" }, opcion.detalle) : null);
      boton.addEventListener("click", () => enviar(c.accion, { ...c.args, respuesta: opcion.id }));
      rejilla.append(boton);
    }
    return rejilla;
  },

  tabla(c) {
    return el("div", { class: "tabla-marco" }, el("table", { class: "tabla" },
      el("thead", {}, el("tr", {}, c.cabeceras.map((cabecera) => el("th", { scope: "col" }, cabecera)))),
      el("tbody", {}, c.filas.map((fila) => el("tr", {}, fila.map((celda, i) =>
        el(i === 0 ? "th" : "td", i === 0 ? { scope: "row" } : {}, typeof celda === "string" ? celda : pintarComponente(celda))))))));
  },

  preformateado(c) {
    return el("pre", { class: "preformateado" }, c.texto);
  },

  archivo(c) {
    const selector = el("input", { type: "file", accept: c.aceptar, hidden: true });
    const boton = el("button", { type: "button", class: `boton ${c.estilo}`, "data-clave": claveDe(c) }, c.texto);
    boton.addEventListener("click", () => selector.click());
    selector.addEventListener("change", async () => {
      const archivo = selector.files[0];
      if (!archivo) return;
      try {
        enviar(c.accion, { ...c.args, nombre: archivo.name, datos: await leerBase64(archivo) });
      } catch (error) {
        aviso(`No se ha podido leer «${archivo.name}»`, "error");
      }
    });
    return el("span", { class: "archivo" }, boton, selector);
  },

  radios(c) {
    const nombre = nuevoId();
    const grupo = el("div", { class: "radios", role: "radiogroup" });
    for (const [valor, texto] of c.opciones) {
      const radio = el("input", { type: "radio", name: nombre, value: valor, checked: valor === c.seleccion,
                                  "data-clave": claveDe(c, valor) });
      radio.addEventListener("change", () => radio.checked && enviar(c.accion, { ...c.args, valor }));
      grupo.append(el("label", { class: "radio" }, radio, el("span", {}, texto)));
    }
    return grupo;
  },

  eleccion(c) {
    const cabecera = el("p", { class: `texto negrita ${c.completa ? "" : "pendiente"}` },
                        `${c.completa ? "✓" : "•"} ${c.nombre}  ·  elige ${c.elegir}`);
    const cuerpo = { casillas: eleccionCasillas, desplegables: eleccionDesplegables, buscador: eleccionBuscador }[c.modo](c);
    return el("div", { class: "eleccion caja" }, cabecera, c.etiqueta ? el("p", { class: "texto gris" }, c.etiqueta) : null,
              cuerpo);
  },

  recomendaciones(c) {
    const lista = el("div", { class: "lista-recomendaciones", role: "listbox", "aria-label": c.titulo });
    for (const opcion of c.opciones) {
      const elegida = opcion.id === c.seleccion;
      const boton = el("button", { type: "button", role: "option", class: "opcion", "aria-selected": String(elegida),
                                   "data-clave": claveDe(c, opcion.id) },
                       el("span", {}, opcion.nombre), el("span", { class: "afinidad" }, `${opcion.afinidad}%`));
      boton.addEventListener("click", () => !elegida && enviar(c.accion, { ...c.args, valor: opcion.id }));
      lista.append(boton);
    }
    return el("section", { class: "recomendaciones caja" }, el("h3", { class: "titulo" }, icono(c.icono, "grande"),
              el("span", {}, c.titulo)), lista, el("p", { class: "texto" }, c.descripcion));
  },

  recientes() {
    const recientes = leerRecientes();
    if (!recientes.length) return null;
    const filas = recientes.map((reciente) => {
      const continuar = el("button", { type: "button", class: "boton primario" }, "Continuar");
      continuar.addEventListener("click", () => {
        const estado = leerPersonaje(reciente.id);
        if (!estado) {
          aviso("No queda nada guardado de ese personaje", "error");
          borrarPersonaje(reciente.id);
          enviar("ir", { pantalla: "portada" });
          return;
        }
        enviar("restaurar", { estado });
      });
      const borrar = el("button", { type: "button", class: "boton enlace" }, "Borrar");
      borrar.addEventListener("click", () => {
        if (!window.confirm(`¿Borrar «${reciente.titulo}» de este navegador? No se puede deshacer.`)) return;
        borrarPersonaje(reciente.id);
        enviar("ir", { pantalla: "portada" });
      });
      return el("li", { class: "reciente" }, el("span", { class: "reciente-titulo" }, reciente.titulo),
                el("span", { class: "texto gris" }, hace(reciente.fecha)), el("span", { class: "fila" }, continuar, borrar));
    });
    return el("section", { class: "caja recientes" }, el("h3", { class: "titulo" }, "Tus personajes en este navegador"),
              el("p", { class: "texto gris" }, "Se guardan solos mientras los creas, pero solo en este navegador: descarga el " +
                "personaje (.json) para tenerlo a salvo o llevarlo a otro dispositivo."),
              el("ul", { class: "lista-recientes" }, filas));
  },
};

function textoOpcion(opcion) {
  return opcion.motivo ? `${opcion.nombre} (${opcion.motivo})` : opcion.nombre;
}

function eleccionCasillas(c) {
  const llenas = c.seleccion.length >= c.elegir;
  const rejilla = el("div", { class: "casillas", style: "--columnas:3" });
  const casillas = c.opciones.map((opcion) => {
    const marcada = c.seleccion.includes(opcion.id);
    const casilla = el("input", { type: "checkbox", checked: marcada, value: opcion.id,
                                  disabled: !marcada && (llenas || Boolean(opcion.motivo)), "data-clave": claveDe(c, opcion.id) });
    rejilla.append(el("label", { class: "casilla" }, casilla, el("span", {}, textoOpcion(opcion))));
    return casilla;
  });
  for (const casilla of casillas) {
    casilla.addEventListener("change", () => enviar(c.accion, { ...c.args, valores: casillas.filter((x) => x.checked).map((x) => x.value) }));
  }
  return rejilla;
}

function eleccionDesplegables(c) {
  const libres = c.opciones.filter((o) => !o.motivo);
  const fila = el("div", { class: "desplegables" });
  const menus = [];
  for (let i = 0; i < c.elegir; i++) {
    const actual = c.seleccion[i];
    const menu = el("select", { "aria-label": `${c.nombre} ${i + 1}`, "data-clave": claveDe(c, i) },
                    el("option", { value: "" }, "— elige —"),
                    libres.map((o) => el("option", { value: o.id }, textoOpcion(o))));
    const bloqueada = c.opciones.find((o) => o.id === actual && o.motivo);
    if (bloqueada) menu.append(el("option", { value: bloqueada.id }, textoOpcion(bloqueada)));
    menu.value = actual ?? "";
    menu.addEventListener("change", () => enviar(c.accion, { ...c.args, valores: menus.map((m) => m.value).filter(Boolean) }));
    menus.push(menu);
    fila.append(menu);
  }
  return fila;
}

function eleccionBuscador(c) {
  const clave = claveDe(c, "buscar");
  const nombres = new Map(c.opciones.map((o) => [o.id, o.nombre]));
  const busqueda = el("input", { type: "search", class: "filtro", value: filtros.get(clave) || "", "data-clave": clave,
                                 placeholder: `Buscar entre ${c.opciones.length} opciones…`, "aria-label": `Buscar: ${c.nombre}` });
  const elegidas = el("p", { class: "texto" },
                      `Elegidas: ${c.seleccion.map((id) => nombres.get(id) || id).join(", ") || "ninguna"}`);
  const resultados = el("div", { class: "casillas resultados", style: "--columnas:2" });
  const llenas = c.seleccion.length >= c.elegir;
  const pintarResultados = () => {
    filtros.set(clave, busqueda.value);
    const buscado = sinAcentos(busqueda.value.trim());
    const coinciden = c.opciones.filter((o) => sinAcentos(o.nombre).includes(buscado));
    coinciden.sort((a, b) => c.seleccion.includes(b.id) - c.seleccion.includes(a.id)); // las elegidas primero
    resultados.replaceChildren();
    for (const opcion of coinciden.slice(0, c.max_resultados)) {
      const marcada = c.seleccion.includes(opcion.id);
      const casilla = el("input", { type: "checkbox", checked: marcada, disabled: !marcada && (llenas || Boolean(opcion.motivo)),
                                    "data-clave": claveDe(c, opcion.id) });
      casilla.addEventListener("change", () => {
        const valores = casilla.checked ? [...c.seleccion, opcion.id] : c.seleccion.filter((id) => id !== opcion.id);
        enviar(c.accion, { ...c.args, valores });
      });
      resultados.append(el("label", { class: "casilla" }, casilla, el("span", {}, textoOpcion(opcion))));
    }
    if (coinciden.length > c.max_resultados) {
      resultados.append(el("p", { class: "texto gris" }, `… y ${coinciden.length - c.max_resultados} más: escribe para afinar`));
    } else if (!coinciden.length) {
      resultados.append(el("p", { class: "texto gris" }, "Nada coincide con la búsqueda"));
    }
  };
  busqueda.addEventListener("input", pintarResultados);
  pintarResultados();
  return el("div", { class: "buscador" }, busqueda, elegidas, resultados);
}

function pintarComponente(componente) {
  if (componente === null || componente === undefined) return null;
  if (typeof componente === "string") return document.createTextNode(componente);
  const pintor = PINTORES[componente.t];
  if (!pintor) return el("p", { class: "texto aviso" }, `(No sé pintar «${componente.t}»)`);
  return pintor(componente);
}

// ── pantallas ────────────────────────────────────────────────────────────

let anterior = { pantalla: null, paso: null };

function pintar(vista) {
  const enfocado = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.clave : null;
  const seleccion = enfocado && "selectionStart" in document.activeElement
    ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
  const mismaPantalla = anterior.pantalla === vista.pantalla && anterior.paso === (vista.paso || null);
  const desplazamiento = window.scrollY;

  const contenido = el("div", { class: "contenido" }, vista.contenido.map(pintarComponente));
  if (vista.lateral) {
    $app.replaceChildren(el("div", { class: "asistente" }, pintarLateral(vista.lateral),
      el("main", { class: "principal" },
         el("header", { class: "cabecera" }, icono(vista.cabecera.icono, "grande"), el("span", {}, vista.cabecera.texto)),
         contenido,
         el("footer", { class: "pie" }, vista.pie.map(pintarComponente)))));
  } else {
    $app.replaceChildren(el("main", { class: `pantalla ${vista.pantalla}` }, contenido), pintarCreditos());
  }
  document.body.dataset.pantalla = vista.pantalla;
  document.body.dataset.pintado = String(Number(document.body.dataset.pintado || 0) + 1); // para las pruebas

  if (mismaPantalla) window.scrollTo(0, desplazamiento);
  else window.scrollTo(0, 0);
  if (enfocado) {
    const nodo = [...$app.querySelectorAll("[data-clave]")].find((n) => n.dataset.clave === enfocado);
    if (nodo) {
      nodo.focus({ preventScroll: true });
      if (seleccion && "setSelectionRange" in nodo) {
        try {
          nodo.setSelectionRange(...seleccion);
        } catch {
          /* los campos que no son de texto no tienen selección */
        }
      }
    }
  }
  anterior = { pantalla: vista.pantalla, paso: vista.paso || null };
}

function pintarLateral(pasos) {
  return el("nav", { class: "lateral", "aria-label": "Pasos" }, el("ol", {}, pasos.map((paso) => {
    const boton = el("button", { type: "button", class: "paso", "aria-current": paso.actual ? "step" : null,
                                 "data-clave": `paso|${paso.id}` },
                     icono(paso.icono), el("span", { class: "paso-titulo" }, paso.titulo),
                     el("span", { class: `paso-estado ${paso.completo ? "completo" : ""}`, "aria-label": paso.completo ? "completo" : "pendiente" },
                        paso.completo ? "✓" : "•"));
    boton.addEventListener("click", () => !paso.actual && enviar("paso", { paso: paso.id }));
    return el("li", {}, boton);
  })));
}

function pintarCreditos() {
  return el("footer", { class: "creditos" }, botonTema());
}

// ── tema claro u oscuro ─────────────────────────────────────────────────

function temaGuardado() {
  try {
    return localStorage.getItem(CLAVE_TEMA);
  } catch {
    return null;
  }
}

function aplicarTema(tema) {
  if (tema) document.documentElement.dataset.theme = tema;
  else delete document.documentElement.dataset.theme;
}

function botonTema() {
  const oscuro = (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
  const boton = el("button", { type: "button", class: "boton enlace" }, oscuro ? "Tema claro" : "Tema oscuro");
  boton.addEventListener("click", () => {
    const tema = oscuro ? "light" : "dark";
    try {
      localStorage.setItem(CLAVE_TEMA, tema);
    } catch {
      /* sin almacenamiento, el tema dura lo que la página */
    }
    aplicarTema(tema);
    boton.replaceWith(botonTema());
  });
  return boton;
}

aplicarTema(temaGuardado());
