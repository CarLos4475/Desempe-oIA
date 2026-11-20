"""Dashboard local de agregados. Inicio: streamlit run dashboard.py"""
from datetime import date
from html import escape
from pathlib import Path
from importlib import reload

import altair as alt
import pandas as pd
import streamlit as st

import dashboard_datos

# Una sesión activa puede conservar un adaptador anterior al contrato actual
# de resultados y documentos. Se recarga una vez cuando cambia ese contrato.
if getattr(dashboard_datos,'VERSION_ADAPTADOR',0)!=3:
    reload(dashboard_datos)

from dashboard_datos import (NOMBRES_HERRAMIENTAS, NOMBRES_VARIABLES,
                             documentos_publicos, leer_resumen,
                             tabla_herramientas, tabla_modalidades, tabla_regresion)

ROOT=Path(__file__).resolve().parent
RESUMEN=ROOT/'resultados'/'resumen.json'
VISTAS=['Panorama','Uso de IA','Entorno y bienestar','Modelos','Documentación']
AZUL='#285A88'
TURQUESA='#438F91'
ORO='#C4A265'
GRIS='#CCD7E3'
FONT='Century Gothic'

st.set_page_config(page_title='IA en contexto · MAC',page_icon='◈',layout='wide',initial_sidebar_state='auto')
st.html('<style>'+(ROOT/'assets'/'dashboard.css').read_text(encoding='utf-8')+'</style>')


@st.cache_data(show_spinner=False)
def cargar(version_fichero:int):
    return leer_resumen(RESUMEN)


def titulo(kicker:str,principal:str,descripcion:str):
    h=escape(principal).replace('\n','<br>')
    st.html(f'<div class="hero"><div class="eyebrow">{escape(kicker)}</div><h1>{h}</h1><p>{escape(descripcion)}</p></div>')


def seccion(principal:str,descripcion:str='',kicker:str=''):
    st.html((f'<div class="section-kicker">{escape(kicker)}</div>' if kicker else '')+
            f'<div class="section-title">{escape(principal)}</div>'+
            (f'<div class="section-sub">{escape(descripcion)}</div>' if descripcion else ''))


def metricas(items):
    for col,(label,valor,unidad,nota) in zip(st.columns(len(items)),items):
        with col:
            st.html(f'<div class="metric-card"><div class="metric-label">{escape(label)}</div>'
                    f'<div class="metric-value">{escape(str(valor))} <small>{escape(unidad)}</small></div>'
                    f'<div class="metric-note">{escape(nota)}</div></div>')


def mensaje(tit,texto):
    st.html(f'<div class="insight"><strong>{escape(tit)}</strong><p>{escape(texto)}</p></div>')


def nota(numero,tit,texto):
    st.html(f'<div class="note-card"><div class="numero">{escape(numero)}</div><strong>{escape(tit)}</strong><p>{escape(texto)}</p></div>')


def grafica(chart,key,descripcion):
    chart=(chart.configure_view(strokeOpacity=0)
           .configure_axis(labelFont=FONT,titleFont=FONT,labelFontSize=10,titleFontSize=10,
                           labelColor='#708298',titleColor='#708298',gridColor='#EDF1F6',domain=False,ticks=False)
           .configure_legend(labelFont=FONT,titleFont=FONT,labelColor='#667E94',labelFontSize=10,title=None)
           .configure_title(font=FONT,color='#284C69',fontSize=12))
    st.altair_chart(chart,width='stretch',theme=None,key=key,alt=descripcion)


def barras_herramientas(r,seleccion=None,unidad='Respuestas',key='herramientas',orden='Mayor uso'):
    df=tabla_herramientas(r,seleccion)
    df=df[df['Respuestas']>0]
    if df.empty:
        st.info('Selecciona al menos una herramienta con menciones para ver la gráfica.')
        return
    orden_y=alt.SortField(field=unidad,order='descending') if orden=='Mayor uso' else 'ascending'
    punto=alt.selection_point(fields=['Herramienta'],empty=True)
    base=alt.Chart(df).encode(
        y=alt.Y('Herramienta:N',sort=orden_y,title=None,axis=alt.Axis(labelLimit=130)),
        x=alt.X(f'{unidad}:Q',title=None,scale=alt.Scale(domain=[0,max(df[unidad])*1.23])),
        tooltip=[alt.Tooltip('Herramienta:N'),alt.Tooltip('Respuestas:Q',format='.0f'),
                 alt.Tooltip('Porcentaje:Q',format='.1f',title='% de la muestra')])
    barras=base.mark_bar(cornerRadiusEnd=3,size=19).encode(color=alt.condition(punto,alt.value(AZUL),alt.value('#CBD8E5'))).add_params(punto)
    formato='.1f' if unidad=='Porcentaje' else '.0f'
    labels=base.mark_text(align='left',dx=7,color='#47667F',font=FONT,fontSize=11).encode(text=alt.Text(f'{unidad}:Q',format=formato))
    grafica((barras+labels).properties(height=max(200,len(df)*35)),key,'Menciones de herramientas, con conteo y porcentaje sobre la muestra de IA.')


