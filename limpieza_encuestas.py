"""Normalización por pregunta y auditoría agregada de las dos encuestas."""

from datetime import date
from difflib import SequenceMatcher
import re
from unicodedata import normalize

import pandas as pd


TEXTO = 'Unicode NFC, espacios y marcas explícitas de ausencia. Se conserva el contenido.'
CUENTA = 'Clave privada validada con regex de nueve dígitos y verificación de unicidad.'
CAMPOS_IA = {
    'timestamp_ia': 'Conversión a fecha y hora. Entradas inválidas quedan como ausentes.',
    'cuenta': CUENTA,
    'herramientas_frecuencia': 'Texto normalizado, alias por regex y similitud de nombres aislados.',
    'fase_estudio': TEXTO,
    'cambio_estudio': TEXTO,
    'proceso_verificacion': TEXTO,
    'impacto_tiempo': TEXTO,
    'diferencia_calificaciones': TEXTO,
    'independencia_resolucion': TEXTO,
    'impacto_estres': TEXTO,
    'reglas_personales': TEXTO,
    'pensamiento_critico': TEXTO,
    'horas_ia_raw': 'Texto normalizado y conversión posterior a horas mediante regex y reglas de unidades.',
    'semestre_inicio_raw': 'Texto normalizado y conversión posterior de ordinales a números de semestre.',
    'reemplazo_laboral_raw': 'Texto normalizado y clasificación posterior por patrones de respuesta.',
    'guia_o_atajo_raw': 'Texto normalizado y clasificación posterior por patrones de modalidad.',
    'motivo_principal': TEXTO,
    'otros_usos_raw': TEXTO,
}
CAMPOS_BIENESTAR = {
    'cuenta': CUENTA,
    'edad_raw': 'Texto normalizado y conversión posterior a años mediante regex.',
    'convivencia_raw': 'Texto normalizado y unificación posterior en categorías de convivencia.',
    'traslado_raw': 'Texto normalizado y conversión posterior a minutos mediante regex y unidades.',
    'ambiente_hogar': TEXTO,
    'calidad_sueno': TEXTO,
    'frecuencia_desanimo': TEXTO,
    'irritabilidad': TEXTO,
    'dificultad_concentracion': TEXTO,
}
AUSENCIAS = {'', 'n/a', 'sin respuesta'}


def _texto_limpio(valor):
    if pd.isna(valor):
        return pd.NA
    texto = normalize('NFC', str(valor)).replace('\u200b', '').replace('\ufeff', '')
    texto = re.sub(r'\s+', ' ', texto).strip()
    return pd.NA if texto.casefold() in AUSENCIAS else texto


def _fecha_limpia(columna):
    # Los números aislados podrían interpretarse como nanosegundos desde 1970.
    fechas = columna.map(lambda v: v if isinstance(v, date) else _texto_limpio(v) if isinstance(v, str) else None)
    return pd.to_datetime(fechas, format='mixed', dayfirst=True, errors='coerce')


def _limpiar_campos(original, campos):
    limpio = original.loc[:, list(campos)].copy()
    filas = []
    for campo, tratamiento in campos.items():
        origen = original[campo]
        if campo == 'timestamp_ia':
            limpio[campo] = _fecha_limpia(origen)
        elif campo != 'cuenta':
            limpio[campo] = origen.map(_texto_limpio)

        antes = origen.astype('string')
        despues = limpio[campo].astype('string')
        sin_cambio = antes.eq(despues).fillna(False) | (antes.isna() & despues.isna())
        filas.append({
            'campo': campo,
            'tratamiento': tratamiento,
            'ausentes_origen': int((antes.isna() | antes.str.strip().eq('')).sum()),
            'ausentes_limpios': int(despues.isna().sum()),
            'modificados': int((~sin_cambio).sum()),
        })
    return limpio, {'filas': len(limpio), 'columnas_cubiertas': len(filas), 'columnas': filas}


def limpiar_fuentes(ia, bienestar):
    """Normaliza copias en memoria y registra únicamente conteos por campo.

    Recibe las fuentes después de validar las claves del cruce. Las conversiones
    de unidades y categorías se completan en los parsers del análisis.
    """
    if set(ia) != CAMPOS_IA.keys():
        raise ValueError('La limpieza debe cubrir todas las columnas del formulario de IA.')
    if not CAMPOS_BIENESTAR.keys() <= set(bienestar):
        raise ValueError('Faltan variables de bienestar seleccionadas para el análisis.')
    ia_limpia, auditoria_ia = _limpiar_campos(ia, CAMPOS_IA)
    bie_limpio, auditoria_bie = _limpiar_campos(bienestar, CAMPOS_BIENESTAR)
    auditoria_bie['columnas_fuera_de_alcance'] = [campo for campo in bienestar if campo not in CAMPOS_BIENESTAR]
    return ia_limpia, bie_limpio, {'ia': auditoria_ia, 'bienestar': auditoria_bie}


def detectar_herramientas(normalizado, patrones, *, original):
    """Reconoce alias conocidos y erratas aisladas con una coincidencia clara."""
    encontradas = {nombre for nombre, patron in patrones.items() if re.search(patron, normalizado)}
    candidatos = [nombre for nombre in patrones if len(nombre) >= 6]
    partes = re.split(r'[,;/.\n]+|\s+(?:y|e)\s+', original.casefold())
    for parte in partes:
        palabra = parte.strip()
        if palabra in patrones or not re.fullmatch(r'[a-z]{6,}', palabra):
            continue
        puntuaciones = sorted(
            ((SequenceMatcher(None, palabra, nombre).ratio(), nombre) for nombre in candidatos),
            reverse=True,
        )
        if not puntuaciones:
            continue
        similitud, nombre = puntuaciones[0]
        alternativa = puntuaciones[1][0] if len(puntuaciones) > 1 else 0
        if similitud >= 0.88 and similitud - alternativa >= 0.08:
            encontradas.add(nombre)
    return encontradas
