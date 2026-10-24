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

Opciones de personaje escritas desde el texto oficial (paquete `dmg-2014`): aasimar, eladrín, Dominio de la Muerte y Rompejuramentos (estos dos, hasta nivel 20). Los nombres de conjuros que citan coinciden con los de nuestros datos.

Reglas de la Guía que afectan a la ficha y **aún no están en el motor** (no las usa la campaña; se pueden añadir como reglas opcionales):

- Equipo inicial al empezar por encima de nivel 1 (tabla «Equipo inicial», p. 38): a niveles 1-4, equipo normal; a niveles 5-10, 500 po + 1d10 × 25 po y equipo normal (más un objeto mágico infrecuente en campañas con mucha magia). Se usará en el asistente de creación (paso 3).
- Dados de competencia en lugar del bonificador por competencia.
- Competencia en trasfondo (sin competencias en habilidades ni herramientas).
- Puntos de héroe (5 + mitad del nivel).
- Características nuevas: Honor y Cordura.
- Puntos de conjuro en lugar de espacios.
- Los conjuros del PHB que no aparecen en la Guía (25 de 28) siguen sin confirmar; solo se confirman «Amistad», «Rayo nauseabundo» y «Corona de la locura».

# Segunda tanda (razas, trasfondos, dotes y clases)

## Razas

30 entradas.

- **Traducción oficial de las subrazas y rasgos del PHB (sin verificar)** (`nombres_phb_razas`): Los nombres de las subrazas son los más probables del Manual del Jugador en español: Enano de las montañas, Elfo de los bosques, Elfo oscuro (drow), Mediano fornido, Gnomo de los bosques y Humano variante. Los de los rasgos también: Máscara de la Naturaleza, Sensibilidad a la Luz Solar, Magia Drow, Resistencia de los Fornidos, Ilusionista Nato y Hablar con Bestias Pequeñas. No he podido comprobar ninguno contra el libro. Hay alternativas posibles, como «Máscara de lo Salvaje» o «Sensibilidad a la Luz del Sol». Si se corrige un nombre, el id se mantiene.
- **Dragón de latón: «oropel» en el SRD ES** (`draconido_oropel`): La tabla de Linaje Dracónico del SRD ES llama «Oropel» al dragón de latón (brass). He mantenido el id fijado, draconido_laton, pero el nombre es «Dracónido (oropel)» para seguir el SRD. Si se prefiere «latón», basta cambiar el nombre.
- **Nombre de la subraza humano_estandar** (`nombre_humano_estandar`): El SRD no tiene subraza para el humano. He llamado «Humano» a humano_estandar para que en la ficha aparezca «Humano», no «Humano estándar». En el selector se verán «Humano» y «Humano variante». Si se prefiere «Humano (estándar)», solo hay que cambiar el nombre.
- **¿Debe el humano variante llevar permiso_dm?** (`humano_variante_permiso`): El PHB presenta el humano variante como opción para campañas con dotes que el DM puede permitir. Por la definición de la guía encajaría con "permiso_dm": true, pero no lo he puesto: el encargo no lo pedía y la interfaz aún no usa ese campo. Su descripción lo menciona. Queda por decidir si se marca o si basta con depender de la regla opcional «dotes».
- **Forma de los ids de subraza** (`ids_subrazas`): He usado ids que siguen el nombre completo: enano_de_las_colinas, alto_elfo, mediano_piesligeros, gnomo_de_las_rocas, enano_de_las_montanas, elfo_de_los_bosques, elfo_oscuro, mediano_fornido y gnomo_de_los_bosques. El ejemplo de docs/formato-paquetes.md y el paquete de prueba usan enano_colinas y elfo_alto. Ahora mismo ningún archivo real hace referencia a ids de subraza. El eladrín de dmg-2014 apunta a la raza elfo y ya valida.
- **Tiefling o tiflin** (`tiefling_nombre`): El SRD ES dice «Tiefling» y el id fijado es tiefling, así que el nombre es «Tiefling». En la documentación, el ejemplo y el paquete de prueba usan «tiflin», que probablemente es la forma de una traducción anterior del PHB (sin verificar). No toca ningún dato real.
- **Idiomas que se pueden elegir como idioma adicional** (`idioma_extra_secretos`): La elección del idioma adicional del humano, el alto elfo y el semielfo excluye druídico y jerga de ladrones: el filtro es tipo estándar o exótico, igual que el del Acólito. El texto dice «de tu elección», pero esos idiomas son secretos de clase. Es una interpretación.
- **Perfiles del cuestionario** (`perfiles_razas`): Los perfiles son criterio mío. Algunos ejemplos: enano de las colinas {aguante 1, fe 1}, pensando en el clérigo enano clásico; humano {carisma 2, combate 1, saber 1, astucia 1}, sin ningún 3 por ser versátil. Al sumar raza y subraza, alguna puntuación llega a 4 (aguante del enano de las colinas). El validador lo permite porque cada entrada por separado no pasa de 3.

**Limitaciones del motor señaladas:**

- Las ventajas y desventajas condicionales solo están en el texto del rasgo: Resistencia Enana y Resistencia de los Fornidos (salvaciones contra veneno), Linaje Feérico, Valiente, Astucia Gnoma y Sensibilidad a la Luz Solar.
- Afinidad con la Piedra y Saber del Artífice son una pericia en Historia solo en ciertas pruebas, y no hay efecto para eso. El rasgo muestra el total calculado: +{mod_int+2*competencia}.
- Afortunado, Aguante Incansable (con usos 1 y recarga larga), Ataques Salvajes, Agilidad de Mediano, Sigiloso por Naturaleza, Máscara de la Naturaleza, Trance, Manitas y Hablar con Bestias Pequeñas son solo texto.
- El efecto «conjuro» no tiene usos, recarga ni nivel de lanzamiento. Reprensión infernal como conjuro de nivel 2, fuego feérico y oscuridad «1 vez por descanso largo» van en rasgos aparte con usos, recarga y nivel_minimo; su CD (8 + competencia + mod_car) está en el resumen, porque conjuros_innatos no la muestra.
- El filtro de opciones no admite negación. La elección del idioma adicional ofrece también los idiomas que ya se conocen (Común, Elfo…); si se elige uno repetido, se pierde sin aviso.
- El humano variante ofrece la elección de dote aunque personaje.reglas_opcionales['dotes'] sea False: el motor solo comprueba esa regla en la Mejora de característica.
- El Ataque de Aliento no aparece como «ataque» de la ficha, porque es un área con salvación. Va como rasgo con el daño y la CD calculados.
- Tamaño Pequeño (mediano, gnomo): el motor no aplica la desventaja con armas pesadas.
- ficha.resistencias muestra ids sin tildes (relampago, frio, acido); los nombres tendrá que ponerlos la interfaz.

## Trasfondos

30 entradas.