def donut_modalidades(r,key):
    df=tabla_modalidades(r)
    domain=['Híbrido','Guía','Atajo','Contextual','No clasificable']
    colors=[AZUL,TURQUESA,ORO,'#97ACC0','#DCE4ED']
    aro=alt.Chart(df).mark_arc(innerRadius=64,outerRadius=96,stroke='#FFFFFF',strokeWidth=3).encode(
        theta=alt.Theta('Respuestas:Q'),
        color=alt.Color('Modalidad:N',scale=alt.Scale(domain=domain,range=colors),
                        legend=alt.Legend(orient='bottom',columns=2,labelLimit=180,symbolType='circle')),
        order=alt.Order('Respuestas:Q',sort='descending'),
        tooltip=['Modalidad',alt.Tooltip('Respuestas:Q',format='.0f'),alt.Tooltip('Porcentaje:Q',format='.1f',title='% de la muestra')])
    centro=alt.Chart(pd.DataFrame({'n':[r['muestra']['ia']]})).mark_text(font=FONT,fontSize=34,color='#234C6D',dy=-4).encode(text='n:Q')
    etiqueta=alt.Chart(pd.DataFrame({'etiqueta':['respuestas']})).mark_text(font=FONT,fontSize=10,color='#8898A7',dy=23).encode(text='etiqueta:N')
    grafica((aro+centro+etiqueta).properties(height=250),key,'Distribución de modalidades declaradas; incluye respuestas ambiguas y no clasificables.')


def panorama(r):
    k,m=r['kpis'],r['muestra']
    titulo('SISTEMAS INTELIGENTES · MAC','Así usan la IA\nlos estudiantes.',
           f'Resultados de {m["ia"]} encuestas sobre herramientas de IA, hábitos de estudio y vida universitaria. Aquí puedes consultar qué respondió este grupo.')
    metricas([
        ('Tiempo diario (mediana)',f'{k["mediana_ia_h"]:.2f}','h',f'{m["ia"]} respuestas sobre IA'),
        ('Uso mixto',f'{k["hibrido_pct"]:.1f}','%',f'{r["tipo_uso"].get("Híbrido",0)} de {m["ia"]} respuestas'),
        ('Dos o más herramientas',f'{k["multiherramienta_pct"]:.1f}','%',f'{k["multiherramienta_n"]} de {m["ia"]} participantes'),
        ('Traslado (mediana)',f'{k["traslado_mediana_min"]:.0f}','min',f'{r["descriptivos"]["traslado_min"]["n"]} respuestas con duración'),
    ])
    mensaje('La IA aparece en las actividades de quienes respondieron.',
            f'{k["adopcion_observada_n"]} de {m["ia"]} personas mencionaron al menos una herramienta. Estas cifras corresponden al grupo encuestado, no a toda la carrera.')
    izquierda,derecha=st.columns([1.35,1],gap='medium')
    with izquierda,st.container(border=True,key='panel_panorama_tools'):
        seccion('Las herramientas más mencionadas','Una persona puede mencionar más de una herramienta.','01 / ADOPCIÓN')
        unidad=st.segmented_control('Unidad de las menciones',['Respuestas','Porcentaje'],default='Respuestas',required=True,key='unidad_panorama',label_visibility='collapsed')
        barras_herramientas(r,unidad=unidad,key='chart_tools_panorama')
        st.caption(f'Base: {m["ia"]} respuestas. Haz clic en una barra para resaltarla; doble clic para restaurar.')
    with derecha,st.container(border=True,key='panel_panorama_modalidad'):
        seccion('¿Guía, atajo o ambas?','Así describieron su forma de usar la IA.','02 / HÁBITOS')
        donut_modalidades(r,'chart_donut_panorama')
        st.caption('Si alguien respondió “depende” sin dar más detalles, su respuesta aparece como contextual.')
    a,b=st.columns(2)
    with a:
        total=r['tipo_uso'].get('Guía',0)+r['tipo_uso'].get('Híbrido',0)
        nota('PARA QUÉ LA USAN',f'{total} de {m["ia"]} declaran guía o uso mixto.',
             'Esto describe cómo dicen usarla. No demuestra cuánto aprendieron.')
    with b:
        nota('QUIÉNES CONTESTARON',f'{m["emparejados"]} personas respondieron ambas encuestas.',
             f'De las otras {m["solo_ia"]} personas no tenemos respuestas sobre su entorno.')


