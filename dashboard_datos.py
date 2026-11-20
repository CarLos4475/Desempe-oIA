"""Adaptador de agregados públicos. No importa el análisis ni abre las encuestas."""
import json
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

VERSION_ADAPTADOR=3

NOMBRES_HERRAMIENTAS={'gemini':'Gemini','chatgpt':'ChatGPT','claude':'Claude',
                     'deepseek':'DeepSeek','copilot':'Copilot','notebooklm':'NotebookLM',
                     'qwen':'Qwen','perplexity':'Perplexity'}
NOMBRES_VARIABLES={'horas_ia_dia':'Horas de IA','semestre_inicio':'Inicio de uso',
                   'total_herramientas':'Herramientas','traslado_min':'Traslado',
                   'score_beneficio_ia':'Polaridad IA','score_bienestar':'Polaridad entorno','edad':'Edad'}
INDIVIDUALES={'cuenta','cuentas','timestamp_ia','timestamp_bie','corpus_ia','corpus_bie',
              'datos_individuales','respuestas_individuales','guia_o_atajo_raw',
              'reemplazo_laboral_raw','herramientas_frecuencia'}
ESTADISTICOS=('n','media','mediana','sd','min','max','q1','q3')
MODALIDADES=('Híbrido','Guía','Atajo','Contextual','No clasificable')
REEMPLAZO=('Sí','No','Parcial / Depende','Indeciso')
MODELOS=('Regresión logística','Random Forest','SVM','KNN','Baseline (mayoría)')
PREGUNTAS=('fase_estudio','cambio_estudio','proceso_verificacion','impacto_tiempo',
           'diferencia_calificaciones','independencia_resolucion','impacto_estres',
           'reglas_personales','pensamiento_critico','motivo_principal','ambiente_hogar',
           'calidad_sueno','frecuencia_desanimo','irritabilidad','dificultad_concentracion')


def _validar_privacidad(obj):
    if isinstance(obj,dict):
        if INDIVIDUALES.intersection(obj):
            raise ValueError('Se detectaron campos individuales. Use únicamente el resumen público.')
        for value in obj.values():_validar_privacidad(value)
    elif isinstance(obj,list):
        for value in obj:_validar_privacidad(value)


def _numeros(obj,claves,enteros=(),nulos=False):
    salida={}
    for k in claves:
        v=obj[k]
        if v is None and nulos and k not in enteros:
            salida[k]=None
            continue
        if type(v) not in (int,float) or not math.isfinite(v):raise ValueError
        if k in enteros and (type(v) is not int or v<0):raise ValueError
        salida[k]=v
    return salida


def _metricas(obj):
    r=_numeros(obj,('accuracy','precision','recall','f1'))
    if any(not 0<=v<=1 for v in r.values()):raise ValueError
    cm=obj['confusion']
    if (not isinstance(cm,list) or len(cm)!=2 or
            any(not isinstance(fila,list) or len(fila)!=2 or
                any(type(x) is not int or x<0 for x in fila) for fila in cm)):raise ValueError
    r['confusion']=cm
    return r


def _ajuste(obj, metrica):
    metodos = {'GridSearchCV', 'RandomizedSearchCV'}
    n_folds = _numeros(obj, ('n_folds',), enteros=('n_folds',))['n_folds']
    if obj['metrica'] != metrica or obj['mejor_metodo'] not in metodos or n_folds < 2:
        raise ValueError
    parametros = ({'modelo__n_neighbors': (1, 3, 5, 7), 'modelo__p': (1, 2),
                   'modelo__weights': ('uniform', 'distance')} if metrica == 'F1' else
                  {'modelo__n_clusters': (2, 3, 4, 5), 'modelo__n_init': (10, 20),
                   'modelo__init': ('k-means++', 'random')})
    filas = []
    for fila in obj['busquedas']:
        vals = _numeros(fila, ('media', 'desviacion', 'configuraciones', 'pliegues_validos'),
                        enteros=('configuraciones', 'pliegues_validos'))
        if (not (-1 if metrica == 'Silueta' else 0) <= vals['media'] <= 1 or vals['desviacion'] < 0 or
                not 0 <= vals['pliegues_validos'] <= n_folds or vals['configuraciones'] < 1):
            raise ValueError
        elegidos = {nombre: fila['parametros'][nombre] for nombre in parametros}
        if any(valor not in parametros[nombre] for nombre, valor in elegidos.items()):
            raise ValueError
        filas.append({**vals, 'metodo': fila['metodo'], 'parametros': elegidos})
    if len(filas) != 2 or {fila['metodo'] for fila in filas} != metodos:
        raise ValueError
    return {'metrica': metrica, 'n_folds': n_folds, 'busquedas': filas,
            'mejor_metodo': obj['mejor_metodo']}


