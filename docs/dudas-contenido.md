# Dudas de contenido pendientes de revisar

Lo que los agentes no pudieron confirmar con una fuente oficial. El SRD 5.1 en español sí se usó; el Manual del Jugador aún no estaba disponible. Revísalo con el libro y marca lo que se corrija.

## Equipo e idiomas

222 entradas. Escrito con un script Python que vuelca con json.dump (UTF-8, indentación de 2, ensure_ascii=False). El script está en /tmp/claude-0/equipo/generar.py y no queda nada suelto en el repositorio. Los datos se han comprobado contra el PDF del SRD ES con pdftotext -layout, porque las tablas del .txt salen desordenadas. También se han cotejado con el SRD inglés (precios, pesos, daños).

- **Nombre del idioma élfico** (`idioma_elfico_nombre`): En la tabla y en los rasgos raciales, el SRD ES llama al idioma «Elfo» (y a su escritura también «Elfo»), así que el id elfico lleva el nombre «Elfo». El paquete de prueba usa «Élfico», que probablemente es la forma del PHB ES (sin verificar). En la ficha puede confundirse con la raza. Si se prefiere «Élfico», habría que cambiarlo con "modifica" desde phb-2014 una vez confirmada la traducción del PHB.
- **Ids de armaduras distintos de los ejemplos de la documentación** (`ids_armaduras_vs_docs`): docs/formato-paquetes.md y el paquete de prueba usan «cota_de_mallas» y «cuero»/«armadura_de_cuero». El SRD ES dice «Cota de malla», así que el id es cota_de_malla, y la armadura de cuero es armadura_de_cuero. Los agentes de clases y trasfondos tienen que usar estos ids; si ponen cota_de_mallas, el validador dará «no existe en objetos».
- **Nombres largos de armaduras ligeras y de pieles** (`nombres_armaduras`): La tabla del SRD usa nombres cortos («Acolchada», «Cuero», «Cuero tachonado», «Pieles»). He usado la forma larga, que el propio SRD también emplea en su texto y en el equipo de clase: «Armadura acolchada», «Armadura de cuero», «Armadura de cuero tachonado» y «Armadura de pieles». Así se entienden en la ficha.
- **No hay objeto genérico «símbolo sagrado» ni «canalizador»** (`focos_sin_generico`): Solo existen las variantes del SRD: canalizador_arcano_{baston,cristal,orbe,vara,varita}, canalizador_druidico_{baston_de_madera,rama_de_muerdago,totem,varita_de_tejo} y simbolo_sagrado_{amuleto,emblema,relicario}. Para «un símbolo sagrado» o «un canalizador arcano», clases y trasfondos deben usar {"desde": "objetos", "filtro": {"categoria": "foco", "subcategoria": "sagrado"}} (o arcano o druidico). Comprobado con opciones_desde: funciona.
- **Escudo de madera del druida** (`escudo_de_madera`): El SRD no lo trata como un objeto distinto; mecánicamente es un escudo. No he creado escudo_de_madera: el agente del druida debería usar «escudo».
- **Útiles para disfrazarse y para falsificar** (`disfraz_falsificar_categoria`): En el PDF del SRD ES aparecen sangrados dentro de «Herramientas de artesano». Parece una errata de maquetación: en el SRD inglés son herramientas independientes y en el orden alfabético español deberían ir fuera del grupo. Los he puesto con subcategoria «kit», como pedía el encargo.
- **Id de los útiles de herborista** (`herborista_id`): El encargo daba «utiles_de_herbolario» como ejemplo de id, pero el SRD ES dice «Útiles de herborista» (también en la competencia del druida). He usado utiles_de_herborista para que coincida con el nombre. Si algún agente usa utiles_de_herbolario, tendrá un error de referencia.
- **Objetos de paquetes y del Acólito que no tienen precio en el SRD** (`objetos_sin_precio_duplicados`): He creado en srd-5.1/objetos.json los objetos caja_para_limosnas, incensario, incienso («Barra de incienso»), vestiduras, devocionario, rueda_de_oraciones, bolsita_de_arena, cuchillo_pequeno y cordel («Cordel (3 m)»), sin coste ni peso. Los necesitaba para el contenido exacto de los paquetes, y el Acólito usa los cuatro primeros más ropas_comunes y bolsa. Si el agente de trasfondos crea los mismos ids en su archivo, tendrá un error de id duplicado (objetos.json se carga antes) y deberá quitar los suyos.
- **Unidad de la munición** (`municion_unidad`): Siguiendo el ejemplo de docs ({"id": "flecha", "cantidad": 20}), la unidad del inventario es una pieza: flecha, virote («Virote de ballesta»), bala_de_honda y dardo_de_cerbatana. «coste» y «peso» se copian tal cual del lote del SRD (p. ej. 1 po y 0,5 kg por 20 flechas), con el tamaño del lote en el campo nuevo «lote». Un cálculo futuro de precio o carga tendrá que dividir por «lote». En cambio, abrojos (bolsa de 20), bolas de metal (bolsa de 1000) y pinchos de hierro (10) son un único objeto-lote, como en el nombre del SRD.
- **Nombres españoles de los juegos del PHB** (`phb_juegos_nombres`): «Apuesta de los Tres Dragones» aparece en el texto del SRD ES (descripción de Juegos), así que es casi seguro. «Ajedrez de dragones» está sin verificar contra el PHB ES 2014. El peso «250 g» del ajedrez sale de convertir ½ lb con la convención del SRD ES (poción, saco y espejito pesan ½ lb y figuran como 250 g); también sin verificar. Precio de ambos: 1 po (PHB inglés).
- **Objetos propios de los trasfondos del PHB** (`phb_objetos_trasfondos`): No he añadido los objetos sueltos que dan los trasfondos del PHB (trofeos, insignias de rango, cartas de presentación, mapa de la ciudad natal, ratón mascota, amuletos de la suerte, etc.): no están en el capítulo de equipo y es más fácil que los cree quien escriba esos trasfondos. Los objetos genéricos ya existen en srd-5.1: ropas_comunes, ropas_de_calidad, ropas_de_viaje, disfraz, bolsa, pala, olla_de_hierro, tinta, pluma, palanqueta, trampa_para_cazar, cuerda_de_seda, manta, anillo_de_sellar, perfume y otros.
- **Metros en nombres de objetos** (`longitudes_en_nombres`): Los nombres del SRD con longitudes se dejan tal cual, en metros: «Cuerda de cáñamo (15 m)», «Cadena (3 m)», «Escalera (3 m)», «Vara (3 m)» y «Cordel (3 m)», igual que los pesos en kg. Las distancias de reglas en las descripciones y los alcances de armas sí van en pies. Si se quiere todo en pies, habría que renombrarlos (50 pies, 10 pies).
- **Valores de idioma fuera de la documentación** (`idioma_tipo_secreto_escritura`): docs/formato-paquetes.md solo menciona "tipo": estandar/exotico; "secreto" lo pide el encargo y el validador no lo comprueba. Habla de las profundidades lleva "escritura": "—", tal cual en el SRD (no tiene escritura). Druídico y jerga de ladrones no llevan «escritura». Los campos extra «escritura», «hablantes» y «dialectos» no los usa el motor.
- **Nombre de las ropas de disfraz** (`nombre_disfraz`): El SRD lo escribe «Ropas, disfraz». Lo he mantenido como nombre, con id disfraz (el Paquete de artista dice «2 disfraces»). En la ficha se verá «Ropas, disfraz (x2)».