def uso_ia(r):
    m=r['muestra'];k=r['kpis']
    titulo('HÁBITOS Y ADOPCIÓN','Qué herramientas usan\ny para qué.',
           'Consulta las herramientas que mencionaron, cómo las usan y desde qué semestre. También puedes ver los temas más frecuentes en sus respuestas.')
    with st.container(border=True,key='panel_uso_tools'):
        seccion('Herramientas de IA','Elige cuáles quieres comparar. Los porcentajes siguen calculándose sobre todas las respuestas.')
        activas=[x for x,v in r['herramientas'].items() if v>0]
        c1,c2,c3=st.columns([2.3,1,1])
        with c1:seleccion=st.multiselect('Herramientas',activas,default=activas,format_func=lambda x:NOMBRES_HERRAMIENTAS.get(x,x),key='filtro_herramientas')
        with c2:unidad=st.selectbox('Mostrar',['Respuestas','Porcentaje'],key='unidad_uso')
        with c3:orden=st.selectbox('Orden',['Mayor uso','Nombre'],key='orden_uso')
        barras_herramientas(r,seleccion,unidad,'chart_tools_uso',orden)
        st.caption(f'Cada porcentaje se calcula sobre {m["ia"]} respuestas, incluso cuando solo se muestran algunas herramientas.')
    izq,der=st.columns(2)
    with izq,st.container(border=True,key='panel_uso_modalidad'):
        seccion('Cómo dicen usar la IA',f'Base: {m["ia"]} respuestas. Las respuestas que no definen una modalidad aparecen por separado.')
        donut_modalidades(r,'chart_donut_uso')
    with der,st.container(border=True,key='panel_uso_inicio'):
        seccion('Desde qué semestre la usan','El semestre que mencionó cada persona al responder.')
        d=pd.DataFrame([{'Semestre':f'{key}.º','Respuestas':v} for key,v in r['semestre_inicio'].items()])
        chart=alt.Chart(d).mark_bar(color=AZUL,cornerRadiusEnd=4,size=28).encode(
            x=alt.X('Semestre:O',title=None,axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Respuestas:Q',title=None),tooltip=['Semestre','Respuestas']).properties(height=260)
        grafica(chart,'chart_semestre','Número de respuestas por semestre de inicio del uso de IA.')
        st.caption('Las referencias relativas (“hace… semestres”) se interpretan respecto al 7.º semestre de la cohorte descrita.')
    with st.container(border=True,key='panel_uso_texto'):
        seccion('De qué hablan las respuestas','TF-IDF ayuda a identificar términos destacados. Que una palabra aparezca aquí no indica si se usó con una opinión positiva o negativa.','ANÁLISIS DEL TEXTO')
        d=pd.DataFrame([{'Término':key,'Peso medio':v} for key,v in r['tfidf_top'].items()])
        if d.empty:st.info('No hay vocabulario descriptivo disponible para esta ejecución.')
        else:
            chart=alt.Chart(d).mark_bar(color=TURQUESA,cornerRadiusEnd=3,size=16).encode(
                x=alt.X('Peso medio:Q',title='Peso TF-IDF medio'),y=alt.Y('Término:N',sort='-x',title=None),
                tooltip=['Término',alt.Tooltip('Peso medio:Q',format='.3f')]).properties(height=260)
            grafica(chart,'chart_tfidf','Términos destacados del texto académico por TF-IDF medio.')


def entorno(r):
    m,k=r['muestra'],r['kpis'];d=r['descriptivos']['traslado_min'];co=r['correlacion_traslado_ia']
    titulo('ENTORNO UNIVERSITARIO','El entorno de\nquienes respondieron.',
           f'Esta sección reúne las respuestas de las {m["emparejados"]} personas que contestaron ambos cuestionarios. No asignamos una puntuación de bienestar a quienes no respondieron esa encuesta.')
    metricas([
        ('Respondieron ambas encuestas',str(m['emparejados']),f'/ {m["ia"]}',f'{100*m["emparejados"]/m["ia"]:.1f}% de cobertura'),
        ('Traslado (mediana)',f'{d["mediana"]:.0f}','min',f'n = {d["n"]} respuestas observadas'),
        ('Traslado mayor a 90 min',str(k['traslado_mayor_90_n']),f'/ {d["n"]}','Umbral descriptivo propuesto'),
        ('Sin encuesta de entorno',str(m['solo_ia']),'casos','No tenemos datos de su entorno'),
    ])
    st.write('')
    izq,der=st.columns([1.35,1])
    with izq,st.container(border=True,key='panel_entorno_traslado'):
        seccion('Cuánto tiempo les toma trasladarse','Se muestran el rango y los cuartiles. Cada marca resume al grupo; no representa a una persona.')
        rango=pd.DataFrame([{'Mínimo':d['min'],'Máximo':d['max'],'Q1':d['q1'],'Q3':d['q3'],'Mediana':d['mediana']}])
        base=alt.Chart(rango)
        regla=base.mark_rule(color='#AFC0D0',strokeWidth=3).encode(x=alt.X('Mínimo:Q',scale=alt.Scale(domain=[0,d['max']*1.08]),title='Minutos de traslado declarados'),x2='Máximo:Q')
        caja=base.mark_bar(color='#C4D8E8',size=38).encode(x='Q1:Q',x2='Q3:Q',tooltip=[alt.Tooltip('Q1:Q',title='Primer cuartil'),alt.Tooltip('Q3:Q',title='Tercer cuartil')])
        mediana=base.mark_tick(color=ORO,thickness=4,size=53).encode(x='Mediana:Q',tooltip=['Mediana'])
        grafica((regla+caja+mediana).properties(height=170),'chart_traslado','Rango de traslado y cuartiles; la línea dorada indica la mediana.')
        st.caption(f'El 50% central se ubica entre {d["q1"]:.0f} y {d["q3"]:.0f} min. Rango observado: {d["min"]:.0f}–{d["max"]:.0f} min. No se asume un trayecto de ida o viaje redondo.')
    with der,st.container(border=True,key='panel_entorno_asociacion'):
        seccion('Traslado y horas de IA','Correlación de Spearman entre las respuestas disponibles.')
        if co['rho'] is None or co['p'] is None:
            st.info('No se pudo estimar la correlación con los datos disponibles.')
        else:
            lectura=('No se encontró una asociación monotónica clara en esta muestra.' if co['p']>=.05
                     else 'Se encontró una asociación monotónica en esta muestra (p < 0.05).')
            st.html(f'<div class="coef">ρ {co["rho"]:+.3f}</div><div class="coef-caption">p = {co["p"]:.3f} · n = {co["n"]}<br>{lectura}</div>')
        st.caption('El resultado es exploratorio. No prueba que el traslado cambie las horas de uso de IA, ni descarta que exista alguna relación.')
    with st.container(border=True,key='panel_entorno_matriz'):
        seccion('Relaciones entre las variables','Solo se incluyen quienes respondieron ambos cuestionarios. Son asociaciones exploratorias, sin ajuste por comparaciones múltiples.')
        opciones=list(r['correlacion_spearman'])
        variables=st.multiselect('Variables de la matriz',opciones,default=opciones,format_func=lambda x:NOMBRES_VARIABLES.get(x,x),key='variables_correlacion')
        if not variables:st.info('Selecciona al menos una variable para mostrar la matriz.')
        else:
            filas=[{'Variable X':NOMBRES_VARIABLES.get(x,x),'Variable Y':NOMBRES_VARIABLES.get(y,y),
                    'Correlación':r['correlacion_spearman'][x][y]} for x in variables for y in variables]
            df=pd.DataFrame(filas)
            base=alt.Chart(df).encode(x=alt.X('Variable X:N',title=None,axis=alt.Axis(labelAngle=-30,labelLimit=140)),y=alt.Y('Variable Y:N',title=None,axis=alt.Axis(labelLimit=140)))
            mapa=base.mark_rect(cornerRadius=3,stroke='#FFFFFF',strokeWidth=2).encode(color=alt.Color('Correlación:Q',scale=alt.Scale(domain=[-1,0,1],range=['#7CA9AD','#F3F6FA','#285A88']),legend=alt.Legend(orient='right')),tooltip=['Variable X','Variable Y',alt.Tooltip('Correlación:Q',format='.3f')])
            numeros=base.mark_text(font=FONT,fontSize=11).encode(text=alt.Text('Correlación:Q',format='.2f'),color=alt.condition(alt.datum.Correlación>.65,alt.value('#FFFFFF'),alt.value('#365A76')))
            grafica((mapa+numeros).properties(height=max(150,len(variables)*45)),'chart_correlacion','Matriz de correlaciones de Spearman con valores numéricos y etiquetas de variables.')
    with st.expander('Qué significa la puntuación del texto'):
        st.write('La puntuación se basa en palabras y reglas de negación; no es una evaluación clínica. Un cero puede significar que no se encontraron palabras del vocabulario. Esto ocurre especialmente en respuestas de frecuencia, así que no equivale a un estado emocional neutral.')
        preguntas={'ambiente_hogar':'Ambiente del hogar','calidad_sueno':'Calidad del descanso','frecuencia_desanimo':'Frecuencia de desánimo','irritabilidad':'Irritabilidad','dificultad_concentracion':'Concentración'}
        filas=[{'Pregunta':label,**r.get('polaridad_por_pregunta',{}).get(key,{})} for key,label in preguntas.items()]
        st.dataframe(pd.DataFrame(filas).rename(columns={'n':'Respuestas','media':'Media léxica','n_score_cero':'Puntuaciones en cero'}),hide_index=True,width='stretch')


def regresion(r):
    g=r['regresion']
    if g['estado']!='ok':
        st.info('No hay suficientes casos completos o variación en las horas para evaluar la regresión.')
        return
    lineal=next(m for m in g['modelos'] if m['modelo']=='Regresión lineal')
    referencia=next(m for m in g['modelos'] if m['modelo']=='Referencia (media)')
    t=lineal['prueba'];b=referencia['prueba']
    fmt=lambda v:'No definido' if v is None else f'{v:.3f}'
    seccion('¿Podemos estimar las horas de uso de IA?',
            'La regresión lineal usa el semestre en que se empezó a utilizar IA y la cantidad de herramientas mencionadas. Las horas son declaradas por quienes respondieron.')
    metricas([('R² de prueba',fmt(t['r2']),'','Puede ser negativo'),
              ('Error absoluto medio (MAE)',f'{t["mae_h"]:.2f}','horas',f'Unos {60*t["mae_h"]:.0f} minutos de error medio'),
              ('Raíz del error cuadrático (RMSE)',f'{t["rmse_h"]:.2f}','horas','Da más peso a los errores grandes'),
              ('Casos reservados para prueba',str(g['n_test']),'casos',f'{g["n_train"]} casos para entrenamiento')])
    with st.container(border=True,key='panel_regresion_prueba'):
        seccion('Comparación en las mismas respuestas de prueba',
                'La referencia predice siempre el promedio de horas del conjunto de entrenamiento. Ninguno de los dos modelos se eligió a partir de esta prueba.')
        tabla=tabla_regresion(r)
        st.dataframe(tabla,hide_index=True,width='stretch',column_config={c:st.column_config.NumberColumn(format='%.3f') for c in ['R²','MAE (horas)','RMSE (horas)']})
        medida=st.segmented_control('Métrica de regresión',['R²','MAE (horas)','RMSE (horas)'],default='R²',required=True,key='metrica_regresion')
        d=tabla[['Modelo',medida]].rename(columns={medida:'Valor'}).dropna()
        if not d.empty:
            base=alt.Chart(d).encode(y=alt.Y('Modelo:N',title=None),x=alt.X('Valor:Q',title=medida),tooltip=['Modelo',alt.Tooltip('Valor:Q',format='.3f',title=medida)])
            barras=base.mark_bar(cornerRadiusEnd=4,size=30).encode(color=alt.Color('Modelo:N',scale=alt.Scale(domain=['Regresión lineal','Referencia (media)'],range=[AZUL,ORO]),legend=None))
            cero=alt.Chart(pd.DataFrame({'Cero':[0]})).mark_rule(color='#8293A5').encode(x='Cero:Q')
            grafica((barras+cero).properties(height=170),'chart_regresion','Comparación agregada de regresión y referencia. Los R² negativos se muestran sin recortarlos.')
        if t['mae_h']>=b['mae_h']:
            mensaje('El promedio fue una mejor referencia por error medio.',
                    f'La regresión se desvió {t["mae_h"]:.2f} horas en promedio, frente a {b["mae_h"]:.2f} de la referencia. Estas dos variables aportaron poca capacidad predictiva en los {g["n_test"]} casos de prueba.')
        else:
            mensaje('La regresión redujo el error medio en esta prueba.',
                    'Es una comparación exploratoria con pocos casos. Hace falta comprobar si se mantiene con otras respuestas.')
    with st.expander('Cómo interpretar R², MAE y RMSE',expanded=True):
        st.write('R² compara el error cuadrático del modelo con la variación de las horas observadas en el conjunto evaluado. Un 1 indica ajuste perfecto; 0 equivale a usar la media de ese conjunto y un valor negativo indica mayor error que esa referencia matemática.')
        st.write('La referencia de la tabla usa la media de entrenamiento, por eso su R² de prueba también puede ser negativo. Un R² de −0.245 no significa “−24.5 % de precisión”. Si las horas evaluadas son constantes, R² se muestra como no definido.')
        st.write('MAE indica cuánto se desvían las predicciones en promedio, en horas. RMSE también se expresa en horas, pero penaliza más las equivocaciones grandes. Un error medio no garantiza ese margen para cada persona.')
    with st.expander('Validación, partición y límites del ejercicio'):
        cv=pd.DataFrame([{'Modelo':m['modelo'],'R² CV medio':m['cv']['r2_media'],'DE de R²':m['cv']['r2_sd'],
                          'MAE CV (horas)':m['cv']['mae_media_h'],'RMSE CV (horas)':m['cv']['rmse_media_h'],
                          'Pliegues R² válidos':f'{m["cv"]["folds_r2_validos"]}/{g["n_folds"]}'} for m in g['modelos']])
        st.dataframe(cv.round(3),hide_index=True,width='stretch')
        st.write(f'Se usaron {g["n"]} casos completos y se excluyeron {g["n_excluidos"]}. La partición 75/25 y los cinco pliegues se fijaron con semilla 42. La escala se aprende en cada entrenamiento; la prueba se mantiene fuera de la validación.')
        st.write('R² se calcula por pliegue y después se resume. Con tres o cuatro respuestas por pliegue puede variar mucho: si las horas son parecidas, incluso un error pequeño pesa bastante. La desviación entre pliegues no es un intervalo de confianza. Se omite del promedio cualquier R² no definido y se conserva ese dato en las tablas del análisis.')
        st.write('Este ejercicio estudia intensidad de uso de IA. Para evaluar desempeño académico harían falta calificaciones numéricas independientes. No se ajustaron parámetros ni se cambiaron las particiones buscando un R² favorable.')
    st.download_button('Descargar métricas de regresión (CSV)',tabla.to_csv(index=False).encode('utf-8-sig'),file_name='regresion_prueba_agregada.csv',mime='text/csv')


def mostrar_busquedas(ajuste, explicacion):
    nombres = {'modelo__n_neighbors': 'vecinos', 'modelo__weights': 'voto',
               'modelo__p': 'distancia', 'modelo__n_clusters': 'grupos',
               'modelo__init': 'inicio', 'modelo__n_init': 'reinicios'}
    legibles = {'uniform': 'igual', 'distance': 'por cercanía', 'random': 'al azar'}
    with st.expander('Ver GridSearchCV y RandomizedSearchCV'):
        st.write(explicacion)
        filas = []
        for fila in ajuste['busquedas']:
            valores = {nombres[k]: v for k, v in fila['parametros'].items()}
            if 'distancia' in valores:
                valores['distancia'] = {1: 'Manhattan', 2: 'euclidiana'}[valores['distancia']]
            config = ' · '.join(f'{k} {legibles.get(v, v)}' for k, v in valores.items())
            filas.append({'Búsqueda': fila['metodo'], 'Combinaciones': fila['configuraciones'],
                          'Configuración': config, f'{ajuste["metrica"]} media CV': fila['media'],
                          'Desviación CV': fila['desviacion'],
                          'Pliegues válidos': f'{fila["pliegues_validos"]}/{ajuste["n_folds"]}'})
        st.dataframe(pd.DataFrame(filas).round(3), hide_index=True, width='stretch')
        if ajuste.get('aplicado', True):
            st.caption(f'Se conservó la configuración de {ajuste["mejor_metodo"]}. En caso de empate en media y pliegues válidos, se conserva GridSearchCV.')
        else:
            st.caption('Se muestran los grupos de la exploración sobre la muestra completa porque la búsqueda no produjo una configuración con silueta válida.')


def modelos(r):
    s=r['supervisado'];c=r['clusters']
    titulo('EVALUACIÓN EXPLORATORIA','Qué muestran\nlos modelos.',
           'Comparamos tres ejercicios: distinguir modalidades de uso, estimar horas de IA y explorar agrupaciones. Cada uno responde una pregunta distinta y usa sus propias métricas.')
    tabs=st.tabs(['Clasificación','Regresión (R²)','Agrupación exploratoria'])
    with tabs[0]:
        if s['estado']!='ok':
            st.info('No hay suficientes respuestas para evaluar la clasificación. Puedes consultar la agrupación en la otra pestaña.')
        else:
            ajuste = s.get('ajuste')
            prueba = ajuste['test'] if ajuste else s['test']
            candidato = 'KNN ajustado' if ajuste else s['seleccionado']
            metricas([('Respuestas que se pudieron clasificar',str(s['n_etiquetados']),'casos',f'{s["n_excluidos"]} respuestas ambiguas fuera del modelo'),
                      ('Entrenamiento',str(s['n_train']),'casos','Selección y validación cruzada'),
                      ('Prueba reservada',str(s['n_test']),'casos','Se revisa después de elegir el modelo'),
                      ('Validación estratificada',str(s['n_folds']),'pliegues','Cada pliegue aprende sus transformaciones')])
            if not s['supera_baseline_cv']:
                mensaje('La referencia mayoritaria tuvo el mejor F1 en la comparación inicial.',
                        'En las configuraciones fijas, predecir siempre la categoría más frecuente rindió mejor en validación. La prueba de KNN ajustado se muestra por separado abajo.')
            else:
                mensaje('Hace falta probarlo con más datos.','Un F1 mayor en esta evaluación no garantiza que el modelo funcione igual con otros estudiantes.')
            if ajuste:
                mostrar_busquedas(ajuste, 'Ajustamos KNN dentro del conjunto de entrenamiento. Cada intento cambia la cantidad de vecinos, la forma de medir su distancia y el peso de su voto. Usamos F1 para comparar los intentos y guardamos la prueba para el final.')
                f1_knn = max(fila['media'] for fila in ajuste['busquedas'])
                f1_referencia = next(fila['cv_f1'] for fila in s['cv'] if fila['modelo'] == 'Baseline (mayoría)')
                st.caption(f'En los pliegues de entrenamiento, el mejor KNN obtuvo F1 de {f1_knn:.3f} y la referencia mayoritaria obtuvo {f1_referencia:.3f}. Abajo se muestra la prueba reservada.')
            with st.container(border=True,key='panel_modelos_cv'):
                seccion('Comparación con configuraciones fijas','La etiqueta distingue uso mixto (1) de uso declarado solo como guía o atajo (0). La respuesta que define esa etiqueta queda fuera de los predictores.')
                st.html(f'<div class="pasos"><span class="paso"><b>{s["n_train"]}</b> entrenamiento</span><span class="paso">CV de <b>{s["n_folds"]}</b> folds</span><span class="paso">Selección por <b>F1</b></span><span class="paso"><b>{s["n_test"]}</b> prueba</span></div>')
                medida=st.segmented_control('Métrica de comparación',['F1','Accuracy'],default='F1',required=True,key='metrica_modelos')
                campo='cv_f1' if medida=='F1' else 'cv_accuracy';sd=campo+'_sd'
                df=pd.DataFrame(s['cv']);df['Inferior']=df[campo]-df[sd];df['Superior']=df[campo]+df[sd]
                df['Tipo']=df['modelo'].map(lambda x:'Referencia mayoritaria' if x.startswith('Baseline') else 'Clasificador')
                base=alt.Chart(df).encode(y=alt.Y('modelo:N',title=None,sort=alt.SortField(field=campo,order='descending')),
                                         tooltip=[alt.Tooltip('modelo:N',title='Modelo'),alt.Tooltip(f'{campo}:Q',format='.3f',title=f'{medida} medio'),alt.Tooltip(f'{sd}:Q',format='.3f',title='DE entre folds')])
                barra=base.mark_bar(cornerRadiusEnd=4,size=24).encode(x=alt.X(f'{campo}:Q',title=f'{medida} medio ± desviación entre folds',scale=alt.Scale(domain=[-.03,1.08])),color=alt.Color('Tipo:N',scale=alt.Scale(domain=['Referencia mayoritaria','Clasificador'],range=[ORO,AZUL]),legend=alt.Legend(orient='bottom')))
                error=base.mark_rule(color='#536D83',strokeWidth=1.5).encode(x='Inferior:Q',x2='Superior:Q')
                grafica((barra+error).properties(height=260),'chart_cv','Comparación de modelos y baseline en validación de entrenamiento, con dispersión entre folds.')
                st.caption('La desviación entre folds no es un intervalo de confianza. Cambiar la métrica de la gráfica no vuelve a seleccionar el candidato.')
            izq,der=st.columns([1.05,1])
            with izq,st.container(border=True,key='panel_modelos_test'):
                seccion('Prueba reservada',candidato)
                cm=prueba['confusion'];filas=[{'Real':['Exclusiva','Mixta'][i],'Predicción':['Exclusiva','Mixta'][j],'Casos':cm[i][j]} for i in range(2) for j in range(2)]
                base=alt.Chart(pd.DataFrame(filas)).encode(x=alt.X('Predicción:N',title='Predicción',axis=alt.Axis(labelAngle=0)),y=alt.Y('Real:N',title='Modalidad declarada'))
                cuad=base.mark_rect(cornerRadius=4,stroke='white',strokeWidth=4).encode(color=alt.Color('Casos:Q',scale=alt.Scale(range=['#EAF0F7',AZUL]),legend=None),tooltip=['Real','Predicción','Casos'])
                tex=base.mark_text(fontSize=24,font=FONT).encode(text='Casos:Q',color=alt.condition(alt.datum.Casos>2,alt.value('white'),alt.value('#285A88')))
                grafica((cuad+tex).properties(height=240),'chart_confusion','Matriz de confusión agregada de la prueba reservada.')
            with der,st.container(border=True,key='panel_modelos_metricas'):
                seccion('La prueba tiene pocos casos','Este resultado puede cambiar mucho con una sola respuesta.')
                filas=[{'Indicador':nombre,'Candidato':prueba[key],'Baseline':s['baseline_test'][key]} for key,nombre in [('accuracy','Accuracy'),('precision','Precisión'),('recall','Recall'),('f1','F1')]]
                st.dataframe(pd.DataFrame(filas),hide_index=True,width='stretch',column_config={'Candidato':st.column_config.NumberColumn(format='%.3f'),'Baseline':st.column_config.NumberColumn(format='%.3f')})
                st.html(f'<div class="quiet">Con {s["n_test"]} casos de prueba, una sola predicción cambia accuracy en <b>{s["test_sensible_pp"]:.1f} puntos porcentuales</b>.</div>')
            with st.expander('Ver tabla de validación y definición del experimento'):
                tabla=pd.DataFrame(s['cv']).drop(columns='fold_f1').rename(columns={'modelo':'Modelo','cv_accuracy':'Accuracy CV','cv_accuracy_sd':'DE accuracy','cv_f1':'F1 CV','cv_f1_sd':'DE F1'})
                st.dataframe(tabla.round(3),hide_index=True,width='stretch')
                st.write('Escala e imputación KNN, vectorización TF-IDF y PCA se ajustan únicamente en entrenamiento dentro de cada fold. No se usa la prueba para seleccionar el candidato. La tarea es clasificar una modalidad declarada, no medir aprendizaje efectivo.')
    with tabs[1]:
        regresion(r)
    with tabs[2]:
        if c['estado']!='ok':st.info('No hay suficientes observaciones para explorar agrupaciones.')
        else:
            ajuste = c.get('ajuste')
            st.write('')
            metricas([('Respuestas con datos de entorno',str(c['n']),'casos','Sin completar respuestas de bienestar'),
                      ('Grupos de K-Means',str(c['k']),'grupos','Elegidos por validación' if ajuste and ajuste['aplicado'] else 'Exploración en la muestra'),
                      ('Silueta en la muestra',f'{c["silhouette"]:.3f}','','Configuración final sobre todos los casos observados'),
                      ('Varianza PCA',f'{100*sum(c["pca_varianza"]):.1f}','%','Primeros dos componentes')])
            if ajuste:
                mostrar_busquedas(ajuste, 'Probamos distintos números de grupos y formas de iniciar K-Means. En cada pliegue el modelo aprende los centros con una parte de los datos y asigna los casos reservados al centro más cercano. Medimos la separación por silueta. Si un pliegue no permite calcularla, se penaliza con −1 al comparar configuraciones.')
            a,b=st.columns(2)
            with a,st.container(border=True,key='panel_clusters_k'):
                seccion('Exploración del número de grupos','Este gráfico mide la silueta en toda la muestra con parámetros fijos. La tabla de arriba usa pliegues de validación.')
                d=pd.DataFrame([{'k':int(key),'Silhouette':v} for key,v in c['siluetas'].items()])
                grafica(alt.Chart(d).mark_line(point=True,color=AZUL).encode(x=alt.X('k:O',title='k ensayado',axis=alt.Axis(labelAngle=0)),y=alt.Y('Silhouette:Q',title=None,scale=alt.Scale(zero=False)),tooltip=['k',alt.Tooltip('Silhouette:Q',format='.3f')]).properties(height=240),'chart_siluetas','Puntuación silhouette para cada número de grupos ensayado.')
            with b,st.container(border=True,key='panel_clusters_tamanos'):
                seccion('Cuántas personas hay en cada grupo')
                tamanos={f'Grupo {key}':v for key,v in c['tamanos'].items() if v>=3}
                pequenos=sum(v for v in c['tamanos'].values() if v<3)
                if pequenos:tamanos['Grupos pequeños']=pequenos
                d=pd.DataFrame([{'Grupo':key,'Casos':v} for key,v in tamanos.items()])
                grafica(alt.Chart(d).mark_bar(color=TURQUESA,cornerRadiusEnd=4,size=50).encode(x=alt.X('Grupo:N',title=None,axis=alt.Axis(labelAngle=0)),y=alt.Y('Casos:Q',title=None),tooltip=['Grupo','Casos']).properties(height=240),'chart_clusters','Tamaños de grupos; los subgrupos pequeños se muestran agrupados y sin descripciones individuales.')
            mensaje('Los casos extremos pueden explicar parte de la separación.','Estos grupos son exploratorios. No sirven para diagnosticar o asignar apoyos. Tampoco se muestran perfiles si un grupo, o el resto de la muestra, tiene menos de tres personas.')


def documentacion(r):
    titulo('DOCUMENTACIÓN Y MÉTODO','Los informes\ndel proyecto.',
           'Descarga los informes y las tablas de resultados. Ambos documentos usan los mismos cálculos que aparecen en este panel.')
    docs=documentos_publicos(ROOT)
    a,b=st.columns(2)
    for col,key,numero,nombre,descripcion in [
        (a,'tecnica','01','Documentación\ntécnica','Explica cómo se limpiaron los datos, cómo se analizó el texto y cómo se evaluaron los modelos.'),
        (b,'negocio','02','Documentación\nde negocio','Reúne los indicadores, los hallazgos y las propuestas de seguimiento, junto con sus límites.')]:
        with col,st.container(border=True,key=f'panel_doc_{key}'):
            st.html(f'<div class="doc-tag">{numero} / INFORME PDF</div><div class="doc-titulo">{escape(nombre).replace(chr(10),"<br>")}</div><div class="doc-texto">{escape(descripcion)}</div>')
            path=docs[key]
            if path.is_file():
                st.download_button('Descargar informe '+('técnico' if key=='tecnica' else 'de negocio'),data=path.read_bytes(),file_name=path.name,mime='application/pdf',key=f'descarga_{key}',type='primary',width='stretch')
            else:st.info('Este informe todavía no se ha generado en este equipo.')
    st.write('')
    with st.container(border=True,key='panel_doc_datos'):
        seccion('Tablas de resultados','Son resúmenes del grupo. No incluyen números de cuenta, fechas de respuesta ni textos individuales.')
        a,b=st.columns(2)
        with a:
            st.download_button('Descargar tabla de herramientas (CSV)',tabla_herramientas(r).drop(columns='Clave').to_csv(index=False).encode('utf-8-sig'),file_name='herramientas_agregadas.csv',mime='text/csv',width='stretch')
        with b:
            tabla=pd.DataFrame(r['descriptivos']).T
            st.download_button('Descargar descriptivos (CSV)',tabla.to_csv(index_label='Variable').encode('utf-8-sig'),file_name='descriptivos_agregados.csv',mime='text/csv',width='stretch')
    with st.expander('Cómo se construyó el estudio',expanded=True):
        st.markdown('1. **Limpiar en Python.** Validamos cuentas y fechas, unificamos unidades y revisamos alias de herramientas con patrones y similitud de nombres.\n2. **Explorar.** Calculamos indicadores, distribuciones y asociaciones con las respuestas disponibles.\n3. **Ajustar modelos.** Probamos GridSearchCV y RandomizedSearchCV en K-Means y KNN con el mismo conjunto de pliegues para cada tarea. KNN también se compara con la referencia mayoritaria en una prueba reservada.\n4. **Presentar.** Publicamos métricas agregadas y el número de respuestas que sustenta cada resultado.')
    with st.expander('Cobertura y calidad de los datos'):
        m=r['muestra'];q=r['calidad']
        if 'limpieza' in r:
            ia = r['limpieza']['ia']['columnas_cubiertas']
            bienestar = r['limpieza']['bienestar']['columnas_cubiertas']
            st.write(f'El código de Python trata las {ia} columnas del formulario de IA y las {bienestar} seleccionadas del formulario de bienestar.')
        st.dataframe(pd.DataFrame([{'Fuente / control':'Respuestas de IA','Casos':m['ia']},{'Fuente / control':'Respuestas de bienestar','Casos':m['bienestar']},{'Fuente / control':'Casos emparejados','Casos':m['emparejados']},{'Fuente / control':'Sin encuesta complementaria','Casos':m['solo_ia']},{'Fuente / control':'Textos abiertos de IA ausentes','Casos':q['textos_ia_ausentes']}]),hide_index=True,width='stretch')
        st.write('La ausencia de encuesta no se transforma en bienestar neutral. Las metas de negocio son propuestas de seguimiento, no políticas institucionales aprobadas.')
    with st.expander('Reproducibilidad'):
        st.caption('Metodología '+r['metodologia']['version']+' · Semilla '+str(r['metodologia']['semilla']))
        st.dataframe(pd.DataFrame(list(r['proveniencia']['versiones'].items()),columns=['Biblioteca','Versión']),hide_index=True,width='stretch')
        st.write('Las versiones están anotadas en los requisitos del proyecto. Navegar por este panel solo consulta los resultados ya calculados; no vuelve a entrenar los modelos.')


def main():
    try:
        r=cargar(RESUMEN.stat().st_mtime_ns if RESUMEN.exists() else 0)
    except (ValueError,OSError):
        st.error('No pudimos abrir los resultados del estudio. Revisa el archivo de resumen o vuelve a ejecutar el análisis.')
        st.stop()
    m=r['muestra']
    with st.sidebar:
        st.html('<div class="marca"><div class="sello">MAC</div><div><strong>IA en contexto</strong><span>PROYECTO DE MAC</span></div></div><div class="nav-label">EL ESTUDIO</div>')
        vista=st.radio('Sección del dashboard',VISTAS,key='vista',label_visibility='collapsed')
        st.html(f'<div class="sidebar-estudio"><strong>Sobre las encuestas</strong><div class="muestra-side"><div><b>{m["ia"]}</b><span>respuestas de IA</span></div><div><b>{m["emparejados"]}</b><span>emparejadas</span></div></div><p>Uso de IA y vida universitaria entre estudiantes de MAC.</p></div><div class="side-pie">SISTEMAS INTELIGENTES<br>FES Acatlán · UNAM<br>Estudio exploratorio</div>')
    fecha=r['proveniencia']['fecha'][:10]
    try:
        f=date.fromisoformat(fecha);fecha=f'{f.day:02d}.{f.month:02d}.{f.year}'
    except (ValueError,TypeError):fecha='Fecha no disponible'
    st.html(f'<div class="topline"><span class="ruta">ESTUDIO ACADÉMICO / {escape(vista.upper())}</span><span class="estado"><i></i> Datos del estudio · {escape(fecha)}</span></div>')
    {'Panorama':panorama,'Uso de IA':uso_ia,'Entorno y bienestar':entorno,'Modelos':modelos,'Documentación':documentacion}[vista](r)
    st.html(f'<div class="pie-dashboard"><span>MAC · Sistemas Inteligentes</span><span>n = {m["ia"]} IA / {m["emparejados"]} emparejados · Solo resultados agregados</span></div>')


if __name__=='__main__':main()
