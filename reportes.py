"""Recrea los informes con cifras de resultados/resumen.json y portadas originales."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                               Spacer, Table, TableStyle)

AZUL=colors.HexColor('#365F91')
ANCHO=520


def numero(valor,decimales=3):
    return 'No definido' if valor is None else f'{valor:.{decimales}f}'


def estado_meta(valor:float,meta:float)->str:
    return 'CUMPLE' if valor>=meta else 'REVISAR'


def estilos():
    reg=Path('C:/Windows/Fonts/GOTHIC.TTF')
    bold=Path('C:/Windows/Fonts/GOTHICB.TTF')
    if not reg.is_file():
        from matplotlib.font_manager import findfont
        reg=Path(findfont('DejaVu Sans'))
        bold=Path(findfont('DejaVu Sans:weight=bold'))
    pdfmetrics.registerFont(TTFont('Proyecto',str(reg)))
    pdfmetrics.registerFont(TTFont('Proyecto-Bold',str(bold)))
    pdfmetrics.registerFontFamily('Proyecto',normal='Proyecto',bold='Proyecto-Bold',
                                italic='Proyecto',boldItalic='Proyecto-Bold')
    return {
        'body':ParagraphStyle('body',fontName='Proyecto',fontSize=10.5,leading=14.5,
                              alignment=TA_JUSTIFY,spaceAfter=8),
        'title':ParagraphStyle('title',fontName='Proyecto',fontSize=19,leading=23,
                               textColor=AZUL,spaceAfter=15),
        'sub':ParagraphStyle('sub',fontName='Proyecto-Bold',fontSize=11,leading=14.5,
                             spaceBefore=9,spaceAfter=7),
        'note':ParagraphStyle('note',fontName='Proyecto',fontSize=9,leading=12,
                              textColor=colors.HexColor('#444444'),spaceAfter=7),
        'cell':ParagraphStyle('cell',fontName='Proyecto',fontSize=9.2,leading=12),
        'head':ParagraphStyle('head',fontName='Proyecto-Bold',fontSize=9.2,leading=12),
        'caption':ParagraphStyle('caption',fontName='Proyecto',fontSize=8.5,leading=11,
                                 alignment=TA_CENTER,spaceBefore=5,spaceAfter=8),
    }


class Informe:
    def __init__(self,r:dict,figuras:Path):
        self.r=r;self.figuras=figuras;self.s=estilos()

    def p(self,t,style='body'):
        return Paragraph(t,self.s[style])

    def h(self,t):return self.p(t,'title')
    def sub(self,t):return self.p(t,'sub')
    def nota(self,t):return self.p(t,'note')

    def tabla(self,filas,anchos):
        datos=[[self.p(escape(str(c)),'head' if i==0 else 'cell') for c in fila]
               for i,fila in enumerate(filas)]
        t=Table(datos,colWidths=anchos,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([
            ('GRID',(0,0),(-1,-1),.65,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F1F4F8')),
        ]))
        return t

    def img(self,nombre,ancho=ANCHO,maxalto=260):
        i=Image(str(self.figuras/f'{nombre}.png'))
        escala=min(ancho/i.imageWidth,maxalto/i.imageHeight)
        i.drawWidth=i.imageWidth*escala;i.drawHeight=i.imageHeight*escala
        i.hAlign='CENTER'
        return i

    def tabla_busquedas(self, ajuste):
        filas = [['Búsqueda', 'Pruebas', 'Configuración elegida', 'Media CV', 'DE', 'Pliegues válidos']]
        for fila in ajuste['busquedas']:
            parametros = ', '.join(f'{k.split("__")[-1]}={v}' for k, v in fila['parametros'].items())
            filas.append([
                fila['metodo'], fila['configuraciones'], parametros,
                numero(fila['media']), numero(fila['desviacion']),
                f'{fila["pliegues_validos"]}/{ajuste["n_folds"]}',
            ])
        return self.tabla(filas, [128, 51, 151, 60, 52, 78])

    def tecnica(self):
        r=self.r;m=r['muestra'];k=r['kpis'];c=r['clusters'];s=r['supervisado']
        filas=r['descriptivos'];rho=r['correlacion_traslado_ia']
        paginas=[]
        paginas.append([
            self.h('CONTEXTO, PROBLEMA Y OBJETIVOS'),
            self.p('<b>¿Cómo usan la IA quienes respondieron las encuestas y qué podemos aprender de esas respuestas?</b> Este informe reúne el análisis de hábitos, percepciones y entorno universitario del grupo. También evalúa dos tareas: clasificar la modalidad declarada de uso y estimar las horas diarias de IA.'),
            self.sub('CONTEXTO ACADÉMICO Y TECNOLÓGICO'),
            self.p('Las respuestas describen cómo se estudia con IA, cómo se verifica lo que produce y qué cambios se perciben en el tiempo de trabajo, la autonomía y el bienestar. Como cada persona escribió con sus propias palabras, fue necesario normalizar expresiones y documentar cómo se interpretaron.'),
            self.sub('PLANTEAMIENTO DEL PROBLEMA'),
            self.p('Las encuestas permiten describir experiencias y buscar asociaciones. Para saber si la IA mejora el desempeño académico harían falta calificaciones verificadas y un diseño que permita comparar cambios. Esos datos no están disponibles, así que el análisis mantiene sus conclusiones dentro de lo observado.'),
            self.sub('OBJETIVO GENERAL'),
            self.p('Preparar los cuestionarios con Python, describir el uso de IA y el contexto estudiantil mediante indicadores, explorar agrupaciones con K-Means y evaluar si KNN ayuda a clasificar el uso declarado. La regresión de horas de IA es un ejercicio complementario.'),
            self.sub('OBJETIVOS ESPECÍFICOS'),
            self.p('1. Limpiar todos los campos de la encuesta de IA y las variables de bienestar que se incorporan al estudio.<br/>2. Validar las claves, unir las fuentes y explorar sus indicadores.<br/>3. Comparar GridSearchCV y RandomizedSearchCV en K-Means y KNN.<br/>4. Evaluar KNN en una prueba reservada y estimar horas de uso con una regresión complementaria.<br/>5. Compartir los indicadores y resultados en un tablero analítico.'),
            self.nota('El notebook, el tablero y los informes usan los mismos resultados agregados. Cada tarea predictiva tiene su propio objetivo, sus particiones y sus métricas.'),
        ])
        paginas.append([
            self.h('ARQUITECTURA E INTEGRACIÓN DE DATOS'),
            self.p('El módulo analisis.py calcula los resultados que después consultan el notebook, las figuras, el tablero interactivo y ambos informes. Así, una misma cifra conserva su definición en toda la entrega.'),
            self.tabla([
                ['Módulo','Responsabilidad'],
                ['1. Fuentes y validación','Verificar columnas, orden, identificadores de nueve dígitos, unicidad y presencia de archivos.'],
                ['2. Limpieza y unión','Normalización, expresiones regulares, similitud de cadenas para herramientas y unión uno a uno.'],
                ['3. Texto y codificación','Corpus sin valores nan ni respuestas inventadas. Polaridad por pregunta con negación.'],
                ['4. Descripción y agrupación','EDA de la muestra; asociaciones y clustering de registros con bienestar observado.'],
                ['5. Modelos y evaluación','Búsqueda en cuadrícula y aleatoria para K-Means y KNN. Clasificación y regresión usan sus propias referencias y pruebas.'],
                ['6. Salidas','JSON, tablas y figuras agregadas; reportes generados desde la misma ejecución.'],
            ],[135,385]),Spacer(1,14),
            self.tabla([
                ['Fuente / cruce','Registros','Atributos originales'],
                ['Uso de IA',m['ia'],18],['Entorno y bienestar',m['bienestar'],17],
                ['Emparejados',m['emparejados'],'Llave validada, unión uno a uno'],
                ['Solo en IA',m['solo_ia'],'Bienestar no observado'],
                ['Solo en bienestar',m['solo_bienestar'],'No se incorporan al universo principal'],
            ],[270,80,170]),
            self.nota('La clave se utiliza únicamente en memoria para el cruce. No se exportan cuentas, marcas temporales ni respuestas abiertas. Las encuestas originales permanecen locales, excluidas de Git.'),
        ])
        limpieza = r.get('limpieza')
        cobertura_limpieza = []
        if limpieza:
            ia = limpieza['ia']
            bie = limpieza['bienestar']
            cobertura_limpieza = [
                self.p(f'El flujo aplica una regla o validación a los {ia["columnas_cubiertas"]} campos de la encuesta de IA y a {bie["columnas_cubiertas"]} campos del complemento. Los {len(bie["columnas_fuera_de_alcance"])} campos de bienestar ajenos al análisis quedan identificados en el registro de cobertura.'),
                self.nota('El notebook muestra la regla, los ausentes de origen, los ausentes tras la limpieza y los valores modificados por campo. Los conteos proceden de Python y el archivo de resultados registra las huellas de ambas fuentes.'),
            ]
        paginas.append([
            self.h('LIMPIEZA, REGEX Y DATOS AUSENTES'),
            self.p('Python lee directamente las exportaciones originales. Los cambios se aplican en memoria y el cotejo por campo deja evidencia de qué pasó con las respuestas, incluso con las preguntas que sirven solo para describir el formulario.'),
            self.tabla([
                ['Variable / caso','Regla aplicada'],
                ['Cuenta y marca temporal','Validación del formato de las cuentas y conversión de la marca temporal. Se usan internamente y se excluyen de las salidas públicas.'],
                ['Respuestas abiertas','Normalización de espacios y caracteres sin perder el contenido. Se conserva como ausente una respuesta en blanco. La pregunta sobre otros usos de IA también se prepara.'],
                ['Horas de IA','Minutos / 60; “hora y media” = 1.5; “entre 1 y 3” = 2. Los rangos se aproximan y no representan mediciones exactas.'],
                ['Semestre de inicio','Ordinales y dígitos. “Hace 3 semestres” se interpreta respecto al 7.º semestre de la cohorte descrita.'],
                ['Edad y traslado','Se extraen edades; horas y minutos se convierten a minutos. No se recortan los valores extremos observados.'],
                ['Herramientas','Los patrones y alias reconocen nombres como Chat GPT y Chargpt. La similitud sirve para detectar variantes cercanas de forma conservadora. Cada herramienta se cuenta una vez por respuesta.'],
                ['Modalidad de uso','Guía, atajo, híbrido, contextual o no clasificable. “Depende” por sí solo no prueba modalidad híbrida.'],
                ['Reemplazo laboral','Se distinguen Sí, No, Parcial / Depende e Indeciso antes de calcular porcentajes.'],
            ],[125,395]),
            Spacer(1, 10), *cobertura_limpieza,
            self.sub('TRATAMIENTO DE AUSENCIAS'),
            self.p(f'Los {m["solo_ia"]} participantes sin segunda encuesta conservan bienestar nulo. Las {r["calidad"]["textos_ia_ausentes"]} respuestas abiertas faltantes de IA no se sustituyen por textos de otros estudiantes. Para describir entorno se usan solo los {m["emparejados"]} registros observados.'),
            self.p('En clasificación, cada pliegue aprende la escala y la imputación numérica por tres vecinos con sus propios datos de entrenamiento. La imputación añade indicadores de ausencia y se aplica a los predictores numéricos.'),
            self.nota('Los conteos de horas, semestres, edades y traslados sin convertir se consultan en el notebook. Cuando la respuesta original da un rango, el valor convertido sigue siendo una aproximación.'),
        ])
        paginas.append([
            self.h('PROCESAMIENTO DE LENGUAJE NATURAL'),
            self.sub('NORMALIZACIÓN Y VECTORIZACIÓN'),
            self.p('El texto se normaliza con Unicode, se retiran signos y números y se filtran palabras funcionales preservando negaciones. TF-IDF utiliza hasta 30 características con unigramas y bigramas. La vectorización descriptiva de toda la muestra es independiente de la que se ajusta dentro de cada fold del modelo.'),
            self.sub('POLARIDAD LÉXICA CONTEXTUAL'),
            self.p('Se cuentan raíces positivas y negativas por pregunta. La negación en las cuatro palabras anteriores y las expresiones de alivio modifican la polaridad. La puntuación por pregunta es (positivos - negativos) / (positivos + negativos + 1); el indicador final es la media de las preguntas respondidas.'),
            self.tabla([
                ['Comprobación','Resultado esperado'],
                ['ayuda / no ayuda','Polaridad positiva / negativa'],
                ['La práctica no afecta mi comprensión','No se penaliza como afectación afirmada'],
                ['Mi estrés ha bajado / no reduce mi estrés','Alivio positivo / alivio negado negativo'],
                ['El descanso no parece bueno','Polaridad negativa en el contexto de descanso'],
                ['Sin encuesta','Dato ausente; no se asigna bienestar neutral'],
            ],[245,275]),Spacer(1,10),self.img('nlp',maxalto=170),
            self.nota('Estas frases de ejemplo comprueban reglas del programa, pero no validan una escala psicológica. La ironía, las negaciones lejanas y la ambigüedad siguen siendo difíciles de interpretar. Un cero también puede indicar que no hubo palabras reconocidas. El notebook muestra cuántas respuestas y ceros hay por pregunta.'),
        ])
        nombres={'horas_ia_dia':'Horas IA / día','semestre_inicio':'Inicio (semestre)',
                 'total_herramientas':'Herramientas','edad':'Edad observada',
                 'traslado_min':'Traslado (min)','score_beneficio_ia':'Polaridad IA','score_bienestar':'Polaridad entorno'}
        tabla=[['Variable','n','Media','DE','Mediana','Mín.','Máx.']]
        for var in nombres:
            d=filas[var]
            tabla.append([nombres[var],d['n'],f'{d["media"]:.2f}',f'{d["sd"]:.2f}',f'{d["mediana"]:.2f}',f'{d["min"]:.2f}',f'{d["max"]:.2f}'])
        paginas.append([
            self.h('ANÁLISIS EXPLORATORIO UNIVARIADO'),self.tabla(tabla,[155,35,66,66,66,66,66]),
            Spacer(1,12),self.img('uso_modalidad',maxalto=245),
            self.p(f'La mediana de uso es {k["mediana_ia_h"]:.2f} h/día. La diversidad de herramientas, una vez normalizados los alias, tiene media {filas["total_herramientas"]["media"]:.2f}; {k["multiherramienta_n"]} de {m["ia"]} participantes mencionan al menos dos plataformas.'),
            self.nota('La mediana ubica el centro de las respuestas ordenadas y es menos sensible a valores muy altos que el promedio. La media de herramientas es un promedio del grupo, no una cantidad que deba usar cada estudiante.'),
            self.p(f'El uso híbrido explícito representa {k["hibrido_pct"]:.1f}%. Guía e híbrido suman {k["guia_hibrido_pct"]:.1f}%. Las respuestas contextuales y no clasificables se conservan en el denominador total y no se fuerzan a una modalidad.'),
            self.nota('DE = desviación estándar muestral. Edad, traslado y polaridad del entorno se describen sobre observaciones reales; no sobre valores imputados. El valor extremo de traslado se conserva como respuesta, sin asumir que corresponde a un solo trayecto.'),
        ])
        paginas.append([
            self.h('ASOCIACIONES Y CRUCE DE ENCUESTAS'),
            self.p(f'El cruce directo utiliza {rho["n"]} participantes con respuesta en ambos cuestionarios. Para traslado y horas de IA se obtuvo rho de Spearman = {rho["rho"]:.3f}, con p = {rho["p"]:.3f}.'),
            self.p('El coeficiente está cerca de cero: en estas respuestas no aparece un patrón claro en el que más traslado acompañe más o menos horas de IA. El valor p es alto, por lo que la muestra no aporta evidencia suficiente de una asociación monotónica. Eso tampoco prueba que la relación sea inexistente. Las demás correlaciones se exploran sin ajuste por comparaciones múltiples.'),
            self.img('correlacion',maxalto=330),
            self.sub('ALCANCE DE LA INTERPRETACIÓN'),
            self.p('Las respuestas describen percepciones en un único momento. La selección de participantes, el tamaño reducido y el posible sesgo de autoinforme limitan la generalización a la carrera. La presencia de valores extremos puede alterar tanto correlaciones como agrupaciones.'),
        ])
        paginas.append([
            self.h('CLUSTERING Y PROYECCIÓN PCA'),
            self.p(f'Se agruparon {c["n"]} registros con bienestar observado. Se estandarizaron horas de IA, semestre de inicio, diversidad de herramientas, traslado y los dos indicadores léxicos. La solución mostrada usa k={c["k"]} y tiene una silueta de {c["silhouette"]:.3f} en la muestra completa.'),
            self.img('clusters',maxalto=225),
            self.p(f'El clustering jerárquico con el mismo k obtuvo {c["silhouette_jerarquico"]:.3f}. Los dos primeros componentes PCA explican {100*sum(c["pca_varianza"]):.2f}% de la varianza: PC1 {100*c["pca_varianza"][0]:.2f}% y PC2 {100*c["pca_varianza"][1]:.2f}%.'),
            self.sub('GRUPOS PEQUEÑOS Y ESTABILIDAD'),
            self.p('La silueta resume qué tan separado queda cada grupo respecto de los demás. Un valor más cercano a 1 indica mayor separación según esta métrica. El recorrido de k entre 2 y 5 sobre la muestra completa sirve como comparación descriptiva. La separación observada aquí puede cambiar en otra muestra.'),
            self.p('Los tamaños desiguales muestran que pocos casos pueden explicar parte de la separación. Se omiten descripciones si el grupo o su complemento tienen menos de tres personas, para evitar que un agregado permita reconocer una respuesta individual. Los grupos sirven para plantear nuevas preguntas sobre los hábitos.'),
        ])
        ajuste_c = c.get('ajuste')
        ajuste_s = s.get('ajuste')
        if ajuste_c and ajuste_s:
            paginas.append([
                self.h('CÓMO SE AJUSTARON K-MEANS Y KNN'),
                self.p('GridSearchCV prueba cada combinación de la cuadrícula. RandomizedSearchCV prueba una selección de combinaciones con semilla fija. La media de validación y la dispersión entre pliegues permiten comparar los resultados bajo la misma partición dentro de cada tarea.'),
                self.sub('K-MEANS · SILUETA EN VALIDACIÓN'),
                self.tabla_busquedas(ajuste_c), Spacer(1, 9),
                self.p('En cada pliegue se ajustan la escala y los centroides con los datos de entrenamiento. Luego se asignan los casos de validación a esos centroides. Cuando las etiquetas obtenidas no permiten calcular la silueta se aplica una penalización de -1 para elegir la configuración. La columna de pliegues válidos distingue los que sí permitieron calcularla.'),
                self.nota(f'Método seleccionado para K-Means: {ajuste_c["mejor_metodo"] or "ninguno con pliegues válidos"}.'),
                self.sub('KNN · F1 EN VALIDACIÓN ESTRATIFICADA'),
                self.tabla_busquedas(ajuste_s), Spacer(1, 9),
                self.p('La búsqueda de KNN se realiza solo con los datos de entrenamiento. Cada pliegue vuelve a aprender las transformaciones. F1 determina la configuración elegida. En los parámetros, p=1 corresponde a distancia Manhattan y p=2 a euclidiana. La prueba reservada se consulta al final.'),
                self.nota(f'Método seleccionado para KNN: {ajuste_s["mejor_metodo"]}. Se reporta la media y la desviación estándar (DE) de la mejor configuración de cada búsqueda.'),
            ])
        cv=[['Clasificador','Accuracy CV','DE','F1 CV','DE']]
        cv.extend([[x['modelo'],f'{x["cv_accuracy"]:.3f}',f'{x["cv_accuracy_sd"]:.3f}',f'{x["cv_f1"]:.3f}',f'{x["cv_f1_sd"]:.3f}'] for x in s['cv']])
        paginas.append([
            self.h('CLASIFICADORES CON PARÁMETROS FIJOS'),
            self.p(f'La variable objetivo distingue la modalidad mixta (1) de la exclusiva como guía o atajo (0). Se etiquetaron {s["n_etiquetados"]} respuestas, {s["clases"]["mixta"]} mixtas y {s["clases"]["exclusiva"]} exclusivas. Se excluyeron {s["n_excluidos"]} por ambigüedad o falta de una categoría clara.'),
            self.p('La pregunta de modalidad no se incluye en los predictores. Se combinan siete variables estructuradas con TF-IDF de otras preguntas, reducido a un máximo de cuatro componentes PCA según disponibilidad. Un vocabulario vacío aporta ceros. Cada fold ajusta escala, imputación, vocabulario y PCA.'),
            self.p(f'Se reservan {s["n_test"]} casos para prueba. La validación cruzada estratificada de {s["n_folds"]} folds se aplica solo a los {s["n_train"]} casos de entrenamiento. Se compara contra la estrategia de predecir siempre la clase mayoritaria.'),
            self.tabla(cv,[180,85,85,85,85]),Spacer(1,10),
            self.img('modelos_cv',maxalto=205),
            self.nota('Esta comparación exploratoria usa configuraciones fijas. El KNN ajustado de la página anterior tiene su propia evaluación. F1 combina precisión y recall para la modalidad mixta. Accuracy indica la proporción total de aciertos. CV significa validación cruzada y DE describe la variación entre pliegues.'),
        ])
        t=s['test'];b=s['baseline_test']
        comparacion_prueba = [
            ['Evaluación sobre prueba','Accuracy','Precisión','Recall','F1'],
            [s['seleccionado'],numero(t['accuracy']),numero(t['precision']),numero(t['recall']),numero(t['f1'])],
        ]
        if ajuste_s and ajuste_s.get('test') and not s['seleccionado'].startswith('KNN'):
            knn = ajuste_s['test']
            comparacion_prueba.append(['KNN ajustado',numero(knn['accuracy']),numero(knn['precision']),numero(knn['recall']),numero(knn['f1'])])
        comparacion_prueba.append(['Baseline (mayoría)',numero(b['accuracy']),numero(b['precision']),numero(b['recall']),numero(b['f1'])])
        mensaje=('El candidato supera el F1 medio del baseline en esta CV, sin acreditar significación ni generalización.' if s['supera_baseline_cv'] else 'El candidato no supera el F1 medio del baseline en validación cruzada. No se acredita ventaja predictiva para uso operativo.')
        paginas.append([
            self.h('PRUEBA RESERVADA, LÍMITES Y CONCLUSIONES'),
            self.p(f'Entre los cuatro modelos entrenables, se seleccionó {s["seleccionado"]} por F1 medio de CV, sin consultar la prueba. {mensaje}'),
            self.tabla(comparacion_prueba,[180,85,85,85,85]),Spacer(1,8),self.img('confusion',ancho=350,maxalto=190),
            self.p(f'Con n={s["n_test"]} en prueba, un acierto cambia accuracy en {s["test_sensible_pp"]:.1f} puntos porcentuales. El resultado puntual no corrige la inestabilidad observada entre folds.'),
            self.sub('CONCLUSIONES Y REPRODUCIBILIDAD'),
            self.p('La ventaja de un clasificador debe sostenerse frente a una referencia sencilla y con más datos. Esta evaluación sirve para entender qué aprende el modelo y cuánto cambian sus aciertos con la partición. Para tomar decisiones sobre estudiantes harían falta datos adicionales y una evaluación independiente.'),
            self.nota('Las páginas siguientes presentan una tarea distinta: estimar horas de uso con regresión. Fuente: resultados/resumen.json, metodología '+r['metodologia']['version']+', ejecución '+r['proveniencia']['fecha'][:10]+'. Las encuestas originales se conservan sin cambios.'),
        ])
        g=r['regresion'];lineal=g['modelos'][0];base=g['modelos'][1]
        paginas.append([
            self.h('REGRESIÓN: ESTIMAR HORAS DE USO DE IA'),
            self.p('Este ejercicio pregunta si dos características del uso de IA ayudan a estimar cuánto tiempo se utiliza al día. El objetivo son las horas declaradas en la encuesta, una variable numérica que permite evaluar R². No se dispone de calificaciones verificadas para usar como objetivo académico.'),
            self.tabla([
                ['Elemento','Definición'],
                ['Objetivo','Horas diarias declaradas de uso de IA.'],
                ['Predictores','Semestre de inicio de uso y cantidad de herramientas mencionadas. Las horas no se incluyen como entrada.'],
                ['Modelo','Regresión lineal con escalamiento ajustado en cada entrenamiento. Sin búsqueda de hiperparámetros.'],
                ['Referencia','Predecir siempre la media de horas del conjunto con el que se entrena.'],
                ['Casos',f'{g["n"]} completos; {g["n_excluidos"]} excluidos por objetivo o predictores ausentes/no válidos.'],
                ['Partición',f'{g["n_train"]} para entrenamiento y {g["n_test"]} para prueba (75/25), semilla 42.'],
            ],[120,400]),
            self.sub('CÓMO SE EVALUÓ'),
            self.p(f'Se fijaron ambos modelos antes de consultar la prueba. Sobre entrenamiento se hicieron {g["n_folds"]} pliegues: cada uno volvió a aprender la escala y los parámetros con sus propios datos. Después se ajustó cada modelo con los {g["n_train"]} casos de entrenamiento y se evaluó una vez en los {g["n_test"]} casos reservados. Esta partición es propia de la regresión y no coincide necesariamente con la de clasificación.'),
            self.sub('QUÉ SIGNIFICA CADA MÉTRICA'),
            self.p('<b>R² = 1 - SSE / SST.</b> SSE es la suma de errores cuadrados y SST la variación respecto de la media del conjunto evaluado. Un R² de 1 indica ajuste perfecto; 0 equivale a predecir esa media, y un valor negativo indica mayor error que esa referencia matemática. No es un porcentaje de precisión.'),
            self.p('<b>MAE</b> es el error absoluto medio, expresado en horas. <b>RMSE</b> es la raíz del error cuadrático medio: también se expresa en horas y da más peso a los errores grandes. En ambas métricas, un valor menor es mejor.'),
        ])
        tabla=[['Modelo','R² prueba','MAE (h)','RMSE (h)']]
        tabla.extend([[m['modelo'],numero(m['prueba']['r2']),numero(m['prueba']['mae_h']),numero(m['prueba']['rmse_h'])] for m in g['modelos']])
        validacion=[['Modelo','R² CV medio','DE R²','MAE CV (h)','RMSE CV (h)','R² válidos']]
        validacion.extend([[m['modelo'],numero(m['cv']['r2_media']),numero(m['cv']['r2_sd']),numero(m['cv']['mae_media_h']),numero(m['cv']['rmse_media_h']),f'{m["cv"]["folds_r2_validos"]}/{g["n_folds"]}'] for m in g['modelos']])
        tamanos=[f['n'] for f in g['modelos'][0]['folds']]
        paginas.append([
            self.h('R²: RESULTADOS E INTERPRETACIÓN'),
            self.tabla(tabla,[190,110,110,110]),Spacer(1,10),self.img('regresion',maxalto=185),
            self.p(f'La regresión obtuvo R² = {numero(lineal["prueba"]["r2"])} en prueba. Su MAE fue {lineal["prueba"]["mae_h"]:.3f} h, unos {60*lineal["prueba"]["mae_h"]:.0f} minutos de desviación media. La referencia del promedio tuvo MAE de {base["prueba"]["mae_h"]:.3f} h. '+('Añadir los dos predictores no redujo el error medio.' if lineal['prueba']['mae_h']>=base['prueba']['mae_h'] else 'Añadir los dos predictores redujo el error medio en esta prueba.')),
            self.p('Un R² negativo es un resultado válido, no un fallo del cálculo. La referencia usa la media de entrenamiento, por eso su R² de prueba también puede ser negativo: la media de los casos reservados puede ser distinta. Ningún error medio garantiza un margen de acierto para una persona concreta.'),
            self.tabla(validacion,[145,70,65,85,85,70]),
            self.nota(f'CV resume los {g["n_folds"]} resultados por pliegue, no un R² calculado al juntar predicciones. Los pliegues tienen entre {min(tamanos)} y {max(tamanos)} casos, por lo que su media y variación pueden cambiar mucho. DE no es un intervalo de confianza. R² válidos indica cuántos pliegues entran al promedio. Si las horas son constantes, su R² se registra como nulo y se conservan sus errores en horas.'),
            self.p('El alcance depende de esta pequeña muestra. Para comprobar si el patrón se sostiene se necesitan más participantes y datos precisos sobre frecuencia y tipo de actividad. El ejercicio aporta una evaluación reproducible de intensidad de uso, sin atribuir efectos al desempeño académico.'),
        ])
        return paginas

    def negocio(self):
        r=self.r;m=r['muestra'];k=r['kpis'];c=r['clusters'];s=r['supervisado']
        n=m['ia'];nb=m['emparejados'];tipos=r['tipo_uso'];rep=r['reemplazo']
        cv={x['modelo']:x for x in s['cv']}
        p=[]
        p.append([
            self.h('PANORAMA DEL PROYECTO E INDICADORES'),
            self.p('<b>Uso de IA y entorno estudiantil en MAC.</b><br/>Informe dirigido a la coordinación de la licenciatura y a la profesora de Sistemas Inteligentes.'),
            self.p(f'¿Qué lugar ocupa la IA en el estudio y qué apoyos conviene explorar? El proyecto reúne {n} respuestas sobre IA y {nb} sobre entorno. Los resultados ayudan a plantear conversaciones y actividades de seguimiento. Las encuestas recogen experiencias y percepciones, por lo que no permiten atribuir cambios en las calificaciones al uso de IA.'),
            self.sub('CUADRO DE MANDO: ADOPCIÓN Y MODALIDAD'),
            self.tabla([
                ['Indicador','Valor observado','Referencia propuesta','Lectura'],
                ['Adopción observada',f'{k["adopcion_observada_pct"]:.1f}% ({k["adopcion_observada_n"]}/{n})','Descriptiva','Menciones de herramientas reconocidas en las respuestas; no representa a toda la carrera ni acredita uso ético.'],
                ['Consumo mediano',f'{k["mediana_ia_h"]:.2f} h/día','Sin umbral validado','Intensidad declarada; no se etiqueta como saludable o excesiva solo por la mediana.'],
                ['Guía o modalidad mixta',f'{k["guia_hibrido_pct"]:.1f}% ({tipos.get("Guía",0)+tipos.get("Híbrido",0)}/{n})','>=90%: meta de piloto',f'Estado: {estado_meta(k["guia_hibrido_pct"],90)}. Referencia propuesta; no equivale a calidad pedagógica demostrada.'],
                ['Diversidad (>=2 herramientas)',f'{k["multiherramienta_pct"]:.1f}% ({k["multiherramienta_n"]}/{n})','>=60%: meta de piloto',f'Estado: {estado_meta(k["multiherramienta_pct"],60)}. Usar más plataformas no garantiza aprender mejor.'],
            ],[124,93,118,185]),Spacer(1,12),
            self.nota('Las referencias de 90% y 60% son metas propuestas para un posible piloto, no políticas aprobadas. CUMPLE y REVISAR solo comparan la cifra con esa propuesta; no califican el aprendizaje ni a los estudiantes. Cada porcentaje indica cuántas respuestas lo sustentan.'),
        ])
        p.append([
            self.h('KPIs DE CONTEXTO Y VISIÓN PROFESIONAL'),
            self.tabla([
                ['Indicador','Valor observado','Interpretación y uso propuesto'],
                ['Modalidad mixta explícita',f'{k["hibrido_pct"]:.1f}% ({tipos.get("Híbrido",0)}/{n})','Describe combinación de guía y agilización. Las respuestas “depende” sin explicación no se fuerzan a esta categoría.'],
                ['Traslado mediano',f'{k["traslado_mediana_min"]:.0f} min (n={nb})',f'{k["traslado_mayor_90_n"]}/{nb} respuestas superan 90 min. Verificar necesidad de apoyo, sin inferir causalidad sobre aprovechamiento.'],
                ['Reemplazo laboral: Sí',f'{k["reemplazo_si_pct"]:.1f}% ({rep.get("Sí",0)}/{n})',f'Separado de respuestas parciales/depende ({rep.get("Parcial / Depende",0)}) e indecisas ({rep.get("Indeciso",0)}). No equivale a una predicción del mercado laboral.'],
                ['Cobertura de entorno',f'{100*nb/n:.1f}% ({nb}/{n})',f'{m["solo_ia"]} participantes sin segunda encuesta. No se les asigna bienestar neutral.'],
            ],[140,110,270]),Spacer(1,12),self.img('herramientas',maxalto=240),
            self.nota('Las menciones de herramientas no son excluyentes. Se normalizaron variantes ortográficas antes de contar. No se interpretan los porcentajes como estimaciones representativas de toda la generación.'),
        ])
        p.append([
            self.h('SEGMENTACIÓN EXPLORATORIA'),
            self.p(f'K-Means se aplicó a {c["n"]} participantes con entorno observado. Se probaron una búsqueda en cuadrícula y otra aleatoria para elegir la configuración. En la muestra completa quedaron {c["k"]} grupos, de tamaños '+', '.join(str(x) for x in c['tamanos'].values())+f'. Su silueta de {c["silhouette"]:.3f} resume la separación dentro de esta muestra.'),
            self.img('clusters',maxalto=240),
            self.sub('LO QUE PERMITE ESTA EXPLORACIÓN'),
            self.p('La separación puede depender de unos pocos casos con valores muy distintos. Esto ayuda a detectar preguntas que vale la pena estudiar, pero todavía no permite definir perfiles estables del alumnado. Para cuidar la privacidad se omiten descripciones cuando un grupo o su complemento tienen menos de tres personas.'),
            self.tabla([
                ['Uso apropiado','Uso que requiere más evidencia'],
                ['Identificar preguntas para futuras encuestas y revisar sensibilidad a extremos.','Asignar tutorías, beneficios o restricciones a una persona según su cluster.'],
                ['Explorar variación de hábitos dentro de esta muestra.','Atribuir dependencia, burnout o bajo rendimiento a una agrupación.'],
                ['Volver a medir con una muestra mayor y criterios observables.','Generalizar tamaños y perfiles a toda la carrera.'],
            ],[260,260]),
            self.nota('La segmentación se ofrece como material descriptivo. No constituye un mecanismo de selección de estudiantes ni reemplaza una evaluación individual consentida.'),
        ])
        inicio=r['semestre_inicio'];inicio34=inicio.get('3',0)+inicio.get('4',0)
        p.append([
            self.h('PLAN DE ACCIÓN Y SEGUIMIENTO'),
            self.p('Las siguientes actividades son propuestas para probar a pequeña escala. Parten de las respuestas y de objetivos de formación; su utilidad tendría que comprobarse durante el piloto, con criterios definidos antes de comenzar.'),
            self.tabla([
                ['Iniciativa propuesta','Fundamento en la muestra','Cómo verificar el piloto'],
                ['Formación en verificación de IA',f'{inicio34}/{n} respuestas sitúan el inicio entre 3.º y 4.º semestre.','Aplicar ejercicios equivalentes antes/después y evaluar explicación, fuentes y detección de errores.'],
                ['Evaluación del proceso','Guía y uso mixto predominan entre las modalidades declaradas.','Usar rúbricas de comprensión, pruebas de depuración y defensa del procedimiento, además del producto final.'],
                ['Recursos académicos flexibles',f'{k["traslado_mayor_90_n"]}/{nb} respuestas reportan más de 90 min de traslado.','Ofrecer materiales asíncronos y preguntar directamente por barreras y utilidad del apoyo.'],
                ['Orientación profesional','Existen percepciones de reemplazo total, parcial e incertidumbre.','Comparar comprensión de tareas automatizables y competencias de supervisión antes/después de un taller.'],
                ['Mejorar la recolección',f'La cohorte es pequeña y {m["solo_ia"]} personas carecen de encuesta complementaria.','Repetir el instrumento, registrar cobertura y reunir un resultado académico independiente con consentimiento.'],
            ],[128,180,212]),Spacer(1,14),
            self.sub('CÓMO LEER EL TABLERO'),
            self.p(f'El tablero en Streamlit presenta los indicadores junto con su tamaño de muestra. En Modelos se pueden consultar las búsquedas de clasificación y agrupación, y la regresión de horas. Los porcentajes de herramientas tienen como base las {n} respuestas. Las metas de seguimiento siguen siendo propuestas para un piloto.'),
        ])
        g=r['regresion'];lineal=g['modelos'][0]['prueba'];referencia=g['modelos'][1]['prueba']
        p.append([
            self.h('¿PODEMOS ESTIMAR LAS HORAS DE USO?'),
            self.p('Se añadió una regresión lineal para estimar las horas diarias declaradas a partir del semestre de inicio de uso y la cantidad de herramientas. Esta pregunta permite evaluar R² con un objetivo numérico. Describe intensidad de uso, sin convertirla en una medida de aprendizaje.'),
            self.p(f'Se trabajó con {g["n"]} casos completos: {g["n_train"]} para entrenamiento y {g["n_test"]} reservados para prueba. El modelo se comparó con una estrategia sencilla: usar siempre el promedio de horas del conjunto de entrenamiento.'),
            self.tabla([
                ['Modelo','R² de prueba','MAE (horas)','RMSE (horas)'],
                ['Regresión lineal',numero(lineal['r2']),numero(lineal['mae_h']),numero(lineal['rmse_h'])],
                ['Referencia: promedio',numero(referencia['r2']),numero(referencia['mae_h']),numero(referencia['rmse_h'])],
            ],[190,110,110,110]),Spacer(1,12),
            self.img('regresion',maxalto=185),
            self.sub('LECTURA EN PALABRAS SENCILLAS'),
            self.p(f'La regresión se desvió, en promedio, unos {60*lineal["mae_h"]:.0f} minutos. La referencia se desvió unos {60*referencia["mae_h"]:.0f}. '+('En esta prueba, conocer las dos características no mejoró el error medio frente al promedio.' if lineal['mae_h']>=referencia['mae_h'] else 'En esta prueba, las dos características redujeron el error medio frente al promedio.')),
            self.p('Un R² negativo indica que el modelo tuvo más error cuadrático que usar la media de los casos evaluados. No significa un porcentaje negativo de precisión ni que la IA perjudique el estudio. MAE expresa el error medio en horas; RMSE da más peso a los errores grandes. Esas cifras describen al modelo, no a las personas.'),
            self.nota(f'La validación con {g["n_folds"]} pliegues también cambia mucho entre particiones pequeñas. Con {g["n_test"]} casos de prueba, esta evaluación sirve para reconocer los límites del modelo y orientar una recolección más amplia. No respalda decisiones individuales ni conclusiones sobre calificaciones.'),
        ])
        mejor=cv[s['seleccionado']];base=cv['Baseline (mayoría)']
        knn = s.get('ajuste', {}).get('test')
        lectura_knn = []
        if knn:
            ajuste = s['ajuste']
            f1_cv = next(fila['media'] for fila in ajuste['busquedas'] if fila['metodo'] == ajuste['mejor_metodo'])
            lectura_knn.append(self.p(f'KNN ajustado obtuvo F1 medio de {f1_cv:.3f} en validación y {knn["f1"]:.3f} en la prueba. La referencia mayoritaria obtuvo {cv["Baseline (mayoría)"]["cv_f1"]:.3f} y {s["baseline_test"]["f1"]:.3f}, respectivamente. Con pocos casos, la comparación puede cambiar de una partición a otra.'))
        p.append([
            self.h('RESULTADO PREDICTIVO Y CONCLUSIONES'),
            self.p(f'La clasificación distingue uso mixto frente a uso exclusivo declarado, no aprendizaje efectivo. Se utilizaron {s["n_etiquetados"]} respuestas etiquetables; {s["n_excluidos"]} ambiguas se excluyeron. El conjunto de prueba tiene solo {s["n_test"]} casos.'),
            *lectura_knn,
            self.img('modelos_cv',maxalto=185),
            self.p(f'En la comparación con parámetros fijos, {s["seleccionado"]} obtuvo F1 medio de {mejor["cv_f1"]:.3f} en validación, frente a {base["cv_f1"]:.3f} de la referencia mayoritaria. '+('Esta ventaja puntual necesita confirmación independiente.' if s['supera_baseline_cv'] else 'La muestra aporta evidencia limitada para usar un clasificador en decisiones sobre estudiantes.')),
            self.p(f'{s["seleccionado"]} acertó {100*s["test"]["accuracy"]:.1f}% de las modalidades en prueba. Con {s["n_test"]} casos, un acierto cambia el resultado en {s["test_sensible_pp"]:.1f} puntos porcentuales.'),
            self.sub('CONCLUSIÓN PARA LA TOMA DE DECISIONES'),
            self.p('El aporte del proyecto está en describir hábitos, reunir percepciones y hacer visibles los límites de los modelos. En esta ejecución, '+('la clasificación superó la referencia por F1 en validación' if s['supera_baseline_cv'] else 'la clasificación no superó la referencia por F1 en validación')+' y '+('la regresión redujo el error medio frente al promedio' if lineal['mae_h']<referencia['mae_h'] else 'la regresión no redujo el error medio frente al promedio')+'. El siguiente paso es ampliar la muestra y probar actividades de formación con resultados académicos medidos de forma independiente.'),
            self.nota('El notebook, el tablero y estos informes consultan resultados/resumen.json. Metodología '+r['metodologia']['version']+', ejecución '+r['proveniencia']['fecha'][:10]+'.'),
        ])
        return p


def construir(paginas,portada:Path,destino:Path,r:dict,titulo:str):
    if not portada.is_file():
        raise FileNotFoundError('Falta el PDF de referencia para conservar su portada.')
    cuerpo=io.BytesIO()
    doc=SimpleDocTemplate(cuerpo,pagesize=(612,792),leftMargin=46,rightMargin=46,
                          topMargin=42,bottomMargin=53,title=titulo)
    fecha=r['proveniencia']['fecha'][:10]
    def pie(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(AZUL);canvas.setLineWidth(.6)
        canvas.line(46,43,566,43);canvas.setFont('Proyecto',8)
        canvas.setFillColor(colors.HexColor('#555555'))
        canvas.drawString(46,30,f'Proyecto de Sistemas Inteligentes | {fecha}')
        canvas.drawRightString(566,30,str(doc.page+1));canvas.restoreState()
    story=[]
    for i,pagina in enumerate(paginas):
        if i:story.append(PageBreak())
        story.extend(pagina)
    doc.build(story,onFirstPage=pie,onLaterPages=pie)
    writer=PdfWriter()
    writer.append(PdfReader(portada),pages=(0,1))
    writer.append(PdfReader(cuerpo))
    writer.add_metadata({'/Title':titulo,'/Subject':'Uso de IA y entorno universitario: resultados agregados',
                         '/Author':'Proyecto Sistemas Inteligentes - MAC'})
    destino.parent.mkdir(parents=True,exist_ok=True)
    with destino.open('wb') as f:writer.write(f)


def main():
    root=Path(__file__).parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resultados',type=Path,default=root/'resultados')
    p.add_argument('--referencias',type=Path,default=root/'data'/'referencias')
    p.add_argument('--out',type=Path,default=root/'docs')
    args=p.parse_args()
    r=json.loads((args.resultados/'resumen.json').read_text(encoding='utf-8'))
    if any(r[k]['estado']!='ok' for k in ['supervisado','regresion','clusters']):
        p.error('El informe requiere resultados completos; revise las limitaciones de muestra.')
    informe=Informe(r,args.resultados/'figuras')
    construir(informe.tecnica(),args.referencias/'DOCUMENTACION TECNICA SI_C.pdf',
              args.out/'DOCUMENTACION_TECNICA.pdf',r,'Documentación técnica')
    construir(informe.negocio(),args.referencias/'DOCUMENTACIÓN NEGOCIO SI_C.pdf',
              args.out/'DOCUMENTACION_NEGOCIO.pdf',r,'Documentación de negocio')
    print('Se generaron dos PDF nuevos con las portadas originales.')


if __name__=='__main__':main()