def _supervisado(obj):
    if obj['estado']=='insuficiente':
        return {'estado':'insuficiente','motivo':'No hay suficientes respuestas por clase para evaluar esta parte del estudio.'}
    if obj['estado']!='ok':raise ValueError
    keys=('n_etiquetados','n_excluidos','n_train','n_test','n_folds')
    r=_numeros(obj,keys,enteros=keys)
    if r['n_train']+r['n_test']!=r['n_etiquetados'] or r['n_test']<1 or r['n_folds']<2:raise ValueError
    if obj['seleccionado'] not in MODELOS[:-1] or type(obj['supera_baseline_cv']) is not bool:raise ValueError
    r.update(estado='ok',seleccionado=obj['seleccionado'],supera_baseline_cv=obj['supera_baseline_cv'])
    cv=[]
    for fila in obj['cv']:
        if fila['modelo'] not in MODELOS:raise ValueError
        item=_numeros(fila,('cv_accuracy','cv_accuracy_sd','cv_f1','cv_f1_sd'))
        if not all(0<=item[k]<=1 for k in ('cv_accuracy','cv_f1')) or min(item.values())<0:raise ValueError
        folds=fila['fold_f1']
        if not isinstance(folds,list) or len(folds)!=r['n_folds'] or any(type(x) not in (int,float) or not 0<=x<=1 for x in folds):raise ValueError
        item.update(modelo=fila['modelo'],fold_f1=folds);cv.append(item)
    if 'Baseline (mayoría)' not in [x['modelo'] for x in cv] or r['seleccionado'] not in [x['modelo'] for x in cv]:raise ValueError
    r.update(cv=cv,test=_metricas(obj['test']),baseline_test=_metricas(obj['baseline_test']),test_sensible_pp=100/r['n_test'])
    if 'ajuste' in obj:
        ajuste = _ajuste(obj['ajuste'], 'F1')
        ajuste['test'] = _metricas(obj['ajuste']['test'])
        if ajuste['n_folds'] != r['n_folds'] or sum(map(sum, ajuste['test']['confusion'])) != r['n_test']:
            raise ValueError
        r['ajuste'] = ajuste
    return r


def _metricas_regresion(obj):
    r=_numeros(obj,('r2','mae_h','rmse_h'),nulos=True)
    if r['r2'] is not None and r['r2']>1+1e-10:raise ValueError
    if any(r[k] is None or r[k]<0 for k in ('mae_h','rmse_h')):raise ValueError
    return r


def _regresion(obj):
    if obj['estado']=='insuficiente':return {'estado':'insuficiente'}
    if obj['estado']!='ok':raise ValueError
    claves=('n','n_excluidos','n_train','n_test','n_folds')
    r=_numeros(obj,claves,enteros=claves)
    if r['n_train']+r['n_test']!=r['n'] or r['n_test']<2 or r['n_folds']<2:raise ValueError
    modelos=[]
    for m in obj['modelos']:
        if m['modelo'] not in ('Regresión lineal','Referencia (media)'):raise ValueError
        cv=_numeros(m['cv'],('r2_media','r2_sd','mae_media_h','rmse_media_h','folds_r2_validos'),enteros=('folds_r2_validos',),nulos=True)
        if (cv['r2_media'] is not None and cv['r2_media']>1+1e-10 or
            cv['r2_sd'] is not None and cv['r2_sd']<0 or
            any(cv[k] is None or cv[k]<0 for k in ('mae_media_h','rmse_media_h'))):raise ValueError
        folds=[{**_numeros(f,('n',),enteros=('n',)),**_metricas_regresion(f)} for f in m['folds']]
        if (len(folds)!=r['n_folds'] or sum(f['n'] for f in folds)!=r['n_train'] or
            any(f['n']<2 for f in folds) or cv['folds_r2_validos']!=sum(f['r2'] is not None for f in folds)):
            raise ValueError
        modelos.append({'modelo':m['modelo'],'cv':cv,'folds':folds,
                        'entrenamiento':_metricas_regresion(m['entrenamiento']),
                        'prueba':_metricas_regresion(m['prueba'])})
    if len(modelos)!=2 or {m['modelo'] for m in modelos}!={'Regresión lineal','Referencia (media)'}:raise ValueError
    return {**r,'estado':'ok','modelos':modelos}


