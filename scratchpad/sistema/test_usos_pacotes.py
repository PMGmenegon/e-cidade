import importlib.util, os, unittest

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'usos_pacotes.py')
_spec = importlib.util.spec_from_file_location('usos_pacotes', _p)
up = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(up)


def casa(pacote, linha):
    for p, _, pats in up.COMPILADOS:
        if p.startswith(pacote):
            return any(rx.search(linha) for _, rx in pats)
    raise KeyError(pacote)


class PadroesTest(unittest.TestCase):
    def test_casa(self):
        casos = [('silex', 'use Silex\\Application;'), ('silex', '"Silex\\\\Application"'), ('silex', 'use Pimple\\Container;'),
                 ('proner', 'use Proner\\PhpPimaco\\Pimaco;'), ('dbseller/phinx', 'use Classes\\PostgresMigration;'),
                 ('dbseller/phinx', 'use Phinx\\Migration\\AbstractMigration;'),
                 ('dbseller/sdk', 'use Swagger\\Client\\Api\\PixApi;'), ('mpdf', '$m = new mPDF();'),
                 ('mpdf', 'new \\Mpdf\\Mpdf()'), ('phpoffice/phpspreadsheet', 'use PhpOffice\\PhpSpreadsheet\\IOFactory;'),
                 ('phpoffice/phpword', 'new \\PhpOffice\\PhpWord\\PhpWord()'), ('zend', 'use Zend\\EventManager\\EventManager;')]
        for pac, linha in casos:
            self.assertTrue(casa(pac, linha), (pac, linha))

    def test_nao_casa(self):
        for pac, linha in [('silex', '$silex = 1;'), ('mpdf', '$x = "mpdf"'), ('zend', '$zend = 1;'),
                           ('phpoffice/phpword', 'use PhpOffice\\PhpSpreadsheet\\X;')]:
            self.assertFalse(casa(pac, linha), (pac, linha))

    def test_classifica_uso(self):
        self.assertEqual(up.classifica_uso('  // use Silex\\Application;'), 'comentario')
        self.assertEqual(up.classifica_uso(' * @param Silex\\Application $a'), 'comentario')
        self.assertEqual(up.classifica_uso('use Silex\\Application;'), 'use')
        self.assertEqual(up.classifica_uso('$a = new mPDF();'), 'new')
        self.assertEqual(up.classifica_uso('$a = \\Mpdf\\Mpdf::x();'), 'estatico')


if __name__ == '__main__':
    unittest.main()
