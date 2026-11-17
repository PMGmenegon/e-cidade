#!/usr/bin/env python3
"""Testes da logica pura do comparador (scratchpad/cmp.py). Sem rede, sem docker.
Rodar: python3 -m unittest discover -s scratchpad/sistema -p 'test_*.py'
"""
import importlib.util, os, tempfile, unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cmp_sistema', os.path.join(os.path.dirname(AQUI), 'cmp.py'))
cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp)


class Lados(unittest.TestCase):
    def test_parse_lado_completo(self):
        l = cmp.parse_lado('10.0.0.5:8161@ecidade_x_85')
        self.assertEqual((l.host, l.porta, l.container, l.base()), ('10.0.0.5', 8161, 'ecidade_x_85', 'http://10.0.0.5:8161'))

    def test_parse_lado_host_padrao(self):
        self.assertEqual(cmp.parse_lado('8080@ecidade_php56').base(), 'http://localhost:8080')

    def test_parse_lado_invalido(self):
        for ruim in ('', '8080', 'x@y', '8080@'):
            with self.assertRaises(ValueError):
                cmp.parse_lado(ruim)

    def test_normaliza_porta_de_qualquer_lado(self):
        regras = cmp.normalizadores([cmp.parse_lado('8160@a'), cmp.parse_lado('8161@b')])
        self.assertEqual(cmp.norm(b'http://localhost:8160/x http://localhost:8161/x', regras),
                         b'http://localhost:PORT/x http://localhost:PORT/x')

    def test_normaliza_ids_aleatorios(self):
        regras = cmp.normalizadores([])
        self.assertEqual(cmp.norm(b'sid=0123456789abcdef tmp/rel_123.pdf', regras), b'sid=X tmp/X.pdf')


class Conhecidas(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False)
        self.f.write('# comentario\n\nedu1_calendarioescola002\tDIVERGE\tarea-educacao.md\tquebra tambem no 5.6\n'
                     'rec2_espelhoponto002.php\tTIMEOUT\tarea-recursos-humanos.md\tlento\n')
        self.f.close()
        self.k = cmp.carrega_conhecidas(self.f.name)

    def tearDown(self):
        os.unlink(self.f.name)

    def test_carrega_normalizando_nome(self):
        self.assertEqual(set(self.k), {'edu1_calendarioescola002.php', 'rec2_espelhoponto002.php'})

    def test_conhecida_nao_conta(self):
        self.assertEqual(cmp.classifica('edu1_calendarioescola002.php', 'DIVERGE', self.k), ('CONHECIDA', 'area-educacao.md'))

    def test_nova(self):
        self.assertEqual(cmp.classifica('cem1_x001.php', 'DIVERGE', self.k)[0], 'NOVA')

    def test_tipo_diferente_do_registrado_e_nova(self):
        # registrada como DIVERGE, agora TIMEOUT: nao e a mesma caracterizacao
        self.assertEqual(cmp.classifica('edu1_calendarioescola002.php', 'TIMEOUT', self.k)[0], 'NOVA')

    def test_conhecida_que_ficou_identica_e_resolvida(self):
        self.assertEqual(cmp.classifica('edu1_calendarioescola002.php', 'IDENTICA', self.k)[0], 'RESOLVIDA')

    def test_arquivo_ausente(self):
        self.assertEqual(cmp.carrega_conhecidas('/nao/existe.tsv'), {})


class Selecao(unittest.TestCase):
    def test_nome_tela(self):
        self.assertEqual(cmp.nome_tela('cem1_a001'), 'cem1_a001.php')
        self.assertEqual(cmp.nome_tela('cem1_a001.php?x=1'), 'cem1_a001.php')

    def test_le_telas_ignora_comentarios(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write('# c\ncem1_a\n\nitb1_b.php\n')
        try:
            self.assertEqual(cmp.le_telas(f.name), ['cem1_a.php', 'itb1_b.php'])
        finally:
            os.unlink(f.name)

    def test_regex_location_casa_prefixos(self):
        import re
        rx = re.compile(cmp.REGEX_LOCATION, re.I)
        for ok in ('cem1_x.php', 'edu4_y.php', 'sys3_z.php', 'sau2_a.php'):
            self.assertTrue(rx.match(ok), ok)
        for ruim in ('db_x.php', 'index.php', 'dbforms_x.php'):
            self.assertFalse(rx.match(ruim), ruim)


class Diferenca(unittest.TestCase):
    def test_primeira_diferenca(self):
        n, ta, tb = cmp.primeira_diferenca(b'abc\nXdef', b'abc\nYdef')
        self.assertEqual(n, 4)
        self.assertIn('Xdef', ta)
        self.assertIn('Ydef', tb)

    def test_tamanhos_diferentes(self):
        n, ta, tb = cmp.primeira_diferenca(b'abc', b'abcd')
        self.assertEqual(n, 3)


class Args(unittest.TestCase):
    def test_legado(self):
        a = cmp.monta_args(['SID1', '^cem1_', '/tmp/o.tsv'])
        self.assertEqual((a.sid, a.prefixo, a.saida, a.a, a.b), ('SID1', '^cem1_', '/tmp/o.tsv', '8080@ecidade_php56', '8085@ecidade_php85'))

    def test_parametrizado(self):
        a = cmp.monta_args(['--sid', 'S', '--a', '8160@x56', '--b', '8161@x85', '--prefixo', '^itb1_'])
        self.assertEqual((a.a, a.b), ('8160@x56', '8161@x85'))

    def test_sem_selecao_e_erro(self):
        with self.assertRaises(SystemExit):
            cmp.monta_args(['--sid', 'S', '--a', '1111@a', '--b', '2222@b'])


if __name__ == '__main__':
    unittest.main()