**Limitaciones del motor señaladas:**

- Red: no hace daño, pero el validador exige «dano» y «tipo_dano» y el motor suma el modificador. Está modelada con "dano": "—" y "tipo_dano": "—", así que la ficha muestra un ataque «—+3 —». Las reglas reales (apresar, Fuerza CD 10, un solo ataque) van en la descripción.
- Dardo: es un arma a distancia con «sutil». Para cualquier arma de tipo "distancia", el motor usa siempre DES y no elige FUE aunque sea mayor.
- Estas propiedades son solo informativas y el motor no las aplica: pesada (desventaja de las criaturas Pequeñas), recarga, gran alcance, a dos manos, ligera (combate con dos armas), especial (desventaja de la lanza de caballería a 5 pies, a dos manos si no se va montado) y munición (gasto y recuperación).
- Armas arrojadizas cuerpo a cuerpo (daga, hacha de mano, jabalina, lanza, martillo ligero, tridente): el motor da una sola línea de ataque con la característica de cuerpo a cuerpo y añade «Alcance X/Y pies» en las notas. Es correcto por reglas, pero no hay una línea aparte para el ataque a distancia.
- Paquetes de equipo: el motor no expande «contenido». Si se añade un paquete al inventario, aparece como un solo objeto («Paquete de ladrón»); el desglose habrá que hacerlo en la interfaz o al crear el personaje.
- El motor no usa los campos de munición «lote», «armas» ni «tipo_municion» de las armas: no hay control de munición ni comprobación de que el arma tenga munición.
- «coste» y «peso» son texto: no se calcula la carga, ni la penalización por peso, ni el gasto de dinero.
- Consumibles y objetos con reglas (ácido, aceite, fuego de alquimista, agua bendita, abrojos, bolas de metal, poción de curación, veneno básico, antitoxina, útiles de sanador, palanqueta, lupa, ariete, etc.) solo tienen descripción: no generan ataques, tiradas ni efectos en la ficha.
- Focos: el motor no relaciona el canalizador con el lanzamiento de conjuros (componentes materiales); son objetos informativos.

