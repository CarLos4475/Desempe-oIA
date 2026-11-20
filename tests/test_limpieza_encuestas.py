import json
import unittest

import pandas as pd

from limpieza_encuestas import detectar_herramientas, limpiar_fuentes


class LimpiezaEncuestasTest(unittest.TestCase):
    def fuentes(self):
        # Esquema del formulario sin leer ni mostrar respuestas originales.
        from analisis import COLS_BIE, COLS_IA

        ia = pd.DataFrame([{c: None for c in COLS_IA} for _ in range(2)])
        bie = pd.DataFrame([{c: None for c in COLS_BIE}])
        ia['cuenta'] = ['434343434', '123456789']
        ia['timestamp_ia'] = ['04/05/2026 08:21:05', 'fecha inválida']
        ia['otros_usos_raw'] = ['  Repaso\u00a0de\ncálculo   ', 'N/A']
        ia['diferencia_calificaciones'] = [' No. ', '']
        bie['cuenta'] = ['434343434']
        bie['calidad_sueno'] = ['  Normal   en general. ']
        bie['carrera_raw'] = ['Campo sintético fuera de alcance']
        return ia, bie

    def test_limpia_todo_el_formulario_y_solo_bienestar_utilizado(self):
        ia, bie = self.fuentes()
        normal_ia, normal_bie, auditoria = limpiar_fuentes(ia, bie)
        self.assertEqual(list(normal_ia.columns), list(ia.columns))
        self.assertEqual(auditoria['ia']['columnas_cubiertas'], len(ia.columns))
        self.assertIn('carrera_raw', auditoria['bienestar']['columnas_fuera_de_alcance'])
        self.assertNotIn('carrera_raw', normal_bie)
        self.assertEqual(normal_bie.loc[0, 'calidad_sueno'], 'Normal en general.')
        self.assertEqual(normal_ia.loc[0, 'timestamp_ia'], pd.Timestamp('2026-05-04 08:21:05'))
        self.assertTrue(pd.isna(normal_ia.loc[1, 'timestamp_ia']))
        self.assertEqual(normal_ia.loc[0, 'otros_usos_raw'], 'Repaso de cálculo')
        self.assertTrue(pd.isna(normal_ia.loc[1, 'otros_usos_raw']))
        self.assertEqual(normal_ia.loc[0, 'diferencia_calificaciones'], 'No.')
        self.assertTrue(pd.isna(normal_ia.loc[1, 'diferencia_calificaciones']))
        self.assertEqual(ia.loc[0, 'otros_usos_raw'], '  Repaso\u00a0de\ncálculo   ')

    def test_auditoria_conteo_sin_identificadores_ni_respuestas(self):
        ia, bie = self.fuentes()
        _, _, auditoria = limpiar_fuentes(ia, bie)
        por_campo = {fila['campo']: fila for fila in auditoria['ia']['columnas']}
        self.assertEqual(por_campo['timestamp_ia']['ausentes_limpios'], 1)
        self.assertEqual(por_campo['otros_usos_raw']['ausentes_limpios'], 1)
        self.assertEqual(por_campo['otros_usos_raw']['modificados'], 2)
        salida = json.dumps(auditoria, ensure_ascii=False)
        for dato_individual in ['434343434', 'Repaso', 'Campo sintético', '08:21:05']:
            self.assertNotIn(dato_individual, salida)

    def test_variante_cercana_aislada_y_alias_exacto(self):
        patrones = {'gemini': r'\bgemini\b', 'chatgpt': r'\bchat\s*gpt\b', 'copilot': r'\bcopilot\b'}
        herramientas = detectar_herramientas('chat gpt geminni coipilot', patrones,
                                             original='Chat GPT, Geminni y Coipilot')
        self.assertEqual(herramientas, {'chatgpt', 'gemini', 'copilot'})
        self.assertEqual(detectar_herramientas('estas palabras no son geminni', patrones,
                                               original='Estas palabras no son geminni.'), set())


if __name__ == '__main__':
    unittest.main()
