import unittest

import numpy as np
import pandas as pd

from analisis import FEATURES_CLUSTER, FEATURES_NUM, analizar_clusters, evaluar_modelos


class BusquedasModelosTest(unittest.TestCase):
    def comprobar_busquedas(self, ajuste):
        grid, aleatoria = ajuste['busquedas']
        self.assertEqual(grid['metodo'], 'GridSearchCV')
        self.assertEqual(aleatoria['metodo'], 'RandomizedSearchCV')
        self.assertGreater(grid['configuraciones'], aleatoria['configuraciones'])
        self.assertIn(ajuste['mejor_metodo'], {grid['metodo'], aleatoria['metodo']})
        for fila in ajuste['busquedas']:
            self.assertLessEqual(fila['pliegues_validos'], ajuste['n_folds'])
            self.assertGreaterEqual(fila['desviacion'], 0)

    def test_kmeans_compara_ambas_busquedas_con_silueta_de_validacion(self):
        rng = np.random.default_rng(17)
        datos = rng.normal(0, .1, (18, len(FEATURES_CLUSTER)))
        datos[9:] += 8
        df = pd.DataFrame(datos, columns=FEATURES_CLUSTER).assign(tiene_bienestar=True)

        resultado = analizar_clusters(df)

        ajuste = resultado['ajuste']
        self.comprobar_busquedas(ajuste)
        self.assertEqual(ajuste['metrica'], 'Silueta')
        self.assertEqual(resultado['k'], 2)
        self.assertEqual(sum(resultado['tamanos'].values()), 18)
        for fila in ajuste['busquedas']:
            self.assertEqual(fila['pliegues_validos'], ajuste['n_folds'])
            self.assertGreater(fila['media'], .8)

    def test_knn_ajusta_en_entrenamiento_y_evalua_en_prueba_reservada(self):
        rng = np.random.default_rng(17)
        df = pd.DataFrame(rng.normal(0, 1, (24, len(FEATURES_NUM))), columns=FEATURES_NUM)
        df['tipo_uso_ia'] = ['Híbrido'] * 12 + ['Guía'] * 12
        df['corpus_ia'] = ['comprender ejercicios teoría'] * 12 + ['ahorrar tiempo programa'] * 12

        resultado = evaluar_modelos(df)

        ajuste = resultado['ajuste']
        self.comprobar_busquedas(ajuste)
        self.assertEqual(ajuste['metrica'], 'F1')
        self.assertEqual(ajuste['n_folds'], resultado['n_folds'])
        self.assertEqual(sum(map(sum, ajuste['test']['confusion'])), resultado['n_test'])
        for fila in ajuste['busquedas']:
            self.assertIn('modelo__n_neighbors', fila['parametros'])
            self.assertEqual(fila['pliegues_validos'], resultado['n_folds'])


if __name__ == '__main__':
    unittest.main()