## Conjuros 0

26 entradas. Están escritos los 26 trucos (nivel 0) del Manual del Jugador 2014 que aparecen en las listas de bardo, brujo, clérigo, druida, hechicero y mago. Explorador y paladín no tienen trucos en el PHB 2014. Todos están en la categoría «conjuros».

- **Traducción oficial de Blade Ward (PHB 2014)** (`guardia_de_cuchillas`): He usado «Guardia de cuchillas», pero no he podido comprobarlo en el Manual del Jugador. Lo respalda una lista en español de trucos de hechicero (shadowlands.es, de hacia 2020, es decir, anterior al PHB 2024). Esa lista tiene los 16 trucos del PHB 2014 y todos los nombres del SRD coinciden con los oficiales. AideDD y un foro que compara 2014 y 2024 usan el mismo nombre. Algunas traducciones de aficionados lo llaman «Protección contra armas». Si alguien tiene el PHB en español, conviene confirmarlo; el id no cambiaría aunque cambie el nombre.
- **Traducción oficial de Friends (PHB 2014)** (`amistad`): He usado «Amistad». Aparece en la misma lista en español anterior a 2024 y en AideDD. Tengo bastante seguridad, pero no lo he comprobado en el libro.
- **Componente material de Amistad** (`amistad_componentes`): El texto del componente material, «S, M (un poco de maquillaje que te aplicas en la cara al lanzarlo)», está redactado con palabras propias porque el PHB tiene derechos protegidos. No es la redacción oficial.
- **Página del PHB en «fuente»** (`fuente_phb`): En las dos entradas del PHB he puesto «fuente»: «PHB 2014», sin página. No he podido confirmar las páginas de la edición española; en la inglesa son la p. 218 (Blade Ward) y la p. 244 (Friends).
- **Texto del SRD mal ordenado en Creación y Crear llama (aviso para quien escriba conjuros de nivel 5)** (`srd_creacion_crear_llama`): En fuentes/SRD_5.1_ES.txt, hacia la línea 18664, las dos columnas de la p. 143 salen mezcladas. Parece que «Creación» tiene «Conjuración (truco)», 1 acción y alcance Lanzador, y que «Crear llama» dura 1 minuto. Con la página del PDF renderizada he comprobado lo correcto. Creación: Ilusionismo nivel 5, 1 minuto, 9 m, V, S, M, duración Especial. Crear llama: Conjuración (truco), 1 acción, Lanzador, V, S, 10 minutos. Los datos de Crear llama ya van bien.

**Limitaciones del motor señaladas:**

- El motor no calcula nada de un conjuro: solo usa id, nombre, nivel, escuela y listas, para filtrar y avisar. El daño de los trucos que escala con el nivel de personaje (5, 11, 17) queda como texto fijo en «resumen». El campo «resumen» de los conjuros no admite {expresiones}, que solo se procesan en los rasgos.
- Shillelagh: el ataque cuerpo a cuerpo con la característica de lanzamiento y el d8 de daño no se reflejan en los ataques de la ficha. Solo están descritos en el resumen.
- Guardia de cuchillas (resistencia a daño contundente, cortante y perforante de ataques con armas durante 1 asalto) y los demás efectos temporales de los trucos no se pueden modelar como efectos de la ficha. Van solo en el texto.