- **Nombre oficial del trasfondo Sage** (`nombre_sabio_erudito`): He puesto el nombre «Erudito» manteniendo el id sabio. La Guía del DM 2014 en español (fuentes/privado, cap. 9, «Crear un trasfondo») dice: «muy similar al erudito» y «el rasgo Investigador del erudito (como se muestra en el Player's Handbook)». Es la misma línea editorial que el PHB español, así que «Erudito» parece la traducción de 2014; «Sabio» es la de 2024. Sin verificar contra el PHB. Si se confirma «Sabio», solo hay que cambiar el «nombre».
- **Nombres de los rasgos de trasfondo del PHB (sin verificar)** (`rasgos_trasfondo_nombres`): «Investigador» está confirmado por la Guía del DM española. Bastante probables: Identidad falsa, Contacto criminal, Hospitalidad rústica, Descubrimiento, Posición privilegiada, Rango militar, Secretos de la ciudad y Mala reputación. Dudosos, con la alternativa posible: «A petición del público» (By Popular Demand; ¿Por aclamación popular?), «Miembro del gremio» (Guild Membership; ¿Pertenencia al gremio?), «Trotamundos» (Wanderer; ¿Errante/Viajero?), «Pasaje en barco» (Ship's Passage; ¿Pasaje marítimo?) y «Séquito» (Retainers; ¿Sirvientes/Criados?). Las búsquedas web no dieron ninguna fuente española fiable.
- **Nombres de trasfondos y variantes** (`nombres_trasfondos_variantes`): He usado Charlatán, Artista, Héroe del pueblo, Artesano gremial, Ermitaño, Forastero y Huérfano, y las variantes Espía, Gladiador, Mercader gremial, Caballero y Pirata. Son los más extendidos, pero no los he podido comprobar en el PHB español. Una fuente web sugería «Embaucador» para Charlatan, sin respaldo. Los nombres de las tablas (especialidades, rutinas, orígenes, negocios del gremio) son traducción propia.
- **Nombre del rasgo del Acólito** (`refugio_del_fiel`): He usado «Refugio del Fiel», que es el nombre del SRD 5.1 español (la regla pide los nombres del SRD). Es probable que el PHB español de 2014 dijera «Refugio de los fieles».
- **Filtro de idiomas de los trasfondos** (`idiomas_secretos_excluidos`): Las elecciones de idiomas usan el filtro {"tipo": ["estandar", "exotico"]}, que deja fuera druídico y jerga de ladrones (rasgos de clase). El PHB permite exóticos y, con permiso del DM, también secretos; si se quiere eso, basta con quitar el filtro. Un idioma de homebrew sin «tipo» tampoco saldría en la lista.
- **Objetos creados en phb-2014/trasfondos.json** (`objetos_nuevos_en_trasfondos`): Los 17 objetos propios de los trasfondos los he puesto en la categoría «objetos» de mi propio archivo, porque el agente de equipo dejó dicho que no los había creado. Si alguien añade luego los mismos ids en objetos.json, habrá un error de id duplicado y habrá que quitar uno. Ids: botella_con_liquido_de_colores, dados_trucados, naipes_marcados, anillo_de_un_duque_imaginario, ropas_oscuras_con_capucha, prenda_de_un_admirador, carta_de_presentacion_del_gremio, estuche_con_notas, pergamino_de_linaje, trofeo_de_caza, carta_de_un_colega_fallecido, amuleto_de_la_suerte, insignia_de_rango, trofeo_de_un_enemigo_caido, mapa_de_la_ciudad_natal, raton_mascota y recuerdo_de_tus_padres. No tienen coste ni peso, porque el PHB no se los da.
- **Equipo modelado con objetos genéricos** (`equipo_aproximado`): La cabilla del marinero es «garrote», como dice el PHB (belaying pin = club). La «manta de invierno» del ermitaño es «manta», los «dados de hueso» del soldado son «dados» y el traje del artista es «disfraz» («Ropas, disfraz»). El ermitaño recibe 5 po sin bolsa, como en el PHB.
- **Formato de «tablas» y «variantes»** (`formato_tablas_variantes`): «tablas» es un objeto {clave: [textos]}, con claves sin tildes (engano_favorito, especialidad, rutinas, suceso_decisivo, negocio_del_gremio, vida_de_retiro, origen). «variantes» es una lista de {id, nombre, descripcion}, más un «rasgo» {nombre, resumen, descripcion} cuando la variante cambia el rasgo (caballero y pirata). El validador no comprueba ninguno de los dos campos. Noble, marinero y huérfano no tienen tabla propia en el PHB, así que no llevan «tablas».

**Limitaciones del motor señaladas:**

- Variantes no elegibles: el motor no puede cambiar el rasgo de un trasfondo por el de su variante (Séquito del caballero, Mala reputación del pirata) ni las competencias del mercader gremial (herramientas de navegante o un idioma). Las variantes van solo como texto en «variantes»; la ficha muestra siempre el rasgo estándar.
- Competencia repetida: la regla de que, si recibes la misma competencia de dos fuentes, eliges otra del mismo tipo no está modelada. La elección de idiomas tampoco excluye los que el personaje ya conoce.
- Equipo y competencia no están ligados: las herramientas de artesano o el instrumento que se eligen en «equipo» no tienen por qué coincidir con los que se eligen como competencia.
- El motor no usa «equipo», «monedas», «tablas», «variantes» ni «personalidad» del trasfondo: solo valida los ids del equipo. Llevar el equipo y el dinero al inventario, tirar en las tablas o elegir rasgos de personalidad le toca a la interfaz.
- Los rasgos de trasfondo son puramente narrativos (alojamiento gratis, contactos, viajar al doble de rápido por la ciudad, encontrar comida para 6 personas, etc.): van como efecto «rasgo» con resumen, sin ningún cálculo.

## Dotes

42 entradas.

- **Traducción oficial de las dotes del PHB 2014** (`nombres_dotes_sin_verificar`): Sin el PHB ES 2014 no he podido confirmar los nombres. He usado como referencia la traducción oficial de 2024 (aidedd.org/feat/es) cuando la dote existe en las dos ediciones. Sin verificar, con alternativas: Atacante a la Carga (¿«Cargador»?), Combatiente con Dos Armas, Explorador de Mazmorras (no existe en 2024), Resistente (Durable; ¿«Robusto»?), Adepto Elemental (en 2024 «Versado en un elemento»; creo que en 2014 era «Adepto elemental»), Maestro en Armas Pesadas (¿«Maestro en armas grandes»?), Muy Acorazado (¿«Fuertemente acorazado»?), Ligeramente Acorazado, Moderadamente Acorazado, Lingüista (no existe en 2024), Azote de Magos (¿«Asesino de magos» o «Matamagos»?), Tirador de Primera, Matón de Taberna y Lanzador en Combate (¿«Lanzador de guerra»?). Francotirador de Conjuros es el nombre que daba el encargo; en 2024 es «Lanzador preciso». Bastante seguros, porque coinciden con 2024 y con el uso habitual: Acechador, Actor, Adepto Marcial, Afortunado, Alerta, Atacante Salvaje, Atleta, Centinela, Combatiente Montado, Duelista Defensivo, Duro, Experto en Ballestas, Habilidoso, Iniciado en la Magia, Lanzador Ritual, Líder Inspirador, Maestro de Armas, Maestro en Armaduras Medias, Maestro en Armaduras Pesadas, Maestro en Armas de Asta, Maestro en Escudos, Mente Aguda, Móvil, Observador, Resiliente y Sanador. Si se corrige un nombre, el id se mantiene.
- **Mayúsculas de los nombres** (`mayusculas_dotes`): Pongo mayúscula en las palabras principales («Maestro en Armaduras Medias», «Atacante a la Carga»), siguiendo los ejemplos del encargo («Iniciado en la Magia», «Francotirador de Conjuros», «Adepto Marcial») y el estilo de los rasgos del SRD. La traducción de 2024 y el paquete de prueba escriben solo la inicial en mayúscula («Iniciado en la magia»). Si se prefiere así, basta con cambiar «nombre».
- **Truco Látigo de espinas (Thorn Whip) ausente en conjuros_0** (`latigo_de_espinas_falta`): Thorn Whip es un truco de druida del PHB 2014 (p. 282, con tirada de ataque), pero no está en srd-5.1 ni en phb-2014/conjuros_0.json: el agente de trucos escribió 26 y el PHB tiene 27. El filtro de Francotirador de Conjuros ya incluye el id latigo_de_espinas, así que funcionará en cuanto se añada con ese id. Si se usa otro, hay que cambiarlo en TRUCOS_DE_ATAQUE (/tmp/claude-0/dotes/generar.py) o en el JSON. Por ahora un druida solo puede elegir Crear llama. El nombre «Látigo de espinas» está sin verificar.
- **Francotirador de Conjuros: bardo y clérigo** (`francotirador_sin_bardo_clerigo`): La dote permite las listas de bardo, brujo, clérigo, druida, hechicero y mago. En el PHB 2014 ni el bardo ni el clérigo tienen trucos con tirada de ataque: Burla dañina y Llama sagrada piden salvación. Para no ofrecer elecciones vacías, la elección de clase solo da brujo, druida, hechicero y mago; la descripción menciona las seis listas. Si otro paquete añade trucos de ataque a esas listas, hay que ampliar las opciones y la lista de ids.
- **Adepto Marcial depende de las maniobras** (`maniobras_otro_agente`): La elección usa {"desde": "opciones", "filtro": {"grupo": "maniobra"}}. Hoy no hay ninguna opción con ese grupo, porque las clases aún están vacías, y la ficha avisa de que la elección no tiene opciones. Quien escriba las maniobras debería redactar sus resúmenes sin dar por hecho el d8 ni la escala del Maestro de Batalla: con Adepto Marcial el dado es d6 y la CD es 8 + competencia + FUE o DES, que ya muestra el rasgo de la dote.
- **Maestro en Armas de Asta y la lanza** (`armas_de_asta_lanza`): He incluido la lanza tanto en el ataque adicional con el otro extremo como en el ataque de oportunidad, y el mismo modificador que el ataque principal. Así lo dice la fe de erratas del PHB (2018) y D&D Beyond. Si la edición española impresa es anterior a esa errata, su texto solo nombraría guja, alabarda y bastón (y pica en el segundo punto).
- **Habilidoso: lista fija de herramientas** (`habilidoso_lista_estatica`): Para permitir cualquier combinación sin repetir en una sola elección, las 57 opciones (18 habilidades y 39 herramientas de srd-5.1 y phb-2014) se generan con el script como objetos con efectos. Las herramientas que añadan después otros paquetes no saldrán hasta volver a ejecutar /tmp/claude-0/dotes/generar.py.
- **Lingüista sin idiomas secretos** (`linguista_idiomas_secretos`): La elección filtra por «tipo» estandar o exotico, así que deja fuera el druídico y la jerga de ladrones, que no se aprenden por la vía normal. Es una interpretación razonada; el texto de la dote dice solo «tres idiomas a tu elección».
- **Errores de dmg-2014** (`dmg_errores_ajenos`): «validar srd-5.1 phb-2014 dmg-2014» da 3 errores: la raza elfo y las clases clerigo y paladin no existen todavía, porque los archivos de clases y razas siguen vacíos. No afectan a las dotes; ninguna referencia mía depende de entradas ajenas, salvo las maniobras ya mencionadas.

**Limitaciones del motor señaladas:**

- Combatiente con Dos Armas: el +1 a la CA con un arma cuerpo a cuerpo en cada mano no se puede modelar, porque no hay ninguna condición de empuñar dos armas. Queda solo en el texto.
- Maestro en Armaduras Medias: está modelado el máximo de DES 3. La ficha sigue marcando desventaja en Sigilo con armaduras medias que la imponen, porque el motor no permite anular «desventaja_sigilo».
- Maestro en Armaduras Pesadas: la reducción de 3 al daño contundente, cortante y perforante de armas no mágicas no es una resistencia y no existe un efecto de reducción de daño. Queda solo en el texto.
- Explorador de Mazmorras: la resistencia al daño de trampas no corresponde a un tipo de daño, así que no puede ir como efecto «resistencia». Las ventajas también quedan en el texto.
- Matón de Taberna: no hay id ni grupo de competencia para armas improvisadas, así que esa competencia queda en el texto. El ataque sin armas de 1d4 sí está modelado. Un monje con esta dote verá dos líneas de ataque sin armas.
- Lanzador Ritual: no existe un indicador de «solo como ritual». Los dos conjuros salen como conjuros innatos con su característica, el libro de rituales no se añade al equipo y no se modela copiar más rituales.
- Iniciado en la Magia: el «1 vez por descanso largo» del conjuro de nivel 1 aparece como usos 1 y recarga larga en el rasgo de la dote, sin relación directa con el conjuro.
- Adepto Marcial: el dado de superioridad d6 no se suma a los dados del Maestro de Batalla. Es un rasgo aparte con usos 1 y recarga corta.
- Francotirador de Conjuros: los conjuros no tienen un campo que diga si exigen tirada de ataque. Se filtra con una lista explícita de ids, y el alcance doble y la cobertura quedan en el texto.
- Lingüista: la CD de los cifrados usa la puntuación de INT, que no es una variable de expresión. El resumen dice «tu puntuación de INT + {competencia}».
- El motor no impide tomar la misma dote en dos Mejoras de Característica. Solo Adepto Elemental se puede repetir, y con un tipo de daño distinto cada vez, cosa que tampoco se comprueba.
- Los prerrequisitos se comprueban con las puntuaciones y competencias finales, incluidas las que dan dotes posteriores, y solo generan avisos.
- Alerta (no te sorprenden), Afortunado, Duelista Defensivo, Centinela, Tirador de Primera, Maestro en Armas Pesadas (−5/+10), Maestro en Escudos, Sanador, Líder Inspirador, Resistente y las demás ventajas situacionales, reacciones y acciones adicionales solo están en el resumen y la descripción, con números calculados cuando se puede.

## Bárbaro+guerrero

31 entradas.

- **Nombres de rasgos del SRD distintos de los del encargo** (`nombres_srd_vs_encargo`): El encargo decía «Sentido del Peligro» y «Ataque Extra», pero el SRD 5.1 en español (pp. 8-9 y 35) dice «Sentir el Peligro» y «Ataque Adicional», en las dos clases. He usado los nombres del SRD, como manda la guía de contenido.
- **Oro inicial: no está en el SRD y el del bárbaro no es 5d4x10** (`oro_inicial_phb`): La tabla de riqueza inicial por clase solo está en el PHB; he buscado «5d4», «riqueza inicial» y «oro inicial» en el SRD ES sin resultado. Por eso el oro_inicial va en phb-2014 con «modifica»: true. Con solo srd-5.1 cargado, las clases no tienen oro inicial. Los valores son los del PHB 2014: bárbaro 2d4x10 (no 5d4x10, que era el ejemplo del encargo) y guerrero 5d4x10. Si se prefiere tener todo en srd-5.1, basta con mover el campo, pero ya no sería «solo SRD». Conviene que los demás agentes de clases sigan el mismo criterio.
- **Traducción de la Senda del Guerrero Totémico (sin verificar)** (`nombres_phb_barbaro`): Sin el PHB ES 2014 no he podido confirmar estos nombres: «Senda del Guerrero Totémico» (Path of the Totem Warrior), «Buscador Espiritual» (Spirit Seeker), «Espíritu Tótem» (Totem Spirit) y los animales Oso, Águila y Lobo. Las alternativas posibles son «Buscador de Espíritus» y «Espíritu Totémico». Los ids no cambian aunque se corrijan los nombres.
- **Traducción del Maestro de Batalla y del Caballero Arcano (sin verificar)** (`nombres_phb_guerrero`): «Maestro de Batalla» y «Caballero Arcano» venían en el encargo. Sin verificar: «Superioridad en Combate» (Combat Superiority), «Estudiante de la Guerra» (Student of War; ¿«Estudioso de la Guerra»?) y «Vínculo con un Arma» (Weapon Bond; ¿«Vínculo con el Arma»?).
- **Nombres de las 16 maniobras (sin verificar)** (`nombres_maniobras`): Traducciones propias, sin confirmar con el PHB ES 2014:
- Ataque Amenazador (Menacing Attack)
- Ataque con Estocada (Lunging Attack)
- Ataque con Finta (Feinting Attack)
- Ataque de Barrido (Sweeping Attack)
- Ataque de Derribo (Trip Attack)
- Ataque de Empuje (Pushing Attack)
- Ataque de Maniobra (Maneuvering Attack)
- Ataque de Precisión (Precision Attack)
- Ataque Desarmante (Disarming Attack)
- Ataque Provocador (Goading Attack)
- Contraataque (Riposte; ¿«Réplica»?)
- Golpe del Comandante (Commander's Strike)
- Golpe Distractor (Distracting Strike; ¿«Golpe de Distracción»?)
- Juego de Pies Evasivo (Evasive Footwork)
- Parada (Parry)
- Reagrupar (Rally; ¿«Arenga»?)
Los ids no cambian aunque cambien los nombres.
- **Nombres de opciones con prefijo** (`prefijos_opciones`): He seguido la convención del paquete de prueba: los estilos se llaman «Estilo de Combate: Defensa», etc., y las maniobras «Maniobra: Parada», etc. Ese nombre sale en la lista de la elección y como rasgo en la ficha. Los ids no llevan prefijo: defensa, tiro_con_arco, duelo, combate_con_armas_a_dos_manos, combate_con_dos_armas, proteccion, parada, contraataque… Los agentes del paladín y del explorador deben filtrar por {"grupo": "estilo_combate", "clases": "paladin"} o "explorador"; está comprobado que dan los 4 estilos correctos.
- **Sin rasgo «Senda Primordial» ni «Arquetipo Marcial»** (`sin_rasgo_eleccion_subclase`): No he añadido un rasgo para el momento de elegir la subclase a nivel 3: la subclase se elige con EntradaClase.subclase (nivel_subclase 3) y su nombre ya aparece en «clase_y_nivel». Si los demás agentes ponen ese rasgo en sus clases, habría que añadirlo aquí por coherencia.
- **Rasgos solo hasta nivel 5** (`alcance_niveles`): Según el encargo, solo hay rasgos hasta nivel 5 y la única mejora de característica es la de nivel 4. Faltan las mejoras de los niveles 8, 12, 16 y 19 del bárbaro y de los 6, 8, 12, 14, 16 y 19 del guerrero, además de los rasgos de nivel 6 en adelante. Lo que escala más allá de nivel 5 dentro de rasgos que ya existen sí está completo: furias y daño por furia, Ataque Adicional, Acción Súbita, dados de superioridad y tablas de lanzamiento del Caballero Arcano.
- **Errores de dmg-2014 que no son míos** (`dmg_clerigo_paladin`): «validar srd-5.1 phb-2014 dmg-2014» da 2 errores: las subclases dominio_de_la_muerte y rompejuramentos apuntan a las clases clerigo y paladin, que aún no existen porque clases_clerigo_paladin.json sigue vacío ({}). Por lo mismo falla test_paquetes_sin_errores. Desaparecerán cuando el agente de clérigo y paladín escriba su archivo.

**Limitaciones del motor señaladas:**

- Furia: no hay ninguna condición «en furia», así que el daño extra, la resistencia a daño contundente, cortante y perforante y la ventaja en FUE solo están en el resumen del rasgo; no se aplican como efectos.
- Furia a nivel 20: «usos» solo admite un número entero, así que no puede decir «ilimitadas». Desde nivel 17 la ficha muestra 6 usos; lo de nivel 20 solo está en la descripción.
- Espíritu Tótem (Oso, Águila y Lobo): todo depende de estar en furia, así que va solo como rasgo de texto. La resistencia a todo salvo el daño psíquico no se puede modelar como efecto.
- Ataque Temerario, Sentir el Peligro, Frenesí (incluido el nivel de cansancio) y Acción Súbita: ventajas y acciones que el motor no calcula; van como rasgos con usos y recarga cuando los tienen.
- Estilos Duelo, Combate con Armas a Dos Manos, Combate con Dos Armas y Protección: el motor no tiene bonificador de daño por cómo se empuña el arma ni repeticiones de dados, así que van solo en texto. Defensa (bonificador_ca con con_armadura) y Tiro con Arco (bonificador_ataque a distancia) sí se aplican.
- Tiro con Arco: el +2 solo afecta a armas de tipo «distancia». Las armas arrojadizas cuerpo a cuerpo lanzadas (jabalina, daga, hacha de mano) no lo reciben en la ficha.
- Crítico Mejorado: el motor no tiene rango de crítico en los ataques; solo es texto.
- Ataque Adicional: el número de ataques solo aparece en el resumen. Que no se sume entre clases en un multiclase solo queda en la descripción.
- Maestro de Batalla: los dados de superioridad son los usos del rasgo (4/5/6, recarga corta) y el tamaño del dado va con escala. Las maniobras que se aprenden a niveles 7, 10 y 15 y el cambio de maniobras no están modelados (fuera del alcance 1-5).
- Caballero Arcano: el motor no comprueba la restricción de escuela (abjuración o evocación salvo uno de los tres conjuros iniciales y los de niveles 8, 14 y 20) y acepta cualquier conjuro de mago; la regla va en el texto. Los trucos sí pueden ser de cualquier escuela.
- Buscador Espiritual: los conjuros sentidos_de_bestia y hablar_con_los_animales salen como innatos; que solo se puedan lanzar como ritual va solo en el texto.
- Vínculo con un Arma: solo texto.
- Defensa sin Armadura en un multiclase con monje: el motor usa la mejor ca_alternativa. Es razonable, aunque las reglas dicen que el rasgo no se obtiene dos veces.

## Bardo+pícaro

9 entradas.

- **Nombre del rasgo de nivel 2 del bardo** (`bardo_aprendiz_de_mucho_vs_polivalente`): El encargo lo llama «Polivalente», pero el SRD 5.1 oficial en español dice «Aprendiz de Mucho» (tabla «El bardo» y título de la sección, p. 11-12). La guía manda usar el nombre exacto del SRD para el contenido del SRD, así que he puesto «Aprendiz de Mucho». «Polivalente» podría ser la traducción del Manual del Jugador de 2014 (sin verificar). Si se prefiere ese nombre, solo hay que cambiar el «nombre» del rasgo, sin tocar ids.
- **Tabla de trucos del Embaucador Arcano** (`embaucador_trucos_mano_de_mago`): El PHB da 3 trucos conocidos (4 a nivel 10), y uno de ellos es obligatoriamente mano de mago. El motor solo usa trucos_conocidos como límite de los trucos que elige el jugador, y mano de mago se concede aparte como siempre preparado. Por eso la tabla dice 2 (3 a nivel 10): así el total sale 3 y 4, como en el libro. Si el jugador mete también mano_de_mago entre sus conjuros elegidos, el motor avisa de que sobra un truco, y eso es correcto. Si se prefiere copiar la tabla del libro tal cual (3/4), habría que quitar el efecto siempre_preparado y dejar que el jugador elija mano de mago a mano.
- **Traducción oficial de rasgos solo del PHB** (`phb_nombres_rasgos_sin_verificar`): «Colegio del Valor» y «Embaucador Arcano» están confirmados en la Guía del DM en español. Los nombres de algunos rasgos no los he podido confirmar y son los más probables (sin verificar): «Inspiración en Combate» (Combat Inspiration); «Competencias Adicionales» para Valor y Asesino (Bonus Proficiencies; es el mismo nombre que usa el SRD para el Colegio del Conocimiento); «Asesinar» (Assassinate); y sobre todo «Juego de Manos con Mano de Mago» (Mage Hand Legerdemain), del que tengo menos certeza. También podría ser algo como «Prestidigitación con mano de mago».
- **Páginas del PHB** (`fuente_paginas_phb`): Las subclases del PHB llevan "fuente": "PHB 2014" sin número de página, igual que las del bárbaro y el guerrero, porque no tengo el PHB en español para confirmar la paginación.

**Limitaciones del motor señaladas:**

- Inspiración Bárdica pasa de recargarse con descanso largo a recargarse también con descanso corto a nivel 5 (Fuente de Inspiración), pero el motor no puede cambiar la «recarga» de un rasgo según el nivel ni quitar un rasgo a partir de un nivel: no existe nivel_clase_maximo ni recarga con escala. Lo he modelado con rasgos por nivel. Inspiración Bárdica (nivel 1) lleva recarga «largo» y su resumen avisa del cambio a nivel 5. Fuente de Inspiración (nivel 5) es un rasgo aparte que lo explica. A nivel 5 o más la ficha sigue mostrando «recarga: largo» en Inspiración Bárdica. Una solución sería permitir «recarga» como escala ({"1": "largo", "5": "corto"}) o un campo nivel_clase_maximo.
- Pericia (del bardo y del pícaro) debería ofrecer solo las competencias que ya tiene el personaje, pero el filtro de elecciones no puede depender de ellas. Ofrece todas las habilidades (y las herramientas de ladrón en el pícaro), y el motor avisa «Pericia en … sin tener competencia» si se elige mal.
- Embaucador Arcano: la restricción de escuela (los conjuros de nivel 1 o más deben ser de encantamiento o ilusión, salvo 1 de los 3 iniciales y los de los niveles 8, 14 y 20) no se puede comprobar. Va solo en el texto del rasgo.
- Embaucador Arcano: mano de mago se concede con un efecto conjuro con clase picaro y siempre_preparado. No hay forma de declarar un truco conocido obligatorio que cuente dentro de la tabla de trucos (ver dudas).
- Balconero: «trepar no te cuesta movimiento adicional» no es exactamente una velocidad trepando y el efecto velocidad no admite expresiones (igual a caminar). Queda en el texto. El salto extra se muestra calculado ({mod_des} pies).
- Inspiración en Combate, Palabras Cortantes, Asesinar, Acción Astuta, Esquiva Asombrosa, Ataque Furtivo, Manos Rápidas y Jerga de Ladrones son reglas situacionales. Van como rasgos con resumen calculado (escalas de dados, CD y ataque), sin más efecto mecánico posible.

## Clérigo+paladín

12 entradas.

- **Nombres de las subclases del PHB (sin verificar)** (`nombres_phb_subclases`): No tengo el PHB 2014 en español para confirmar estos nombres: Dominio del Conocimiento, Dominio de la Luz, Dominio de la Naturaleza, Dominio de la Tempestad, Dominio de la Guerra, Juramento de los Antiguos y Juramento de Venganza. Trickery va como «Dominio de la Superchería», como pedía la tarea (id dominio_de_la_supercheria); otra traducción posible es «Dominio del Engaño», que choca con la habilidad Engaño.
- **Nombres de los rasgos del PHB (sin verificar)** (`nombres_phb_rasgos`): Están traducidos de memoria, con las mayúsculas del SRD: Bendiciones del Conocimiento; Conocimiento de las Eras; Truco Adicional; Destello Protector; Resplandor del Alba (Radiance of the Dawn); Acólito de la Naturaleza; Hechizar Animales y Plantas; Competencias Adicionales; Ira de la Tormenta; Ira Destructiva; Bendición del Embaucador; Invocar Duplicidad; Sacerdote de Guerra; Golpe Guiado; Ira de la Naturaleza; Expulsar a los Infieles; Abjurar Enemigo; Voto de Enemistad. Todos van precedidos de «Canalizar Divinidad: » cuando corresponde. Hay que revisarlos cuando esté el PHB.
- **La tarea usa nombres que difieren del SRD en español** (`nombres_srd_vs_tarea`): Usé los nombres del SRD en español: «Sentidos Divinos» (la tarea decía Sentido Divino), «Ataque Adicional» (decía Ataque Extra) y «Juramento de Entrega», con id juramento_de_entrega (decía Devoción). Si se prefiere otro id para el juramento, hay que decidirlo antes de que algo lo referencie; hoy no lo referencia nada.
- **CD de Ira de la Tormenta** (`cd_ira_tormenta`): El PHB no indica la CD de la salvación de DES. Usé la CD de conjuros de clérigo ({8+competencia+mod_sab}), que es lo que recuerdo de la Sage Advice; no lo he podido comprobar.
- **Truco de druida del Acólito de la Naturaleza** (`truco_acolito_naturaleza`): Lo modelé como conjuro siempre preparado del clérigo (se lanza con SAB), igual que el Segador del Dominio de la Muerte de dmg-2014. Recuerdo que la Sage Advice dice que cuenta como conjuro de clérigo, pero no lo he podido comprobar.
- **Páginas del PHB** (`fuente_phb_paginas`): Las subclases del PHB llevan «fuente»: «PHB 2014» sin página, igual que las del agente bárbaro/guerrero, porque no puedo confirmar la paginación española. Las del SRD sí llevan página, comprobada en el PDF: clérigo p. 21, Vida p. 23, paladín p. 48, Entrega p. 51.

**Limitaciones del motor señaladas:**

- Equipo inicial del clérigo: el SRD pone el martillo de guerra y la cota de malla con «(si eres competente)». El formato de equipo no admite esa condición, así que esas alternativas se ofrecen siempre.
- Salud Divina: la inmunidad a enfermedades usa el efecto «inmunidad» con id «enfermedades». La enfermedad no es una condición ni un tipo de daño, así que el id es libre y la ficha lo muestra tal cual.
- Canalizar Divinidad en multiclase clérigo/paladín: cada clase muestra su propio rasgo con usos. Por las reglas, los usos no se suman, y el motor no tiene reserva compartida. Las opciones de cada dominio o juramento salen como rasgos sin usos; los usos se cuentan en el rasgo general «Canalizar Divinidad».
- Truco Adicional (luz, Dominio de la Luz): el motor no puede comprobar «si no lo conocías ya». Si el jugador también elige luz como truco, aparece dos veces y no hay aviso.
- Efectos situacionales o activables que quedan solo en el texto del rasgo: Discípulo de la Vida, Preservar Vida, Castigo Divino, Arma Sagrada (bonificador temporal), Destello Protector, Ira de la Tormenta, Ira Destructiva, Sacerdote de Guerra (ataque extra), Golpe Guiado (+10), Voto de Enemistad, Abjurar Enemigo, Ataque Adicional (número de ataques) y la competencia temporal de Conocimiento de las Eras.
- Imponer las Manos: la reserva aparece solo en el resumen ({nivel_clase*5}); el motor no lleva la cuenta de una reserva de puntos gastables.
- Elecciones de idiomas (Bendiciones del Conocimiento): el motor ofrece también idiomas que el personaje ya conoce y no avisa si se repiten.

## Druida+explorador

41 entradas (35 en srd-5.1, 6 en phb-2014).

- **Nombres del SRD frente al encargo**: el SRD ES dice «Percepción Primigenia», «Ataque Adicional» y «El Cazador y la Presa»; se usan esos.
- **Oro inicial**: no está en el SRD; va en phb-2014 con «modifica» (druida 2d4x10, explorador 5d4x10).
- **Nombres del PHB sin verificar**: Círculo de la Luna, Forma Salvaje de Combate, Formas del Círculo, Señor de las Bestias, Compañero del Explorador.
- **Infraoscuridad o Underdark**: la Guía del DM ES usa «Underdark (Infraoscuridad en español)»; se usa «Infraoscuridad». El terreno Infraoscuridad (Explorador Nato y Círculo de la Tierra) solo está en el PHB y sus conjuros van de memoria.
- **Idioma del enemigo predilecto**: bestias y cienos no dan idioma; el resto elige entre estándar y exóticos.
- **Rasgo «Armaduras y escudos no metálicos»**: nombre propio para mostrar la restricción del druida.
- **Errata del Compañero del Explorador (2018)**: no incluida (no se sabe si la edición española la recoge).
- **Grupos de opciones nuevos**: terreno_del_circulo y presa_del_cazador.

**Limitaciones del motor señaladas:**

- Forma Salvaje no sustituye la ficha por la de la bestia.
- No se comprueba que el druida no lleve armadura de metal.
- Ventajas de Enemigo Predilecto y la competencia doble de Explorador Nato solo en texto.
- Conjuros de círculo de niveles 7 y 9 solo en la descripción (los conjuros de nivel 4-5 no existen aún).
- Sin efecto propio: la bestia compañera, el +1d8 de Azote de Colosos, Ataque Adicional y las elecciones de niveles 6, 10 y 14.

## Hechicero+brujo

52 entradas (47 en srd-5.1: 2 clases, 2 subclases, 8 metamagias, 32 invocaciones y 3 pactos; 5 en phb-2014).

- **Oro inicial** (`oro_inicial`): el SRD no trae la tabla de riqueza inicial; va en phb-2014 con «modifica» (3d4x10 hechicero, 4d4x10 brujo). Clérigo y paladín lo pusieron en srd-5.1: hay que unificar.
- **Nombres del SRD frente al encargo**: el SRD ES dice «Magia del Pacto», «Beneficio del Pacto» y «Pacto del Grimorio». El PHB ES podría decir «Don del pacto» y «Pacto del tomo» (sin verificar).
- **Linaje Dracónico**: el SRD ES llama «Resistencia Dracónica» a Draconic Resilience.
- **Traducciones sin verificar**: «Magia Salvaje», «Oleada de Magia Salvaje», «Mareas del Caos» (¿«Mareas de caos»?), «El Archihada», «Presencia Feérica», «El Primigenio», «Mente Despierta».
- **Conjuros de nivel 4-5 de los patrones**: aún no existen; solo en texto. Ids sugeridos para cuando existan: escudo_de_fuego, muro_de_fuego, consagrar, golpe_flamigero, dominar_bestia, invisibilidad_mejorada, dominar_persona, apariencia, tentaculos_negros, telequinesis.
- **Invocaciones con conjuros que faltan** (nivel ≥ 4): Cadenas de Carceri, Esbirros del Caos, Escultor de la Carne, Palabra Aterradora, Susurros Embrujados, Visiones de Reinos Remotos; solo texto.
- **Armadura de Sombras**: se modela `ca_alternativa` 13 + DES dando por lanzada la armadura de mago (a voluntad).
- **Opciones solo del PHB**: ninguna; las metamagias, invocaciones y pactos del PHB 2014 están en el SRD 5.1.
- **Errata del SRD ES**: el texto de trucos del hechicero dice «trucos de druida».
- **Vista del Diablo**: sentido propio de 120 pies (ve también en oscuridad mágica).

**Limitaciones del motor señaladas:**

- Los prerrequisitos de las invocaciones no se comprueban (se ofrecen las 32 desde nivel 2); los conjuros que dan llevan `nivel_clase_minimo`.
- La invocación de nivel 5 puede repetir una ya elegida a nivel 2 sin aviso.
- Los conjuros de invocaciones y pactos salen como siempre preparados, sin distinguir a voluntad, 1 vez por descanso o ritual.
- Puntos de hechicería, Lanzamiento Flexible y Metamagia solo en texto; el arma del Pacto del Filo no se calcula como ataque.
- La tabla d100 de Oleada de Magia Salvaje no se incluye (texto protegido del PHB).

## Mago+monje

21 entradas (4 en srd-5.1, 17 en phb-2014).

- **Nombre del rasgo de nivel 5** (`ataque_adicional_nombre`): el SRD ES (p. 46) dice «Ataque Adicional», no «Ataque Extra»; igual que bárbaro y paladín.
- **Traducción del PHB 2014 del mago, sin verificar** (`nombres_phb_mago`): Custodia Arcana, Presagio, Conjuración Menor, Mirada Hipnótica, Ilusión Menor Mejorada, Alquimia Menor, Cosecha Siniestra (¿«Cosecha Macabra»?). Escuelas y «Experto en X» siguen el patrón del SRD.
- **Traducción del PHB 2014 del monje, sin verificar** (`nombres_phb_monje`): Camino de la Sombra, Artes Sombrías (¿«Artes de las Sombras»?), Camino de los Cuatro Elementos, Discípulo de los Elementos y las 8 disciplinas (sobre todo Sintonía Elemental, Acometida de los Espíritus del Vendaval, Moldear el Río Fluyente, Golpe de Ceniza Arrolladora).
- **Látigo de Agua** (`latigo_de_agua_accion_adicional`): acción adicional según la fe de erratas (de memoria).
- **Característica de los conjuros del monje** (`caracteristica_conjuros_monje`): SAB (el PHB no la fija; criterio de Sage Advice).
- **Tope de ki de las disciplinas** (`limite_ki_disciplinas`): no se aplica a Puño del Aire Inquebrantable ni a Látigo de Agua; queda abierto.
- **Recuperación Arcana** (`recuperacion_arcana_dia`): «una vez al día» modelado como 1 uso con recarga larga.
- **Campo `nivel_monje`** en las disciplinas: lo usa el filtro de la elección; para niveles 6, 11 y 17 habrá que añadir disciplinas y filtrar con una lista.
- **Conjuración Menor** (`conjuracion_menor_dano`): «desaparece si recibe o inflige daño», de memoria.

**Limitaciones del motor señaladas:**

- El dado de artes marciales no sustituye al daño de las armas de monje (una daga sigue en 1d4); solo escala el ataque sin armas.
- No se comprueba «empuñar solo armas de monje»; con armadura o escudo no aparece el ataque sin armas normal (1 + FUE).
- El efecto `velocidad` no admite escala: Movimiento sin Armadura suma +10 fijos (el resumen sí escala).
- Costes de ki, acciones adicionales y conjuros de disciplina con ki solo en texto; los conjuros de la Sombra y de las disciplinas salen como innatos con SAB.
- El libro de conjuros del mago se modela (6 + 2 por nivel, con la restricción de niveles; los preparados salen del libro). Siguen sin modelarse los rituales lanzados desde el libro ni copiar conjuros encontrados (50 po y 2 h por nivel).
- No se lleva la cuenta de Custodia Arcana, Presagio ni Recuperación Arcana.
- Ilusión Menor Mejorada: no se modela la alternativa si ya conoces ilusión menor.

## Correcciones hechas al integrar

- **Oro inicial**: la tabla de riqueza por clase no está en el SRD ni en la Guía del DM, así que todo el oro inicial va en `phb-2014`. Corregidos dos valores: mago 4d4 × 10 po (no 5d4 × 10) y monje **5d4 po** (sin × 10).
- **Látigo de espinas**: faltaba (truco del PHB para el druida). Añadido en `phb-2014`; nombre sin verificar.
- **Opciones de clase repetidas** (p. ej. la misma invocación a nivel 2 y 5): ahora el motor avisa.

## Niveles 6 a 20

### SRD (contrastado con el texto oficial)

- **Furia y Forma Salvaje ilimitadas a nivel 20**: «usos» es una tabla por nivel con `null` desde el 20; la ficha deja de mostrar contador.
- **Secretos Mágicos** (bardo 10, 14 y 18): se eligen entre todos los conjuros de cualquier lista hasta el nivel que el bardo puede lanzar en ese momento (5, 7 y 9). Ocupan plazas de conocidos (`cuenta_como_conocido`); los Secretos Mágicos adicionales del Conocimiento (nivel 6, hasta nivel 3) no. Si se elige un truco, también ocupa plaza de conjuro conocido: así lo dice el texto («están incluidos en la columna Conjuros conocidos»).
- **Maestría sobre Conjuros y Conjuros Característicos** (mago 18 y 20): se eligen entre los conjuros de mago de nivel 1, 2 y 3; el programa **no comprueba que estén en el libro** (lo dice el rasgo). Los característicos quedan siempre preparados.
- **Aura de Protección**: se suma a las salvaciones de la ficha del propio paladín; el alcance (10 o 30 pies) va en el resumen.
- **Arcanum Místico**: aparece entre los conjuros siempre preparados del brujo (niveles 6 a 9) aunque sus espacios de pacto no pasen de 5.
- **Explorador**: Paso de la Tierra (nivel 8) se llama igual que el rasgo del Círculo de la Tierra, como en el SRD.

### Manual del Jugador (de memoria; pendiente de revisar con el libro)

- **Nombres de los 13 conjuros de nivel 4-9 solo del PHB** (`nombres_phb_altos`): tomados de la traducción oficial de 2024 que publica aidedd.org/spell/es/, como los de niveles 0-3. Dudosos para la edición de 2014: Enredadera (¿Enredadera apresadora?), Conjurar lluvia de flechas (¿Conjurar andanada?; ojo: el de nivel 3 se llama aquí «Conjurar andanada»), Castigo desterrador, Ola destructora, Puerta arcana (¿Portal arcano?) y Palabra de poder: sanar (aidedd escribe «Palabra de poder sanar»; se ha puesto con dos puntos como «Palabra de poder: matar» del SRD). Si cambia un nombre, el id se mantiene.
- **Nombres de rasgos de subclase del PHB** (`rasgos_phb_altos`): traducidos por mí; los más dudosos: Aspecto de la Bestia, Caminante Espiritual, Sintonía Totémica, Conoce a tu Enemigo, Golpe Sobrenatural, Carga Arcana, Experto en Infiltración, Emboscada Mágica, Embaucador Versátil, Ladrón de Conjuros, Lanzamiento Potente, Destello Mejorado, Amortiguar los Elementos, Golpe del Rayo, Nacido de la Tormenta, Duplicidad Mejorada, Aura de Custodia, Centinela Imperecedero, Campeón Ancestral, Vengador Implacable, Alma de Venganza, Ángel Vengador, Golpe Primigenio, Mil Formas, Entrenamiento Excepcional, Furia Bestial, Compartir Conjuros, Doblegar la Suerte, Caos Controlado, Bombardeo de Conjuros, Escape Brumoso, Defensas Seductoras, Delirio Oscuro, Guarda Entrópica, Escudo Mental, Crear Siervo, Custodia Proyectada, Adivinación Experta, El Tercer Ojo, Transposición Benigna, Invocaciones Duraderas, Encanto Instintivo, Dividir Encantamiento, Ilusiones Maleables, Doble Ilusorio, Realidad Ilusoria, Siervos No Muertos, Acostumbrado a la Muerte, Dominar Muertos Vivientes, Piedra del Transmutador, Maestro Transmutador, Paso de las Sombras, Manto de Sombras y Oportunista.
- **Disciplinas elementales de nivel 6, 11 y 17** (`disciplinas_altas`): nombres traducidos por mí (Garra del Viento del Norte, Gong de la Cumbre, Llamas del Fénix, Postura de Niebla, Cabalgar el Viento, Aliento del Invierno, Defensa de la Montaña Eterna, Río de Llamas Hambrientas, Ola de Tierra Ondulante). Costes de ki de memoria: 3, 3, 4, 4, 4, 6, 5, 5 y 6.
- **Piedra del Transmutador**: la ficha aplica el beneficio elegido al mago, como si la llevara él; si se la da a otro, hay que quitarlo a mano.
- **Siervos No Muertos y Cambiaformas**: el rasgo dice que añadas animar a los muertos o polimorfar al libro; el programa no lo añade solo.
- **Guerrero Totémico**: Aspecto de la Bestia (6) y Sintonía Totémica (14) son elecciones independientes del Espíritu Tótem de nivel 3, como en el libro.

### Guía del DM (desde el texto oficial, p. 96-97)

- **Dominio de la Muerte y Rompejuramentos completos hasta nivel 20.** Nombres tal cual en el texto: Destrucción Inevitable, Golpe Divino, Segador Mejorado, Aura de Odio, Resistencia Sobrenatural y Amo del Pavor.
- **Resistencia Sobrenatural y Avatar de Batalla** (solo contra armas no mágicas) van como rasgo, sin efecto de resistencia: el motor no distingue daño mágico de no mágico y la ficha mostraría una resistencia total.

## Multiclase

- **Requisitos** (FUE o DES 13, INT 13…): se comprueban los de todas las clases, también la inicial, con las puntuaciones finales y solo avisan (decisión de diseño). El reglamento los mira en el momento de añadir la clase; si una mejora posterior es la que permite cumplirlos, el programa no lo detecta.
- **Rasgos que no se acumulan** («no_acumula»): Ataque Adicional, Defensa sin Armadura, Evasión y Esquiva Asombrosa aparecen una sola vez; de Ataque Adicional se queda el que da más ataques. Defensa sin Armadura de bárbaro y monje: la CA usa la mejor de las dos fórmulas, aunque el reglamento dice que no se puede ganar por segunda vez (cuenta solo la de la primera clase que la dio).
- **Canalizar Divinidad** de clérigo y paladín: se muestran los dos rasgos con sus usos; el reglamento dice que al ganarla otra vez se ganan sus opciones, pero no usos adicionales. Revísalo a mano en la ficha.
- **Equipo inicial y salvaciones**: solo los de la clase inicial; de las demás, las competencias de multiclase.
- **Reparto propuesto por el cuestionario**: heurística propia (no es una regla): desde nivel 4, la clase más afín y la siguiente compatible (no más de tres características clave entre las dos) con un tercio de los niveles (1-5), sin dejar a la principal por debajo de su subclase.

## Resuelto después (octubre de 2026)

- **Rasgos solo hasta nivel 5:** todas las clases y subclases llegan a nivel 20.
- **Furia y Forma Salvaje a nivel 20:** `usos` admite tabla por nivel, con `null` = ilimitado.
- **Inspiración Bárdica:** `recarga` por nivel (largo y, desde nivel 5, corto).
- **Pericia sin competencia:** el asistente bloquea esas opciones («sin competencia»).
- **Competencia, idioma o dote repetidos:** los selectores marcan «ya la tienes» y el cuestionario no los elige. Adepto Elemental sí se puede repetir.
- **Conjuros de nivel 4 y 5 de los patrones del brujo:** existen y se dan como efectos.
- **Canalizar Divinidad en multiclase:** reserva compartida (`usos_compartidos`); no se suman usos.
- **Defensa sin Armadura en multiclase:** solo cuenta la de la primera clase que la dio.
- **Maestría sobre Conjuros y Conjuros Característicos:** se avisa si el conjuro no está en el libro. El cuestionario los mete en el libro sin desplazar los recomendados.
- **Siervos No Muertos y Cambiaformas:** añaden su conjuro gratis al libro (`al_libro`).
- **Equipo inicial por encima de nivel 1 (Guía del DM, p. 38):** regla opcional «Oro extra».
- **Entrenarse para subir de nivel (Guía del DM, p. 131):** regla opcional con días y coste por nivel.
- **Multiclase:** regla apagada de serie; nunca a nivel 1.

## Guía de Tasha (paquete `tasha-2020`), fase 1

Escrito desde la traducción de Alvaro1555 que aportó el usuario, con palabras propias.

- **Nombres de las 15 dotes**: en el texto se perdieron los títulos (solo queda la descripción). Los nombres son míos, a partir del inglés y de lo que hace cada una: Adepto Metamágico, Adepto Sobrenatural, Iniciado Artífice, Chef, Cortador (Slasher), Envenenador, Experto en Habilidades, Perforador (Piercer), Pistolero (Gunner), Iniciado en Combate, Telequinético, Telépata, Tocado por las Sombras, Tocado por las Hadas y Aplastador (Crusher). Los ids no cambian si se corrigen.
- **Erratas de la traducción corregidas según el original** (revisar con el libro oficial):
  - Brebaje cáustico de Tasha: a niveles superiores, el daño aumenta 2d4 por nivel; la traducción dice «la sanación aumenta en 1d8».
  - Látigo mental de Tasha: una criatura más por cada nivel por encima de 2; la traducción dice «por encima de 1».
  - Fortaleza intelectual: una criatura más por cada nivel por encima de 3; la traducción dice «nivel 3 o más… por encima de 4».
  - Invocar autómata: el componente es un cofre ornamentado de piedra y metal de 400 po; la traducción repite el relicario de oro de 500 po de Invocar celestial.
- **Perfiles de criatura de los conjuros de invocar**: no se modelan (el resumen remite al libro).
- **Pistolero**: la competencia con armas de fuego va en el texto; no hay armas de fuego en el catálogo.
- **Linaje personalizado**: el programa lo trata como Mediano (el libro deja elegir Pequeño o Mediano).
- **Personalizar tu origen**: solo se modela el cambio de las mejoras de característica de la raza (regla opcional). El cambio de idiomas y de competencias de la raza aún no.
- **Iniciado Artífice**: elige entre toda la lista del artífice (fase 4).

## Guía de Tasha (paquete `tasha-2020`), fase 2: subclases

Escrito desde la misma traducción, con palabras propias. Se añaden por clases; esta lista crece con cada grupo.

- **Nombres de los rasgos**: en el texto se perdieron los títulos (quedan como «Rasgo de X de nivel N»). Solo son del texto los nombres que el propio texto cita (Vínculo Alentador, Vínculo Protector, Santuario Crepuscular, Golpe Divino, Recipiente del Genio…). El resto los he puesto yo a partir del inglés y de lo que hace cada rasgo; por ejemplo: Implemento de Paz, Bálsamo de Paz, Vínculo Expansivo, Ojos de la Noche, Bendición Vigilante, Pasos de la Noche, Sudario Crepuscular, Voz de Autoridad, Exigencia del Orden, Encarnación de la Ley e Ira del Orden. Si se corrigen, los ids de las subclases no cambian.
- **El Insondable**: *invocar elemental* entra en su lista ampliada solo con la forma de agua; el programa no distingue formas y lo añade entero; la descripción de la subclase lo advierte.
- **Dominios del clérigo**: Lanzamiento Potente (Paz) y Golpe Divino (Crepúsculo y Orden) son los mismos rasgos del Manual del Jugador, con el daño de cada dominio. Los conjuros de dominio que no son de la lista del clérigo (Heroísmo, Dormir, Ralentizar…) van siempre preparados como conjuros de clérigo, como en el Manual.
- **Círculos del druida**: nombres míos: Conjuros del Círculo, Infestación Fúngica, Propagación de Esporas, Cuerpo Fúngico, Mapa Estelar, Presagio Cósmico, Constelaciones Titilantes, Lleno de Estrellas, Invocar Espíritu de Fuego Salvaje, Vínculo Mejorado, Llamas Cauterizantes y Renacer Ardiente. Son del texto Halo de Esporas, Entidad Simbiótica y Forma Estrellada.
- **Espíritu de Fuego Salvaje, erratas corregidas según el original** (revisar con el libro oficial): es inmune al daño de fuego (la traducción dice «veneno, psíquico») y su Semilla de Llamas causa daño de fuego (la traducción dice «de fuerza»). El perfil va resumido en la descripción del rasgo; la criatura no se modela.
- **Cuerpo Fúngico**: las inmunidades a estados (cegado, ensordecido, asustado, envenenado) salen en la ficha junto a las de daño.
- **Arquetipos del explorador**: nombres míos: Magia del Guardián del Enjambre, Mano de Enjambre, Marea Retorciente, Enjambre Poderoso, Dispersión del Enjambre, Golpes Terribles, Magia del Vagabundo Feérico, Regalo Feérico, Encanto Sobrenatural, Giro Seductor, Refuerzos Feéricos y Caminante de la Niebla. Es del texto Enjambre Reunido. Invocar feérico (Refuerzos Feéricos, nivel 11) va con los conjuros del arquetipo, sin contar como conocido.
- **Arquetipos del guerrero**: nombres míos: Competencias Adicionales, Escudo Rúnico, Gran Estatura, Maestro de las Runas, Gigante Rúnico, Poder Psiónico, Adepto Telequinético, Mente Protegida, Baluarte de Fuerza y Maestro Telequinético. Son del texto Tallador de Runas, Poder del Gigante, las seis runas y los poderes psiónicos (Campo Protector, Golpe Psiónico, Movimiento Telequinético, Salto Impulsado por Psiónica, Empuje Telequinético). Las runas son opciones de clase (grupo «runa»); las de nivel 7 llevan ese requisito, que el modo sencillo respeta. Los dados de energía psiónica son los usos de Poder Psiónico.
- **Orígenes del hechicero**: nombres míos: Manifestación del Orden, Restablecer el Equilibrio, Bastión de la Ley, Trance del Orden, Cabalgata Mecánica, Habla Telepática, Defensas Psiónicas, Hechicería Psiónica, Revelación en la Carne e Implosión Distorsionante. Son del texto Magia Mecánica y Conjuros Psiónicos. El cambio de un conjuro de origen por otro de las escuelas permitidas al subir de nivel va solo en el texto del rasgo.
- **Mente Aberrante, conjuros psiónicos de nivel 1**: según el original incluyen el truco *astilla mental*; la traducción solo pone *brazos de Hadar* y *susurros discordantes*. Va incluido (revisar con el libro oficial).
- **Tradiciones del mago**: nombres míos: Entrenamiento en Guerra y Canción, Ataque Adicional (como el del Manual), Canción de Defensa, Canción de Victoria, Mente Manifestada, Maestro Escriba y Uno con la Palabra. Son del texto Canción de Espadas, Pluma de Mago y Libro de Conjuros Despertado. El arma de una mano del Canto de la Hoja se elige entre las armas cuerpo a cuerpo sin la propiedad «a dos manos» (sin la lanza de caballería, que solo es de una mano montado).
- **Tradiciones del monje**: nombres míos: Implementos de Misericordia, Toque del Médico, Ráfaga de Curación y Daño, Mano de la Misericordia Suprema, Rostro del Yo Astral, Cuerpo del Yo Astral y Despertar del Yo Astral. Son del texto Mano de Sanación, Mano de Daño, Brazos del Yo Astral y sus partes (Visión Astral, Sabiduría del Espíritu, Palabra del Espíritu, Desviar Energía, Brazos Potenciados, Armadura del Espíritu, Bombardeo Astral). Los rasgos que usan el dado de Artes Marciales llevan su misma escala.
- **Juramentos del paladín**: nombres míos: Aura de Presteza, Defensa Gloriosa, Leyenda Viviente, Aura del Centinela, Reprensión Vigilante y Baluarte Mortal. Son del texto las opciones de Canalizar Divinidad (Atleta Incomparable, Castigo Inspirador, Voluntad del Vigilante, Abjurar lo Extraplanar). Baluarte Mortal: según el original se recupera con un descanso largo o gastando un espacio de nivel 5; la traducción no lo dice (revisar con el libro oficial). El Aura del Centinela suma ya a la iniciativa de la ficha.
- **Arquetipos del pícaro**: nombres míos: Susurros de los Muertos, Recuerdos de los Difuntos, Amigo de la Muerte, Poder Psiónico, Hojas del Alma, Velo Psíquico y Desgarrar la Mente. Son del texto Lamentos de la Tumba, baratija del alma, Paso Fantasma, Espadas Psíquicas y los poderes psiónicos. Lamentos de la Tumba usa la mitad de los dados de Ataque Furtivo (redondeando hacia arriba) como escala.
- **Competencias que la subclase repite**: si una subclase nueva da fija una competencia que el personaje ya había elegido (Perspicacia del Camino de la Misericordia), el modo sencillo cambia la elegida por otra al subir de nivel, como pide la ficha. En el modo normal, la ficha avisa y se cambia a mano.

## Guía de Tasha, fase 3: rasgos de clase opcionales

- **Uno a uno, con la regla**: el libro dice que cada rasgo se toma o se deja por separado. La regla «Rasgos de clase opcionales» los activa todos y en el paso «Clase» se puede quitar cada uno. El modo sencillo, con la regla activa, los usa todos.
- **Nombres míos** (el texto perdió los títulos): Conocimiento Primigenio, Abalanzarse Instintivo, Inspiración Mágica, Versatilidad Bárdica, Versatilidad Sobrenatural, Armonizar Poder Divino, Versatilidad de Truco, Golpes Bendecidos, Compañero Salvaje, Explorador Hábil (Astuto, Errante, Incansable), Enemigo Favorecido, Canalizador Druídico, Conciencia Primigenia, Versatilidad Marcial, Velo de la Naturaleza, Compañero Primigenio, Versatilidad Hechicera, Guía Mágica, Fórmulas de Truco, Arma Dedicada, Ataque Alimentado por Ki, Curación Acelerada, Puntería Enfocada y Puntería Firme; los estilos Lucha a Ciegas, Intercepción, Técnica Superior, Combate con Armas Arrojadizas, Combate sin Armas, Guerrero Druídico y Guerrero Bendito; las maniobras Emboscada, Cambio de Lugar, Contraataque Preparado, Presencia Imponente, Golpe Apresador, Lanzamiento Rápido y Evaluación Táctica; la metamagia Conjuro Transmutado; y las invocaciones Mente Sobrenatural, Escriba Lejano, Don de los Protectores, Investidura del Amo de la Cadena, Protección del Talismán, Reprensión del Talismán, Servidumbre Imperecedera y Vínculo del Talismán. Son del texto Conjuro Buscador y Pacto del Talismán.
- **Fórmulas de Truco (mago, nivel 3)**: en la traducción solo queda el título del rasgo, sin texto; va según el original (tras un descanso largo cambias un truco de mago por otro). Revisar con el libro oficial.
- **Maniobras nuevas**: el libro las abre a cualquiera que tenga maniobras (también con la dote Adepto Marcial); aquí van con el rasgo «Maniobras adicionales» del guerrero, así que un personaje sin niveles de guerrero no las ve.
- **Combate sin Armas**: la ficha muestra el golpe sin armas con 1d8 (sin armas ni escudo en las manos); con arma o escudo es 1d6, como dice el rasgo.
- **Guerrero Druídico y Guerrero Bendito**: los dos trucos se modelan como los de Iniciado en la Magia (con Sabiduría o Carisma), sin ocupar plaza de conocidos.
- **Listas ampliadas**: los conjuros del capítulo 3 de Tasha ya estaban en las listas de sus clases; los del Manual (Orden imperiosa para el bardo, Portal para el brujo…) solo entran con este rasgo. Mano de Bigby es *mano arcana* en este catálogo.

## Guía de Tasha, fase 4: el artífice

- **Sin Xanathar**: la lista de conjuros del artífice es la de Tasha sin los conjuros de la Guía de Xanathar (no están en el catálogo): 19 trucos y 15, 19, 12, 10 y 5 conjuros de niveles 1 a 5. Se añade con entradas `modifica` sobre los conjuros del Manual y de Tasha (`conjuros_artifice.json`). *Mano de Bigby* es *mano arcana* y *Parpadeo* (Blink) es *desplazamiento* en este catálogo.
- **Nombres**: son del texto los rasgos de la tabla de la clase (Alterar Mágicamente, Imbuir Objeto, La Herramienta Adecuada para el Trabajo, Destello de Ingenio, Almacenar Conjuro, Alma del Artificio…), Elixir Experimental, Armadura Arcana, Modelo de Armadura y sus partes (Guanteletes de Trueno, Campo Defensivo, Lanzarrayos, Pasos Potenciados, Campo Amortiguador), Cañón Sobrenatural, Arma de Fuego Arcana, Defensor de Acero, Sacudida Arcana y las infusiones. Son míos, a partir del inglés: Erudito Alquímico, Reactivos Restauradores, Maestría Química, Modificaciones de Armadura, Armadura Perfeccionada, Cañón Explosivo, Posición Fortificada, Listo para la Batalla y Defensor Mejorado.
- **Erratas de la traducción corregidas según el original** (revisar con el libro oficial): Destello de Ingenio y Sacudida Arcana se recuperan con un descanso **largo**; la traducción dice «corto o largo».
- **Infusiones**: son opciones de clase (grupo «infusion»), 4 a nivel 2 y 2 más a niveles 6, 10, 14 y 18. Las que piden nivel (6, 10 o 14) lo respetan en el modo sencillo; en el modo normal el requisito va en la descripción. Replicar Objeto Mágico se puede repetir; las tablas de objetos replicables van resumidas en su descripción. Ni los objetos imbuidos ni los objetos replicados se añaden al equipo.
- **Herramienta de especialista repetida**: si la herramienta de artesano elegida a nivel 1 es la que da el especialista, el modo sencillo cambia la elegida al subir de nivel; en el modo normal la ficha avisa.
- **Criaturas y armas del especialista**: el homúnculo, el cañón sobrenatural y el defensor de acero van resumidos en el rasgo; no se modelan como criaturas. Las armas de la Armadura Arcana (Guanteletes de Trueno, Lanzarrayos) no salen en la lista de ataques, y la ficha calcula los ataques con armas con Fuerza o Destreza: atacar con Inteligencia (Armero, Listo para la Batalla) va en el texto del rasgo.
- **Perfil en el modo sencillo**: saber, astucia (ingenio) y arcano a partes iguales. Con más peso en saber, quien respondía solo hacia el saber recibía artífice en vez de mago; así el mago se queda el saber puro y el saber con magia, y el artífice el saber con ingenio.
- **Armas de fuego**: la competencia que da el libro si el DM usa armas de fuego no se modela (no hay armas de fuego en el catálogo).