def tabla_regresion(r:dict)->pd.DataFrame:
    return pd.DataFrame([{'Modelo':m['modelo'],'R²':m['prueba']['r2'],
                          'MAE (horas)':m['prueba']['mae_h'],'RMSE (horas)':m['prueba']['rmse_h']}
                         for m in r['regresion']['modelos']])


def _clusters(obj):
    if obj['estado']=='insuficiente':return {'estado':'insuficiente'}
    if obj['estado']!='ok':raise ValueError
    r=_numeros(obj,('n','k','silhouette'),enteros=('n','k'))
    if not 2<=r['k']<=5 or not -1<=r['silhouette']<=1:raise ValueError
    siluetas={k:v for k,v in obj['siluetas'].items() if k in ('2','3','4','5')}
    tamanos={k:v for k,v in obj['tamanos'].items() if re.fullmatch(r'\d+',k)}
    var=obj['pca_varianza']
    if (not siluetas or any(type(v) not in (int,float) or not -1<=v<=1 for v in siluetas.values()) or
        any(type(v) is not int or v<1 for v in tamanos.values()) or sum(tamanos.values())!=r['n'] or
        not isinstance(var,list) or len(var)!=2 or any(type(x) not in (int,float) or not 0<=x<=1 for x in var)):raise ValueError
    r.update(estado='ok',siluetas=siluetas,tamanos=tamanos,pca_varianza=var)
    if 'ajuste' in obj:
        ajuste = _ajuste(obj['ajuste'], 'Silueta')
        aplicado = obj['ajuste']['aplicado']
        if type(aplicado) is not bool:
            raise ValueError
        r['ajuste'] = {**ajuste, 'aplicado': aplicado}
    return r