## Conjuros 1

62 entradas. Están escritos los 62 conjuros de nivel 1 del Manual del Jugador 2014 de las listas de bardo, brujo, clérigo, druida, explorador, hechicero, mago y paladín.

- **Traducción oficial de los 13 conjuros que solo están en el PHB (sin verificar)** (`nombres_phb_2014`): No pude confirmar los nombres de la edición española de 2014. He usado los de la traducción oficial de 2024 que publica aidedd.org/spell/es/. Comprobé que en 21 conjuros del SRD esa traducción coincide exactamente con los nombres del SRD 5.1 en español, así que parece seguir el mismo glosario. Bastante seguros: Armadura de Agathys, Brazos de Hadar, Orbe cromático, Maleficio, Castigo abrasador y Castigo atronador. Dudosos, con la alternativa posible de 2014 entre paréntesis: Duelo forzado (¿Duelo obligado?), Susurros discordantes (¿Susurros disonantes?), Golpe apresador, Tormenta de espinas (¿Granizo de espinas o Lluvia de espinas?), Rayo nauseabundo, Rayo de hechicería (¿Rayo de bruja o Descarga de bruja?) y Castigo furioso (¿Castigo colérico o iracundo?). Si se corrige un nombre, el id se mantiene.
- **Ids que otros archivos deben usar** (`ids_para_otros_agentes`): Hoy ningún otro archivo hace referencia a conjuros de nivel 1; lo comprobé recorriendo todos los JSON. Cuando los escriban, los conjuros de subclase deben usar estos ids exactos. Ejemplos: golpe_apresador (Juramento de los Antiguos), susurros_discordantes (Gran Antiguo), perdicion y marca_del_cazador (Juramento de Venganza), risa_horrible (no risa_horrible_de_tasha), disco_flotante (no disco_flotante_de_tenser), reprension_infernal (tiflin), enmaranar, proteccion_contra_el_bien_y_el_mal y orden_imperiosa.
- **Volúmenes, pesos y distancias largas** (`unidades_no_distancia`): Las distancias van en pies. El volumen y el peso del SRD se dejan en métrico con la equivalencia del PHB entre paréntesis: «40 litros (10 galones)» en Crear o destruir agua y «250 kg (500 libras)» en Disco flotante. Los 1,5 km de la alarma mental de Alarma quedan como «1 milla», como en el PHB.
- **Páginas del PHB** (`fuente_phb_sin_pagina`): En los conjuros del PHB la fuente es solo «PHB 2014», sin número de página, igual que hizo el agente de conjuros_0. No conozco con seguridad la paginación de la edición española.

**Limitaciones del motor señaladas:**

- El motor solo usa de cada conjuro el nombre, el nivel, la escuela y las listas. No muestra ni calcula tiempo, alcance, componentes, duración, ritual, concentración ni resumen, y el validador tampoco comprueba de qué tipo son esos campos. Son datos para mostrar al jugador.
- El aumento con el nivel del espacio (más daño, más objetivos, más duración en Maleficio o Marca del cazador) solo está en el texto del resumen; el motor no lo calcula.
- Lanzar como ritual (por ejemplo, un mago que lanza rituales de su libro sin tenerlos preparados) no está modelado; el campo ritual solo informa.

## Conjuros 2

59 entradas. Categoría «conjuros», todos de nivel 2, 59 entradas en total.

