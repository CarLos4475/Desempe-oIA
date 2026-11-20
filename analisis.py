"""Análisis local reproducible. Los archivos exportados contienen solo agregados.

La clasificación predice modalidad declarada de uso, no rendimiento académico.
Las puntuaciones léxicas son descripciones exploratorias, no diagnósticos.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from scipy.sparse import csr_matrix
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import KNNImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             mean_absolute_error, precision_score, r2_score,
                             recall_score, root_mean_squared_error, silhouette_score)
from sklearn.model_selection import (GridSearchCV, KFold, ParameterGrid,
                                     RandomizedSearchCV, StratifiedKFold,
                                     cross_validate, train_test_split)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.svm import SVC

from limpieza_encuestas import detectar_herramientas, limpiar_fuentes

ARCHIVO_IA = 'Desempeño académico por el uso de IA (Respuestas).xlsx'
ARCHIVO_BIE = 'Cuestionario_ Entorno Universitario y Bienestar.csv'
COLS_IA = ['timestamp_ia','cuenta','herramientas_frecuencia','fase_estudio',
           'cambio_estudio','proceso_verificacion','impacto_tiempo',
           'diferencia_calificaciones','independencia_resolucion','impacto_estres',
           'reglas_personales','pensamiento_critico','horas_ia_raw',
           'semestre_inicio_raw','reemplazo_laboral_raw','guia_o_atajo_raw',
           'motivo_principal','otros_usos_raw']
COLS_BIE = ['timestamp_bie','cuenta','carrera_raw','semestre_raw','edad_raw',
            'convivencia_raw','traslado_raw','ambiente_hogar','calidad_sueno',
            'tranquilidad_estudio','frecuencia_desanimo','irritabilidad',
            'apoyo_social','impacto_transporte','interes_materias',
            'cambios_alimentacion','dificultad_concentracion']
PREGUNTAS_IA = ['fase_estudio','cambio_estudio','proceso_verificacion','impacto_tiempo',
                'diferencia_calificaciones','independencia_resolucion','impacto_estres',
                'reglas_personales','pensamiento_critico','motivo_principal']
PREGUNTAS_BIE = ['ambiente_hogar','calidad_sueno','frecuencia_desanimo',
                 'irritabilidad','dificultad_concentracion']
FEATURES_NUM = ['horas_ia_dia','semestre_inicio','total_herramientas',
                'edad','traslado_min','score_bienestar','tiene_bienestar']
FEATURES_CLUSTER = ['horas_ia_dia','semestre_inicio','total_herramientas',
                    'traslado_min','score_beneficio_ia','score_bienestar']
FEATURES_REGRESION = ['semestre_inicio','total_herramientas']
HERRAMIENTAS = {
    'chatgpt':r'\b(?:chat\s*gpt|chargpt)\b',
    'gemini':r'\bgemini\b', 'deepseek':r'\bdeepse?ek\b',
    'claude':r'\bclaude\b', 'copilot':r'\bcopilot\b',
    'qwen':r'\bqwen\b', 'notebooklm':r'\bnotebook\s*lm\b',
    'perplexity':r'\bperplexity\b',
}
ESQUEMA_IA = [
    'Marca temporal','Número de cuenta','Qué herramientas de inteligencia artificial',
    'En qué fase de tu de estudio','De qué manera ha cambiado tu estudio',
    'Cuando usas la IA para resolver un problema','Cómo ha impactado el uso de la IA',
    'Qué diferencias has notado en las calificaciones','En qué medida sientes',
    'Cómo ha influido la IA en tu nivel de estrés','Qué reglas o límites personales',
    'Cómo consideras que las herramientas','Cuantas horas usas la IA',
    'Desde que semestre','Crees probable','Usas la IA principalmente',
    'Cuál es el motivo principal','Aparte de usar la IA',
]
ESQUEMA_BIE = [
    'Marca temporal','Ingresa tu número de cuenta','Qué carrera universitaria',
    'En qué semestre o año','Cuál es tu edad','Con quiénes vives',
    'Aproximadamente cuánto tiempo','Cómo describirías el ambiente',
    'Cómo suele ser la calidad','Qué tanta tranquilidad','Con qué frecuencia',
    'Qué tan fácilmente','Cómo calificarías el nivel de apoyo','Qué tanto impacto',
    'Cómo describirías tu nivel de interés','Qué cambios has notado',
    'Qué tan difícil te resulta concentrarte',
]


def texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ''
    return str(valor).strip()


def normalizar(valor) -> str:
    t = ''.join(c for c in unicodedata.normalize('NFD', texto(valor).lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', t)).strip()


def validar_esquema(df: pd.DataFrame, origen: str) -> None:
    esperado = ESQUEMA_IA if origen == 'ia' else ESQUEMA_BIE
    if len(df.columns) != len(esperado) or any(
        not normalizar(real).startswith(normalizar(prefijo))
        for real, prefijo in zip(df.columns, esperado)
    ):
        raise ValueError(f'El esquema de {origen} cambió: revisar nombres y orden de preguntas.')


def validar_cuentas(df: pd.DataFrame, origen: str) -> pd.DataFrame:
    df = df.copy()
    s = df['cuenta'].map(texto)
    ids = s.str.extract(r'^\s*(\d{9})(?:\.0+)?\s*$', expand=False)
    if ids.isna().any():
        raise ValueError(f'{origen}: identificadores faltantes o de formato inválido.')
    if ids.duplicated().any():
        raise ValueError(f'{origen}: hay identificadores duplicados; no se permite multiplicar el cruce.')
    df['cuenta'] = ids
    return df


def cargar_fuentes(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir = Path(data_dir)
    rutas = [data_dir / ARCHIVO_IA, data_dir / ARCHIVO_BIE]
    if not all(p.is_file() for p in rutas):
        raise FileNotFoundError('Faltan las dos encuestas. Consulte README y --data-dir.')
    ia = pd.read_excel(rutas[0], engine='openpyxl')
    bie = pd.read_csv(rutas[1], encoding='utf-8-sig')
    validar_esquema(ia, 'ia')
    validar_esquema(bie, 'bienestar')
    ia.columns, bie.columns = COLS_IA, COLS_BIE
    return validar_cuentas(ia, 'IA'), validar_cuentas(bie, 'Bienestar')


def parse_horas_ia(valor) -> float:
    t = normalizar(valor)
    original = texto(valor).lower().replace(',', '.')
    if not t:
        return np.nan
    if re.search(r'entre\s*1\s*y\s*3', t):
        return 2.
    if re.search(r'menos\s*de\s*1', t):
        return .5
    if re.search(r'hora\s*y\s*media', t):
        return 1.5
    m = re.search(r'(\d+(?:\.\d+)?)\s*min', original)
    if m:
        return float(m.group(1)) / 60
    m = re.search(r'(\d+(?:\.\d+)?)', original)
    if m:
        h = float(m.group(1))
        return h if 0 <= h <= 24 else np.nan
    return 1. if re.search(r'\buna? hora\b', t) else np.nan


def parse_semestre_inicio(valor, semestre_actual: int = 7) -> float:
    t = normalizar(valor)
    m = re.search(r'hace\s*(\d+)\s*semestres', t)
    if m:
        return float(semestre_actual - int(m.group(1)))
    for patron, n in [('primer',1),('segund',2),('tercer',3),('cuart',4),
                       ('quint',5),('sext',6),('septim',7),('octav',8),('noven',9)]:
        if re.search(patron,t):
            return float(n)
    m = re.search(r'\b([1-9])(?:er|ro|do|to|mo|vo)?\b',t)
    return float(m.group(1)) if m else np.nan


def parse_edad(valor) -> float:
    t = normalizar(valor)
    if 'veinticuatro' in t:
        return 24.
    m = re.search(r'\b(\d{2})\b',t)
    return float(m.group(1)) if m else np.nan


def parse_traslado_min(valor) -> float:
    t = normalizar(valor)
    if re.search(r'1\s*a\s*2\s*horas', t):
        return 90.
    if re.search(r'hora\s*y\s*(media|30)', t):
        return 90.
    m_hr = re.search(r'(\d+)\s*(?:horas?|hrs?|h)\b',t)
    m_min = re.search(r'(\d+)\s*(?:minutos?|mins?|m)\b',t)
    if m_hr or m_min:
        return float(m_hr.group(1))*60 + (float(m_min.group(1)) if m_min else 0) if m_hr else float(m_min.group(1))
    return 60. if re.search(r'una? hora',t) else np.nan


def extraer_herramientas(valor) -> set[str]:
    return detectar_herramientas(normalizar(valor), HERRAMIENTAS, original=texto(valor))


def clasificar_proposito(valor) -> str:
    t = normalizar(valor)
    guia = bool(re.search(r'guia|aprend|tutor',t))
    atajo = bool(re.search(r'atajo|ahorr|agiliz|terminar rapido',t))
    if re.search(r'\bamb[ao]s?\b|\blas dos\b',t) or (guia and atajo):
        return 'Híbrido'
    if guia:
        return 'Guía'
    if atajo:
        return 'Atajo'
    return 'Contextual' if 'depende' in t else 'No clasificable'


def clasificar_reemplazo(valor) -> str:
    t = normalizar(valor)
    if not t or re.search(r'\bno se\b|\bno estoy segur|\bno sab',t):
        return 'Indeciso'
    if re.search(r'depende|no completamente|no todas|no todo',t):
        return 'Parcial / Depende'
    if re.match(r'^no\b',t):
        return 'No'
    if re.search(r'\bsi\b',t):
        return 'Sí'
    return 'Indeciso'


def normalizar_convivencia(valor) -> str | None:
    t = normalizar(valor)
    if not t:
        return None
    if 'familia' in t:
        return 'Familia'
    if re.search(r'\bsol[oa]\b',t):
        return 'Solo'
    if re.search(r'companer|piso|room',t):
        return 'Compañeros'
    return 'Otro'


# Raíces explícitas; no se asigna polaridad a "menos" ni "poco" por sí solos.
POSITIVAS_IA = r'^(ayud|mejor|comprend|entend|facilit|fortalec|aprend|organiz|explicacion|rapido|guia|disminuid)'
NEGATIVAS_IA = r'^(dependencia|debilit|estres|error|copiar|afect|alucin|dificil)'
POSITIVAS_BIE = r'^(tranquil|buen|excelent|apoyo|descansad|agradable)'
NEGATIVAS_BIE = r'^(mal[ao]?s?$|pesad|cansad|agot|estres|dificil|desmotiv|trist|irrit|descuid|hambre)'


def _negado(tokens: list[str], i: int) -> bool:
    ventana=tokens[max(0,i-4):i]
    return any(x in {'no','sin','nunca','jamas','ni'} and not (
        x=='no' and j+1<len(ventana) and ventana[j+1] in {'solo','solamente'}
    ) for j,x in enumerate(ventana))


def score_polaridad(valor, dominio: str) -> float:
    """Conteo contextual descriptivo; ventana de negación de cuatro palabras.

    Cero indica balance/sin coincidencias, no una medición de salud mental.
    Ausencia de respuesta produce NaN. No es un modelo semántico validado.
    """
    if not texto(valor):
        return np.nan
    pos_re, neg_re = ((POSITIVAS_IA,NEGATIVAS_IA) if dominio == 'ia'
                      else (POSITIVAS_BIE,NEGATIVAS_BIE))
    pos = neg = 0
    # Puntuación y adversativas limitan el alcance de la negación.
    for clausula in re.split(r'[.,;!?]|\bpero\b|\baunque\b',texto(valor).lower()):
        tokens = normalizar(clausula).split()
        for i,w in enumerate(tokens):
            signo = 1 if re.search(pos_re,w) else -1 if re.search(neg_re,w) else 0
            if not signo:
                continue
            if w.startswith('estres'):
                alivios=[j for j in range(max(0,i-5),min(len(tokens),i+6))
                         if re.match(r'^(reduc|disminu|baja|bajo$|alivi)',tokens[j])
                         and not (tokens[j]=='bajo' and j<i)]  # "bajo estrés" no es alivio.
                menos=[j for j in range(max(0,i-3),i) if tokens[j]=='menos']
                if alivios:
                    j=min(alivios,key=lambda j:abs(j-i))
                    signo=-1 if _negado(tokens,j) else 1
                elif menos:
                    signo=-1 if _negado(tokens,menos[-1]) else 1
                elif _negado(tokens,i):
                    signo=1
            elif _negado(tokens,i):
                signo*=-1
            pos += signo > 0
            neg += signo < 0
    return (pos-neg)/(pos+neg+1)


def _score_preguntas(fila: pd.Series, dominio: str) -> float:
    valores = [score_polaridad(x,dominio) for x in fila]
    observados = [x for x in valores if not pd.isna(x)]
    return float(np.mean(observados)) if observados else np.nan


def _corpus(fila: pd.Series) -> str:
    return ' '.join(texto(x) for x in fila if texto(x))


def preparar_datos(ia: pd.DataFrame, bie: pd.DataFrame) -> pd.DataFrame:
    ia, bie = validar_cuentas(ia,'IA'), validar_cuentas(bie,'Bienestar')
    ia, bie, auditoria = limpiar_fuentes(ia, bie)
    ia['horas_ia_dia'] = ia['horas_ia_raw'].map(parse_horas_ia)
    ia['semestre_inicio'] = ia['semestre_inicio_raw'].map(parse_semestre_inicio)
    tools = ia['herramientas_frecuencia'].map(extraer_herramientas)
    for h in HERRAMIENTAS:
        ia[f'usa_{h}'] = tools.map(lambda x:h in x).astype(int)
    ia['total_herramientas'] = tools.map(len)
    ia['tipo_uso_ia'] = ia['guia_o_atajo_raw'].map(clasificar_proposito)
    ia['cree_reemplazo'] = ia['reemplazo_laboral_raw'].map(clasificar_reemplazo)
    ia['corpus_ia'] = ia[PREGUNTAS_IA].apply(_corpus,axis=1)
    ia['score_beneficio_ia'] = ia[PREGUNTAS_IA].apply(_score_preguntas,axis=1,dominio='ia')
    bie['edad'] = bie['edad_raw'].map(parse_edad)
    bie['traslado_min'] = bie['traslado_raw'].map(parse_traslado_min)
    bie['convivencia'] = bie['convivencia_raw'].map(normalizar_convivencia)
    bie['corpus_bie'] = bie[PREGUNTAS_BIE].apply(_corpus,axis=1)
    bie['score_bienestar'] = bie[PREGUNTAS_BIE].apply(_score_preguntas,axis=1,dominio='bienestar')
    df = ia.merge(bie,on='cuenta',how='left',validate='one_to_one',indicator=True)
    df['tiene_bienestar'] = df.pop('_merge').eq('both')
    df['corpus_bie'] = df['corpus_bie'].fillna('')
    df.attrs['limpieza'] = auditoria
    return df


STOPWORDS = frozenset(('a al algo ante como con cual cuando de del desde donde el ella ellas ellos en entre era es esa ese eso esta estan este esto fue ha hacia hay la las le les lo los me mi mis muy o para por que se ser si son su sus te tu tus un una unas uno unos y ya ia inteligencia artificial herramientas utilizar '
                      'mas mucho mucha muchas muchos todo toda todos todas porque solo solamente tambien creo considero puede puedo hacer hace uso usar utilizo utiliza vez veces tengo tiene tener siempre siento forma manera cosas algun alguna algunas algunos mismo misma ahora').split())


def limpiar_texto_nlp(valor) -> str:
    return ' '.join(w for w in normalizar(valor).split()
                    if w.isalpha() and w not in STOPWORDS and (len(w)>2 or w in {'no','ni'}))


def _dense(x):
    return x.toarray()


class TfidfSeguro(TransformerMixin,BaseEstimator):
    """Un fold vacío aporta una columna cero; nunca aprende de otros folds."""
    def fit(self,X,y=None):
        self.vectorizador_=TfidfVectorizer(max_features=30,ngram_range=(1,2),preprocessor=limpiar_texto_nlp)
        try:
            self.vectorizador_.fit(X)
        except ValueError as e:
            if 'empty vocabulary' not in str(e):
                raise
            self.vectorizador_=None
        self.vocabulary_=self.vectorizador_.vocabulary_ if self.vectorizador_ is not None else {}
        return self

    def transform(self,X):
        return self.vectorizador_.transform(X) if self.vectorizador_ is not None else csr_matrix((len(X),1))

    def get_feature_names_out(self,input_features=None):
        return self.vectorizador_.get_feature_names_out() if self.vectorizador_ is not None else np.array(['sin_vocabulario'])


class PCAAdaptativo(TransformerMixin,BaseEstimator):
    """Hasta cuatro componentes según rango disponible solo en entrenamiento."""
    def __init__(self,n_components=4,random_state=42):
        self.n_components=n_components
        self.random_state=random_state

    def fit(self,X,y=None):
        self.n_components_=max(1,min(self.n_components,len(X)-1,X.shape[1]))
        self.pca_=None
        if np.var(X,axis=0).sum()>1e-15:
            self.pca_=PCA(n_components=self.n_components_,random_state=self.random_state).fit(X)
        return self

    def transform(self,X):
        return self.pca_.transform(X) if self.pca_ is not None else np.zeros((len(X),self.n_components_))


def crear_pipeline(modelo) -> Pipeline:
    numeros = Pipeline([
        ('escalar',StandardScaler()),  # Aprende escala sin observar prueba; preserva NaN.
        ('imputar',KNNImputer(n_neighbors=3,add_indicator=True,keep_empty_features=True)),
    ])
    texto_pipe = Pipeline([
        ('tfidf',TfidfSeguro()),
        ('denso',FunctionTransformer(_dense,accept_sparse=True)),
        ('pca',PCAAdaptativo(n_components=4,random_state=42)),
    ])
    return Pipeline([
        ('preprocesar',ColumnTransformer([
            ('numeros',numeros,FEATURES_NUM), ('texto',texto_pipe,'corpus_ia'),
        ])),
        ('modelo',modelo),
    ])


def datos_supervisados(df: pd.DataFrame) -> tuple[pd.DataFrame,pd.Series]:
    validas = df['tipo_uso_ia'].isin(['Híbrido','Guía','Atajo'])
    X = df.loc[validas,FEATURES_NUM+['corpus_ia']].copy().reset_index(drop=True)
    y = df.loc[validas,'tipo_uso_ia'].eq('Híbrido').astype(int).reset_index(drop=True)
    return X,y


def _metricas(y, pred) -> dict:
    return {'accuracy':float(accuracy_score(y,pred)),
            'precision':float(precision_score(y,pred,zero_division=0)),
            'recall':float(recall_score(y,pred,zero_division=0)),
            'f1':float(f1_score(y,pred,zero_division=0)),
            'confusion':confusion_matrix(y,pred,labels=[0,1]).tolist()}


def comparar_busquedas(pipeline, parametros, cv, X, y=None, *, scoring, metrica):
    """Compara búsqueda exhaustiva y muestreo reproducible con los mismos pliegues."""
    refit = 'silueta' if metrica == 'Silueta' else True
    sufijo = 'silueta' if metrica == 'Silueta' else 'score'
    opciones = {'scoring': scoring, 'refit': refit, 'cv': cv, 'error_score': 'raise'}
    n_iter = min(8, len(ParameterGrid(parametros)) // 2)
    buscadores = (
        GridSearchCV(pipeline, parametros, **opciones),
        RandomizedSearchCV(pipeline, parametros, n_iter=n_iter, random_state=42, **opciones),
    )
    filas = []
    for buscador in buscadores:
        buscador.fit(X, y)
        resultados = buscador.cv_results_
        indice = buscador.best_index_
        n_validos = buscador.n_splits_
        if metrica == 'Silueta':
            n_validos = sum(int(resultados[f'split{i}_test_valido'][indice])
                            for i in range(buscador.n_splits_))
        filas.append({
            'metodo': type(buscador).__name__,
            'configuraciones': len(resultados['params']),
            'parametros': buscador.best_params_,
            'media': float(buscador.best_score_),
            'desviacion': float(resultados[f'std_test_{sufijo}'][indice]),
            'pliegues_validos': n_validos,
        })
    indice = max(range(len(filas)), key=lambda i: (filas[i]['media'], filas[i]['pliegues_validos']))
    resumen = {'metrica': metrica, 'n_folds': buscadores[indice].n_splits_,
               'busquedas': filas, 'mejor_metodo': filas[indice]['metodo']}
    return resumen, buscadores[indice].best_estimator_


def evaluar_modelos(df: pd.DataFrame) -> dict:
    X,y = datos_supervisados(df)
    if y.nunique()!=2 or y.value_counts().min()<4:
        return {'estado':'insuficiente','motivo':'Se requieren al menos cuatro casos por clase para separar prueba y validar.'}
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=.25,stratify=y,random_state=42)
    nfolds = min(5,int(ytr.value_counts().min()))
    cv = StratifiedKFold(n_splits=nfolds,shuffle=True,random_state=42)
    minimo_entrenamiento = min(len(indices) for indices, _ in cv.split(Xtr, ytr))
    parametros_knn = {'modelo__n_neighbors': [k for k in (1, 3, 5, 7) if k <= minimo_entrenamiento],
                      'modelo__weights': ['uniform', 'distance'], 'modelo__p': [1, 2]}
    modelos = {
        'Regresión logística':LogisticRegression(max_iter=1000,random_state=42),
        'Random Forest':RandomForestClassifier(n_estimators=100,max_depth=3,random_state=42),
        'SVM':SVC(kernel='rbf',random_state=42),
        'KNN':KNeighborsClassifier(n_neighbors=3),
    }
    filas=[]
    pipelines={nombre:crear_pipeline(modelo) for nombre,modelo in modelos.items()}
    # La referencia necesita solo prevalencia de entrenamiento, no vectorización.
    pipelines['Baseline (mayoría)'] = DummyClassifier(strategy='most_frequent')
    for nombre,pipe in pipelines.items():
        scores = cross_validate(pipe,Xtr,ytr,cv=cv,scoring={'accuracy':'accuracy','f1':'f1'},error_score='raise')
        filas.append({'modelo':nombre, 'cv_accuracy':float(scores['test_accuracy'].mean()),
                      'cv_accuracy_sd':float(scores['test_accuracy'].std(ddof=1)),
                      'cv_f1':float(scores['test_f1'].mean()),
                      'cv_f1_sd':float(scores['test_f1'].std(ddof=1)),
                      'fold_f1':scores['test_f1'].tolist()})
    orden = pd.DataFrame(filas).sort_values(['cv_f1','cv_accuracy','cv_f1_sd'],ascending=[False,False,True])
    ganador = orden.loc[orden['modelo']!='Baseline (mayoría)','modelo'].iloc[0]
    mejor = clone(pipelines[ganador]).fit(Xtr,ytr)
    baseline = DummyClassifier(strategy='most_frequent').fit(Xtr,ytr)
    ajuste, knn_ajustado = comparar_busquedas(pipelines['KNN'], parametros_knn, cv, Xtr, ytr,
                                             scoring='f1', metrica='F1')
    ajuste['test'] = _metricas(yte, knn_ajustado.predict(Xte))
    return {'estado':'ok', 'objetivo':'Modalidad declarada mixta (1) frente a exclusiva: guía o atajo (0).',
            'n_etiquetados':len(y), 'n_excluidos':len(df)-len(y),
            'clases':{'mixta':int(y.sum()),'exclusiva':int((y==0).sum())},
            'n_train':len(ytr),'n_test':len(yte),'n_folds':nfolds,
            'clases_train':{str(k):int(v) for k,v in ytr.value_counts().items()},
            'clases_test':{str(k):int(v) for k,v in yte.value_counts().items()},
            'cv':orden.to_dict(orient='records'),'seleccionado':ganador,
            'supera_baseline_cv':bool(orden.loc[orden['modelo']==ganador,'cv_f1'].iloc[0] >
                                     orden.loc[orden['modelo']=='Baseline (mayoría)','cv_f1'].iloc[0]),
            'seleccion':'Mayor F1 medio de CV solo en entrenamiento; desempate por accuracy y menor dispersión.',
            'test':_metricas(yte,mejor.predict(Xte)),
            'baseline_test':_metricas(yte,baseline.predict(Xte)),
            'ajuste':ajuste,
            'test_sensible_pp':100/len(yte)}


def datos_regresion(df: pd.DataFrame) -> tuple[pd.DataFrame,pd.Series]:
    """Casos completos del objetivo y dos predictores; nunca usa textos o cuentas."""
    columnas=FEATURES_REGRESION+['horas_ia_dia']
    datos=df[columnas].apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    datos=datos.loc[datos['horas_ia_dia']>=0]
    return datos[FEATURES_REGRESION],datos['horas_ia_dia']


def crear_pipeline_regresion() -> Pipeline:
    return Pipeline([('escalar',StandardScaler()),('modelo',LinearRegression())])


def metricas_regresion(y, pred) -> dict:
    # R² no está definido si el objetivo es constante, incluso con ajuste perfecto.
    y=np.asarray(y,dtype=float)
    r2=float(r2_score(y,pred,force_finite=False)) if len(y)>1 and np.ptp(y)>0 else None
    return {'r2':r2,'mae_h':float(mean_absolute_error(y,pred)),
            'rmse_h':float(root_mean_squared_error(y,pred))}


def evaluar_regresion(df: pd.DataFrame) -> dict:
    X,y=datos_regresion(df)
    base={'n':len(y),'n_excluidos':len(df)-len(y),'objetivo':'horas_ia_dia',
          'predictores':FEATURES_REGRESION.copy(),'semilla':42}
    if len(y)<16 or y.nunique()<2:
        return {**base,'estado':'insuficiente',
                'motivo':'Se necesitan al menos 16 casos completos y variación en las horas de uso.'}
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.25,random_state=42)
    if ytr.nunique()<2:
        return {**base,'estado':'insuficiente','motivo':'Las horas no varían en el conjunto de entrenamiento.'}
    cv=KFold(n_splits=5,shuffle=True,random_state=42)
    modelos=[]
    # Ambos modelos y sus parámetros se fijan antes de consultar la prueba.
    for nombre,estimador in [('Regresión lineal',crear_pipeline_regresion()),
                             ('Referencia (media)',DummyRegressor(strategy='mean'))]:
        folds=[]
        for it,iv in cv.split(Xtr):
            modelo=clone(estimador).fit(Xtr.iloc[it],ytr.iloc[it])
            folds.append({'n':len(iv),**metricas_regresion(ytr.iloc[iv],modelo.predict(Xtr.iloc[iv]))})
        validos=[f['r2'] for f in folds if f['r2'] is not None]
        resumen_cv={'r2_media':float(np.mean(validos)) if validos else None,
                    'r2_sd':float(np.std(validos,ddof=1)) if len(validos)>1 else None,
                    'mae_media_h':float(np.mean([f['mae_h'] for f in folds])),
                    'rmse_media_h':float(np.mean([f['rmse_h'] for f in folds])),
                    'folds_r2_validos':len(validos)}
        modelo=clone(estimador).fit(Xtr,ytr)
        modelos.append({'modelo':nombre,'cv':resumen_cv,'folds':folds,
                        'entrenamiento':metricas_regresion(ytr,modelo.predict(Xtr)),
                        'prueba':metricas_regresion(yte,modelo.predict(Xte))})
    return {**base,'estado':'ok','n_train':len(ytr),'n_test':len(yte),'n_folds':5,
            'modelos':modelos,
            'protocolo':'Partición 75/25 fija; cinco pliegues solo en entrenamiento. Sin ajuste de hiperparámetros ni selección por la prueba.',
            'alcance':'Horas declaradas de uso de IA. No mide calificaciones ni efectos causales. Muestra pequeña; R² puede ser negativo.'}


def evaluar_silueta(pipeline, validacion):
    escalados = pipeline.named_steps['escalar'].transform(validacion)
    etiquetas = pipeline.predict(validacion)
    if not 2 <= len(np.unique(etiquetas)) < len(validacion):
        return {'silueta': -1., 'valido': 0.}
    return {'silueta': float(silhouette_score(escalados, etiquetas)), 'valido': 1.}


def analizar_clusters(df: pd.DataFrame) -> dict:
    reales = df.loc[df['tiene_bienestar'],FEATURES_CLUSTER].dropna()
    if len(reales)<7:
        return {'estado':'insuficiente','n':len(reales)}
    n_folds = 3 if len(reales) >= 9 else 2
    cv = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    distintos = len(reales.drop_duplicates())
    tope_cv = min(5, *(min(len(va) - 1, len(reales.iloc[tr].drop_duplicates()))
                        for tr, va in cv.split(reales)))
    if tope_cv < 2:
        return {'estado':'insuficiente','n':len(reales)}

    pipeline = Pipeline([('escalar', StandardScaler()), ('modelo', KMeans(random_state=42))])
    parametros = {'modelo__n_clusters': list(range(2, tope_cv + 1)),
                  'modelo__init': ['k-means++', 'random'], 'modelo__n_init': [10, 20]}
    ajuste, mejor = comparar_busquedas(pipeline, parametros, cv, reales,
                                      scoring=evaluar_silueta, metrica='Silueta')
    X = StandardScaler().fit_transform(reales)
    exploratorios = {k: KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
                     for k in range(2, min(5, len(X) - 1, distintos) + 1)}
    scores = {k: float(silhouette_score(X, grupos)) for k, grupos in exploratorios.items()
              if len(np.unique(grupos)) >= 2}
    fila = next(f for f in ajuste['busquedas'] if f['metodo'] == ajuste['mejor_metodo'])
    labels = mejor.named_steps['modelo'].labels_
    ajuste['aplicado'] = fila['pliegues_validos'] > 0 and len(np.unique(labels)) >= 2
    if ajuste['aplicado']:
        mejor_k = mejor.named_steps['modelo'].n_clusters
    else:
        if not scores:
            return {'estado':'insuficiente','n':len(reales)}
        mejor_k = max(scores, key=scores.get)
        labels = exploratorios[mejor_k]
    jerarquico=AgglomerativeClustering(n_clusters=mejor_k).fit_predict(X)
    pca=PCA(n_components=2,random_state=42).fit(X)
    perfiles=reales.assign(grupo=labels).groupby('grupo')[FEATURES_CLUSTER].mean()
    tamanos=pd.Series(labels).value_counts().sort_index()
    # No se exportan perfiles descriptivos de grupos de una o dos personas.
    publicables=(tamanos>=3)&((len(reales)-tamanos)>=3)
    perfiles=perfiles.loc[tamanos[publicables].index].round(4)
    return {'estado':'ok','n':len(reales),'k':mejor_k,
            'silhouette':float(silhouette_score(X,labels)),'siluetas':{str(k):v for k,v in scores.items()},
            'silhouette_jerarquico':float(silhouette_score(X,jerarquico)),
            'pca_varianza':pca.explained_variance_ratio_.tolist(),
            'ajuste':ajuste,
            'tamanos':{str(k):int(v) for k,v in tamanos.items()},
            'perfiles_n_min_3':{str(k):v for k,v in perfiles.to_dict(orient='index').items()},
            'limite':'Exploratorio; perfiles con grupo o complemento n<3 omitidos. Grupos no son diagnósticos.'}


def _descripcion(s: pd.Series) -> dict:
    s=s.dropna()
    return {'n':len(s),'media':float(s.mean()) if len(s) else None,
            'mediana':float(s.median()) if len(s) else None,
            'sd':float(s.std()) if len(s)>1 else None,
            'min':float(s.min()) if len(s) else None,
            'max':float(s.max()) if len(s) else None,
            'q1':float(s.quantile(.25)) if len(s) else None,
            'q3':float(s.quantile(.75)) if len(s) else None}


def resumir(df: pd.DataFrame, n_bie: int) -> dict:
    n=len(df)
    reales=df.loc[df['tiene_bienestar']]
    pares=reales[['horas_ia_dia','traslado_min']].dropna()
    rho,p=spearmanr(pares['horas_ia_dia'],pares['traslado_min']) if len(pares)>2 else (np.nan,np.nan)
    cuenta=df['tipo_uso_ia'].value_counts().to_dict()
    vocab=TfidfSeguro()
    tf=vocab.fit_transform(df['corpus_ia'])  # EDA descriptivo; nunca se reutiliza para evaluar.
    pesos=pd.Series(np.asarray(tf.mean(axis=0)).ravel(),index=vocab.get_feature_names_out()).sort_values(ascending=False)
    pesos=pesos[(pesos>0)&~pesos.index.isin(['no','ni'])]
    cuant=['horas_ia_dia','semestre_inicio','total_herramientas','score_beneficio_ia']
    cuant_bie=['edad','traslado_min','score_bienestar']
    corr=reales[FEATURES_CLUSTER+['edad']].corr(method='spearman')
    return {
        'muestra':{'ia':n,'bienestar':n_bie,'emparejados':len(reales),'solo_ia':n-len(reales),'solo_bienestar':n_bie-len(reales)},
        'descriptivos':{**{c:_descripcion(df[c]) for c in cuant},**{c:_descripcion(reales[c]) for c in cuant_bie}},
        'tipo_uso':{str(k):int(v) for k,v in cuenta.items()},
        'reemplazo':{str(k):int(v) for k,v in df['cree_reemplazo'].value_counts().items()},
        'herramientas':{h:int(df[f'usa_{h}'].sum()) for h in HERRAMIENTAS},
        'semestre_inicio':{str(int(k)):int(v) for k,v in df['semestre_inicio'].dropna().value_counts().sort_index().items()},
        'kpis':{
            'adopcion_observada_n':int(df['total_herramientas'].gt(0).sum()),
            'adopcion_observada_pct':100*float(df['total_herramientas'].gt(0).mean()),
            'mediana_ia_h':float(df['horas_ia_dia'].median()),
            'guia_hibrido_pct':100*(cuenta.get('Guía',0)+cuenta.get('Híbrido',0))/n,
            'hibrido_pct':100*cuenta.get('Híbrido',0)/n,
            'multiherramienta_pct':100*float(df['total_herramientas'].ge(2).mean()),
            'multiherramienta_n':int(df['total_herramientas'].ge(2).sum()),
            'traslado_mediana_min':float(reales['traslado_min'].median()),
            'traslado_mayor_90_n':int(reales['traslado_min'].gt(90).sum()),
            'reemplazo_si_pct':100*float(df['cree_reemplazo'].eq('Sí').mean()),
        },
        'calidad':{
            'numericas_ia_sin_parsear':{c:int(df[c].isna().sum()) for c in ['horas_ia_dia','semestre_inicio']},
            'numericas_bie_sin_parsear':{c:int(reales[c].isna().sum()) for c in ['edad','traslado_min']},
            'textos_ia_ausentes':int(df[PREGUNTAS_IA].isna().sum().sum()),
            'bienestar_no_observado':int((~df['tiene_bienestar']).sum()),
        },
        'correlacion_traslado_ia':{'n':len(pares),'rho':float(rho),'p':float(p)},
        'correlacion_spearman':corr.to_dict(),
        'tfidf_top':{str(k):float(v) for k,v in pesos.head(10).items()},
        'polaridad_por_pregunta':{
            c:{'n':int(df[c].map(texto).ne('').sum()),
               'media':float(df[c].map(lambda x:score_polaridad(x,dominio)).mean()),
               'n_score_cero':int(df[c].map(lambda x:score_polaridad(x,dominio)).eq(0).sum())}
            for dominio,preguntas in [('ia',PREGUNTAS_IA),('bienestar',PREGUNTAS_BIE)] for c in preguntas
        },
    }


@dataclass
class Resultado:
    datos: pd.DataFrame  # Memoria local; nunca se exporta esta tabla con identificadores.
    resumen: dict


def analizar(data_dir: str | Path) -> Resultado:
    ia,bie=cargar_fuentes(data_dir)
    df=preparar_datos(ia,bie)
    r=resumir(df,len(bie))
    r['limpieza']=df.attrs['limpieza']
    r['supervisado']=evaluar_modelos(df)
    r['regresion']=evaluar_regresion(df)
    r['clusters']=analizar_clusters(df)
    r['metodologia']={
        'version':'2.2.0','semilla':42,
        'polaridad':'Media por pregunta; lexicón contextual con negación. No validado como escala académica o clínica.',
        'faltantes':'Textos ausentes no inventados; bienestar sin encuesta = nulo; KNN solo dentro del pipeline supervisado.',
        'alcance':'Muestra encuestada, sin inferencia causal ni medición objetiva de rendimiento.',
    }
    r['proveniencia']={
        'fecha':datetime.now(ZoneInfo('America/Mexico_City')).isoformat(timespec='seconds'),
        'fuentes':{fn:hashlib.sha256((Path(data_dir)/fn).read_bytes()).hexdigest() for fn in [ARCHIVO_IA,ARCHIVO_BIE]},
        'versiones':{p:importlib.metadata.version(p) for p in ['pandas','numpy','scikit-learn','scipy','matplotlib']},
    }
    return Resultado(df,r)


def json_seguro(obj):
    if isinstance(obj,dict):
        return {str(k):json_seguro(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):
        return [json_seguro(x) for x in obj]
    if isinstance(obj,(float,np.floating)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj,np.integer):
        return int(obj)
    return obj


def exportar(resultado: Resultado, out: str | Path) -> None:
    from visualizaciones import generar_figuras
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    r=json_seguro(resultado.resumen)
    (out/'resumen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    pd.DataFrame(r['descriptivos']).T.to_csv(out/'descriptivos.csv',encoding='utf-8-sig',index_label='variable')
    if r['supervisado']['estado']=='ok':
        pd.DataFrame(r['supervisado']['cv']).drop(columns=['fold_f1']).to_csv(out/'modelos_cv.csv',index=False,encoding='utf-8-sig')
    filas_ajuste = []
    for clave, modelo in [('clusters', 'K-Means'), ('supervisado', 'KNN')]:
        if r[clave]['estado'] != 'ok':
            continue
        ajuste = r[clave]['ajuste']
        for fila in ajuste['busquedas']:
            filas_ajuste.append({'modelo': modelo, 'metrica': ajuste['metrica'],
                                 'pliegues': ajuste['n_folds'], **fila,
                                 'parametros': json.dumps(fila['parametros'], ensure_ascii=False)})
    pd.DataFrame(filas_ajuste, columns=['modelo', 'metrica', 'pliegues', 'metodo', 'configuraciones',
                                       'parametros', 'media', 'desviacion', 'pliegues_validos']).to_csv(
        out/'ajuste_modelos.csv', index=False, encoding='utf-8-sig')
    if r['regresion']['estado']=='ok':
        tabla=[{'modelo':m['modelo'],'evaluacion':etapa,**metricas}
               for m in r['regresion']['modelos']
               for etapa,metricas in [('entrenamiento',m['entrenamiento']),('validacion_cruzada',m['cv']),('prueba',m['prueba'])]]
        pd.DataFrame(tabla).to_csv(out/'regresion_metricas.csv',index=False,encoding='utf-8-sig')
    generar_figuras(resultado,out/'figuras')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=Path(__file__).parent/'data'/'private')
    p.add_argument('--out',type=Path,default=Path(__file__).parent/'resultados')
    args=p.parse_args()
    try:
        r=analizar(args.data_dir)
        exportar(r,args.out)
    except (ValueError,FileNotFoundError) as e:
        p.exit(2,f'No se pudo analizar: {e}\n')
    print('Análisis terminado. Se exportaron solo resultados agregados.')


if __name__=='__main__':
    main()