def leer_resumen(ruta:Path) -> dict:
    try:
        r=json.loads(Path(ruta).read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise ValueError('No se encontró el resumen verificado. Ejecute el análisis antes de abrir el dashboard.') from None
    except (json.JSONDecodeError,UnicodeDecodeError):
        raise ValueError('El archivo de resultados no es un JSON válido.') from None
    _validar_privacidad(r)
    necesarias={'muestra','kpis','descriptivos','herramientas','tipo_uso','reemplazo',
                'supervisado','regresion','clusters','proveniencia','metodologia','calidad',
                'correlacion_traslado_ia','correlacion_spearman','tfidf_top','semestre_inicio'}
    if not isinstance(r,dict) or not necesarias.issubset(r):
        raise ValueError('El resumen está incompleto. Regenera los resultados con el análisis del proyecto.')
    m=r['muestra']
    try:
        if (not isinstance(m['ia'],int) or m['ia']<=0 or m['emparejados']<0 or
                m['emparejados']>m['ia'] or m['emparejados']>m['bienestar'] or
                m['solo_ia']!=m['ia']-m['emparejados']):
            raise ValueError
        if sum(r['tipo_uso'].values())!=m['ia']:
            raise ValueError
        if any(not isinstance(v,int) or v<0 or v>m['ia'] for v in r['herramientas'].values()):
            raise ValueError
    except (KeyError,TypeError,AttributeError,ValueError):
        raise ValueError('Los totales de la muestra son inconsistentes. Revise el análisis.') from None
    # Proyectar listas permitidas: ningún comentario o columna añadida llega a la UI o CSV.
    try:
        limpio={'muestra':_numeros(m,('ia','bienestar','emparejados','solo_ia','solo_bienestar'),enteros=tuple(m))}
        campos_kpi=('adopcion_observada_n','adopcion_observada_pct','mediana_ia_h',
                     'guia_hibrido_pct','hibrido_pct','multiherramienta_pct','multiherramienta_n',
                     'traslado_mediana_min','traslado_mayor_90_n','reemplazo_si_pct')
        limpio['kpis']=_numeros(r['kpis'],campos_kpi,enteros=('adopcion_observada_n','multiherramienta_n','traslado_mayor_90_n'))
        limpio['descriptivos']={v:_numeros(r['descriptivos'][v],ESTADISTICOS,enteros=('n',),nulos=True) for v in NOMBRES_VARIABLES}
        # Las tarjetas de contexto necesitan duración observada para poder interpretarse.
        if limpio['descriptivos']['traslado_min']['n']<1 or any(limpio['descriptivos']['traslado_min'][k] is None for k in ESTADISTICOS):raise ValueError
        for campo,permitidos in [('herramientas',NOMBRES_HERRAMIENTAS),('tipo_uso',MODALIDADES),('reemplazo',REEMPLAZO)]:
            limpio[campo]=_numeros({k:r[campo].get(k,0) for k in permitidos},tuple(permitidos),enteros=tuple(permitidos))
        if sum(limpio['tipo_uso'].values())!=m['ia'] or sum(limpio['reemplazo'].values())!=m['ia']:raise ValueError
        limpio['supervisado']=_supervisado(r['supervisado']);limpio['clusters']=_clusters(r['clusters'])
        limpio['regresion']=_regresion(r['regresion'])
        if limpio['regresion']['estado']=='ok' and limpio['regresion']['n']+limpio['regresion']['n_excluidos']!=m['ia']:raise ValueError
        limpio['correlacion_traslado_ia']=_numeros(r['correlacion_traslado_ia'],('n','rho','p'),enteros=('n',),nulos=True)
        limpio['correlacion_spearman']={x:_numeros(r['correlacion_spearman'][x],tuple(NOMBRES_VARIABLES),nulos=True) for x in NOMBRES_VARIABLES}
        limpio['tfidf_top']={k:v for k,v in r['tfidf_top'].items() if re.fullmatch(r'[a-z ]{1,64}',k) and type(v) in (int,float) and math.isfinite(v) and 0<=v<=1}
        limpio['semestre_inicio']={k:v for k,v in r['semestre_inicio'].items() if re.fullmatch(r'[1-9]',k) and type(v) is int and 0<=v<=m['ia']}
        limpio['calidad']=_numeros(r['calidad'],('textos_ia_ausentes',),enteros=('textos_ia_ausentes',))
        if 'limpieza' in r:
            limpio['limpieza'] = {
                fuente: _numeros(r['limpieza'][fuente], ('columnas_cubiertas',), enteros=('columnas_cubiertas',))
                for fuente in ('ia', 'bienestar')
            }
        limpio['polaridad_por_pregunta']={k:_numeros(v,('n','media','n_score_cero'),enteros=('n','n_score_cero'),nulos=True) for k,v in r.get('polaridad_por_pregunta',{}).items() if k in PREGUNTAS}
        fecha=r['proveniencia']['fecha'];datetime.fromisoformat(fecha)
        versiones={k:v for k,v in r['proveniencia']['versiones'].items() if k in ('pandas','numpy','scikit-learn','scipy','matplotlib') and isinstance(v,str) and re.fullmatch(r'[0-9a-zA-Z.+_-]{1,30}',v)}
        limpio['proveniencia']={'fecha':fecha,'versiones':versiones}
        version=r['metodologia']['version']
        if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError
        limpio['metodologia']={'version':version,**_numeros(r['metodologia'],('semilla',),enteros=('semilla',))}
    except (KeyError,TypeError,AttributeError,ValueError):
        raise ValueError('El resumen está incompleto o no cumple el esquema público. Vuelve a generar los resultados.') from None
    return limpio


def tabla_herramientas(r:dict,seleccion:list[str]|None=None)->pd.DataFrame:
    claves=list(r['herramientas']) if seleccion is None else seleccion
    filas=[{'Clave':k,'Herramienta':NOMBRES_HERRAMIENTAS.get(k,k),
            'Respuestas':r['herramientas'][k],
            'Porcentaje':100*r['herramientas'][k]/r['muestra']['ia']}
           for k in claves if k in r['herramientas']]
    return pd.DataFrame(filas,columns=['Clave','Herramienta','Respuestas','Porcentaje']).sort_values('Respuestas',ascending=False)


def tabla_modalidades(r:dict)->pd.DataFrame:
    return pd.DataFrame([{'Modalidad':k,'Respuestas':v,'Porcentaje':100*v/r['muestra']['ia']}
                         for k,v in r['tipo_uso'].items()])


def documentos_publicos(root:Path)->dict[str,Path]:
    base=Path(root)/'docs'
    return {'tecnica':base/'DOCUMENTACION_TECNICA.pdf',
            'negocio':base/'DOCUMENTACION_NEGOCIO.pdf'}