- **Nombre oficial de Beast Sense (sin verificar)** (`sentidos_de_bestia`): No he podido confirmar la traducción del Manual del Jugador 2014. El conjuro no existe en el PHB 2024, así que aidedd.org no tiene página en español y las búsquedas no dan ninguna fuente fiable. He usado «Sentidos de bestia» por analogía con «Sentidos Divinos» (Divine Sense), que es como traduce el SRD español. Si el nombre oficial es otro, basta cambiar «nombre»; el id no debe cambiar.
- **Nombre oficial de Crown of Madness** (`corona_de_la_locura`): aidedd.org en español, que sigue la traducción del PHB 2024, lo llama «Corona de la locura», y ese nombre he usado. No he podido comprobar si el PHB español de 2014 decía lo mismo o «Corona de locura».
- **Fuerza fantasmal, Nube de dagas y Cordón de flechas** (`nombres_phb_verificados_2024`): Los tres nombres aparecen en aidedd.org en español (traducción del PHB 2024). Lo más probable es que coincidan con el PHB español de 2014, pero no lo he comprobado contra ese libro.
- **Componentes materiales de los conjuros solo del PHB** (`componentes_phb`): Los he escrito con palabras propias: Nube de dagas «una esquirla de cristal», Cordón de flechas «cuatro o más flechas o virotes», Fuerza fantasmal «un poco de vellón». Esta última es la misma expresión que usa el SRD en Ilusión menor.
- **Errata del SRD en los componentes** (`agrandar_reducir`): El SRD español pone «una pizca hierro en polvo», sin «de». En los datos he escrito «una pizca de hierro en polvo».
- **Ids de nombres con barra** (`ids_con_barra`): «Agrandar/reducir» tiene el id agrandar_reducir y «Sordera/ceguera» el id sordera_ceguera. Los agentes de subclases tienen que usar estos ids exactos. Sordera/ceguera aparece, por ejemplo, en la lista ampliada del Infernal del brujo.
- **Unidades en los resúmenes** (`unidades_no_metricas`): Además de pasar metros a pies (300 m = 1.000 pies, 90 m = 300 pies), he pasado las distancias largas a millas: 7,5 km = 5 millas, 1,5 km = 1 milla, 75 y 37,5 km = 50 y 25 millas. El peso de Levitar va en libras (250 kg = 500 libras). Lo he hecho por coherencia con la regla de pies; si se prefieren unidades métricas en el texto, solo hay que tocar el resumen.

**Limitaciones del motor señaladas:**

- Los conjuros son datos de catálogo y de listas: el motor no aplica sus efectos. Daño, salvaciones, escalado a niveles superiores, los PG extra de Auxilio, la CA mínima 16 de Piel robliza, la visión en la oscuridad del conjuro, la velocidad trepando de Trepar cual arácnido o las opciones de Alterar el propio aspecto solo figuran en el «resumen».
- El campo «ritual» se guarda, pero el motor no gestiona el lanzamiento ritual (por ejemplo, el mago que lanza rituales desde su libro sin prepararlos).
- En «listas» solo van ids de clase. Las listas ampliadas de los patrones del brujo y los conjuros de dominio, juramento o círculo se dan desde las subclases (conjuros_adicionales y efectos «conjuro» con siempre_preparado); eso lo escriben otros agentes con los ids de este archivo.

## Conjuros 3

50 entradas. He escrito los 50 conjuros de nivel 3 del PHB 2014 que están en las listas de bardo, brujo, clérigo, druida, explorador, hechicero, mago y paladín. Todas las entradas llevan id, nombre, nivel, escuela, listas, tiempo, alcance (en pies), componentes, duración, ritual, concentración, resumen y fuente.

