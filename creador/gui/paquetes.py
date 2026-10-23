"""Pantalla del gestor de paquetes: ver, importar (.zip o carpeta) y quitar paquetes de contenido."""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..entorno import paquetes_instalados
from ..gestor import ErrorInstalacion, directorio_usuario, es_integrado, instalar, quitar
from .componentes import fuente, texto_ajustado, titulo

ETIQUETAS_TIPO = {"oficial": "Oficial", "propio": "Del programa", "homebrew": "Homebrew"}


def abrir_carpeta(ruta: Path) -> None:
    """Abre la carpeta en el explorador del sistema."""
    if sys.platform.startswith("win"):
        os.startfile(ruta)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(ruta)])


class PantallaPaquetes(ctk.CTkFrame):
    def __init__(self, master, al_volver: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.al_volver = al_volver
        titulo(self, "Paquetes de contenido", 24).pack(anchor="w", padx=30, pady=(26, 4))
        texto_ajustado(self, "Los paquetes traen razas, clases, trasfondos, conjuros, preguntas… Los integrados vienen con "
                             "el programa; los tuyos (homebrew o expansiones) se importan desde un .zip o una carpeta y se "
                             "validan antes de instalarse. Para usarlos, márcalos en la pantalla de inicio.", 860,
                       text_color="gray").pack(anchor="w", padx=30)
        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(anchor="w", padx=30, pady=14)
        ctk.CTkButton(botones, text="Importar .zip…", width=150, command=self.importar_zip).pack(side="left")
        ctk.CTkButton(botones, text="Importar carpeta…", width=160, command=self.importar_carpeta).pack(side="left", padx=10)
        ctk.CTkButton(botones, text="Abrir carpeta de paquetes", width=200, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.abrir).pack(side="left")
        ctk.CTkButton(botones, text="← Volver al inicio", width=150, fg_color="transparent",
                      text_color=("gray10", "gray90"), command=al_volver).pack(side="left", padx=10)
        self.lista = ctk.CTkScrollableFrame(self)
        self.lista.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self.refrescar()

    def refrescar(self) -> None:
        for hijo in self.lista.winfo_children():
            hijo.destroy()
        disponibles, avisos = paquetes_instalados()
        for aviso in avisos:
            texto_ajustado(self.lista, f"Aviso: {aviso}", 840, text_color=("#b45309", "#fbbf24")).pack(anchor="w", pady=2)
        ordenados = sorted(disponibles.values(), key=lambda i: (not es_integrado(i), i.sistema, i.nombre))
        for info in ordenados:
            self._tarjeta(info, disponibles)

    def _tarjeta(self, info, disponibles) -> None:
        caja = ctk.CTkFrame(self.lista)
        caja.pack(fill="x", pady=4, padx=2)
        integrado = es_integrado(info)
        cabecera = ctk.CTkFrame(caja, fg_color="transparent")
        cabecera.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(cabecera, text=info.nombre, font=fuente(14, True), anchor="w").pack(side="left")
        if not integrado:
            ctk.CTkButton(cabecera, text="Quitar", width=80, fg_color="transparent", border_width=1,
                          text_color=("#b91c1c", "#f87171"), command=lambda: self.quitar(info)).pack(side="right")
        origen = "Integrado" if integrado else "Instalado por ti"
        partes = [info.id, f"versión {info.version}", ETIQUETAS_TIPO.get(info.tipo, info.tipo), origen]
        ctk.CTkLabel(caja, text="  ·  ".join(partes), text_color="gray", anchor="w").pack(anchor="w", padx=12)
        detalle = info.descripcion
        if info.depende_de:
            nombres = [disponibles[d].nombre if d in disponibles else f"{d} (¡no instalado!)" for d in info.depende_de]
            detalle += f"  Necesita: {', '.join(nombres)}."
        if not integrado:
            detalle += f"  Carpeta: {info.ruta}"
        texto_ajustado(caja, detalle, 840).pack(anchor="w", padx=12, pady=(2, 10))

    def _instalar(self, origen: str) -> None:
        try:
            instalado = instalar(Path(origen))
        except ErrorInstalacion as exc:
            if "ya está instalado" in str(exc) and messagebox.askyesno("Ya instalado", f"{exc}\n\n¿Reemplazarlo?"):
                try:
                    instalado = instalar(Path(origen), reemplazar=True)
                except ErrorInstalacion as otro:
                    messagebox.showerror("No se ha instalado", str(otro))
                    return
            else:
                if "ya está instalado" not in str(exc):
                    messagebox.showerror("No se ha instalado", str(exc))
                return
        accion = "actualizado" if instalado.reemplazado else "instalado"
        messagebox.showinfo("Paquete " + accion, f"«{instalado.info.nombre}» {accion}.\n\nMárcalo en la pantalla de "
                                                 "inicio para usarlo.")
        self.refrescar()

    def importar_zip(self) -> None:
        ruta = filedialog.askopenfilename(filetypes=[("Paquete comprimido", "*.zip")])
        if ruta:
            self._instalar(ruta)

    def importar_carpeta(self) -> None:
        ruta = filedialog.askdirectory(title="Carpeta del paquete (la que contiene paquete.json)")
        if ruta:
            self._instalar(ruta)

    def quitar(self, info) -> None:
        if not messagebox.askyesno("Quitar paquete", f"¿Quitar «{info.nombre}»? Se borra su carpeta:\n{info.ruta}"):
            return
        try:
            quitar(info.id)
        except ErrorInstalacion as exc:
            messagebox.showerror("No se ha quitado", str(exc))
            return
        self.refrescar()

    def abrir(self) -> None:
        try:
            abrir_carpeta(directorio_usuario())
        except (ErrorInstalacion, OSError) as exc:
            messagebox.showerror("No se puede abrir", str(exc))