- **herramientas/verificar_srd.py lee mal tres listas de clase** (`verificador_srd_falsos_positivos`): En SRD_5.1_ES_pypdf.txt, pypdf parte tres líneas de las listas de conjuros: «T»/«error» (líneas 9998-9999, bardo), «L»/«uz del día» y «Nu»/«be apestosa» (líneas 10495-10498, hechicero). Por eso verificar_srd.py da 3 discrepancias que no son reales: Luz del día sin hechicero, Nube apestosa sin hechicero y Terror sin bardo. Las páginas 111 y 116 del PDF, que he mirado renderizadas, y la extracción de pdftotext confirman que los tres conjuros sí están en esas listas, igual que en el PHB. He dejado los datos correctos, así que test_contraste_con_el_srd_oficial dará esos 3 fallos hasta que alguien arregle el lector (por ejemplo, uniendo una línea de 1 o 2 letras con la siguiente). No lo he tocado porque no es archivo mío. A nivel 4 hay más líneas partidas («D»/«estierro», «G»/«uardián de la fe», «M»/«architar»), pero ahí la herramienta no comprueba nada.
- **Traducción de Lightning Arrow (sin verificar)** (`nombre_flecha_relampagueante`): He usado «Flecha relampagueante» (id flecha_relampagueante), que creo que es la del PHB español de 2018. No lo he podido confirmar; la alternativa sería «Flecha de relámpago».
- **Traducción de Feign Death (sin verificar)** (`nombre_fingir_muerte`): He usado «Fingir muerte» (id fingir_muerte). Es bastante probable, pero no lo he podido confirmar con el PHB español.
- **Traducciones de Crusader's Mantle y Conjure Barrage (sin verificar del todo)** (`nombres_paladin_explorador`): He usado «Manto del cruzado» y «Conjurar andanada», que creo que son las oficiales del PHB español. De «Aura de vitalidad», «Castigo cegador», «Arma elemental» y «Hambre de Hadar» estoy razonablemente seguro. Si alguno cambiara, el id se mantiene igual.
- **Alcances que no se pasan bien a pies** (`alcance_millas`): En Clarividencia (1,5 km en el SRD) he puesto alcance «1 milla», como en el original inglés, en vez de «5.280 pies». En Recado he dejado «Ilimitado». En los resúmenes también aparecen millas, libras y galones (media milla en Crecimiento vegetal, 10/13 millas por hora en Corcel fantasma, 45 libras y 30 galones en Crear comida y agua), con las unidades del PHB en lugar de km, kg y litros.
- **Componentes materiales de los conjuros del PHB** (`componentes_phb`): Los componentes materiales de los 8 conjuros del PHB están descritos con palabras propias: tierra de cementerio, tentáculo de pulpo encurtido, munición o arma arrojadiza. Pueden no coincidir al pie de la letra con el texto del PHB español.
- **Ids que usarán otros archivos** (`referencias_futuras`): Los archivos de clases todavía estaban vacíos, así que no hay referencias que comprobar. Los conjuros de dominio y círculo a nivel 5 y los conjuros ampliados del brujo deben usar estos ids tal cual: manto_del_cruzado y espiritus_guardianes (Guerra), senal_de_esperanza y revivir (Vida), luz_del_dia y bola_de_fuego (Luz), crecimiento_vegetal y muro_de_viento (Naturaleza), llamar_al_relampago y tormenta_de_aguanieve (Tempestad), desplazamiento y disipar_magia (Superchería), indetectable y hablar_con_los_muertos (Conocimiento). También caminar_sobre_el_agua, fundirse_con_la_piedra, respirar_bajo_el_agua, proteccion_contra_energia, patron_hipnotico, nube_apestosa, forma_gaseosa, acelerar, ralentizar, relampago, clarividencia y recado.

**Limitaciones del motor señaladas:**

- Los conjuros son solo datos de catálogo: el motor no calcula daño, curación ni CD por conjuro. La mejora «A niveles superiores» va solo en el texto del «resumen», porque no hay un campo para ella.
- Crecimiento vegetal tiene dos tiempos de lanzamiento con efectos distintos («1 acción u 8 horas»). Lo he puesto como texto en «tiempo» y explicado en el resumen.
- Los campos «ritual» y «concentracion» son informativos: el motor no los usa (no hay lanzamiento como ritual ni control de concentración).

## Guía del DM (2014)

Opciones de personaje escritas desde el texto oficial (paquete `dmg-2014`): aasimar, eladrín, Dominio de la Muerte y Rompejuramentos, hasta nivel 5. Los nombres de conjuros que citan coinciden con los de nuestros datos.

Reglas de la Guía que afectan a la ficha y **aún no están en el motor** (no las usa la campaña; se pueden añadir como reglas opcionales):

- Equipo inicial al empezar por encima de nivel 1 (tabla «Equipo inicial», p. 38): a niveles 1-4, equipo normal; a niveles 5-10, 500 po + 1d10 × 25 po y equipo normal (más un objeto mágico infrecuente en campañas con mucha magia). Se usará en el asistente de creación (paso 3).
- Dados de competencia en lugar del bonificador por competencia.
- Competencia en trasfondo (sin competencias en habilidades ni herramientas).
- Puntos de héroe (5 + mitad del nivel).
- Características nuevas: Honor y Cordura.
- Puntos de conjuro en lugar de espacios.
- Los conjuros del PHB que no aparecen en la Guía (25 de 28) siguen sin confirmar; solo se confirman «Amistad», «Rayo nauseabundo» y «Corona de la locura».
