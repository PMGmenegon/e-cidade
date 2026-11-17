<?php
// pg_lo_export com OID invalido nos pontos restantes: no 5.6 devolve false, no 8.x lanca ValueError (0, null, negativo, nao numerico).
// Para cada ponto o teste le a linha REAL do arquivo-fonte e a executa isolada, com um OID invalido no lugar do OID do ponto:
//  - linha ja com try/catch (apos a correcao): executa a linha como esta;
//  - linha original (antes da correcao): executa so a chamada pg_lo_export(...) cuja expressao foi extraida da linha.
// Tem de nao lancar e nao criar arquivo, nos dois runtimes. So le do banco (begin/rollback por valor); nao grava nada.
// Sem setUp()/tearDown() e sem tipos: o mesmo arquivo roda no PHPUnit 5.7 (5.6) e no 9.6 (8.5).
use PHPUnit\Framework\TestCase;

class PgLoExportOidFalso
{
    public $oid;
    public $arquivo;
    public $rsConexaoOrigem;

    public function __construct($oid, $conn = null)
    {
        $this->oid = $oid;
        $this->arquivo = $oid;
        $this->rsConexaoOrigem = $conn;
    }

    public function getArquivo()
    {
        return $this->oid;
    }
}

class PgLoExportPontosTest extends TestCase
{
    // arquivo => [padrao da linha, preparo das variaveis (usa $oid, $conn, $dest, $falso)]. $this = PgLoExportOidFalso quando o ponto usa $this.
    private function pontos()
    {
        return array(
            'sys4_processarelatorioRPC.php' => array('/\$oArquivoSxw->db15_documento/',
                '$oArquivoSxw = (object) array("db15_documento" => $oid); $sCaminhoTemplate = $dest;'),
            'con4_contratos.RPC.php#documento' => array('/\$oDocumento->getArquivo\(\)/',
                '$oDocumento = $falso; $sNomeArquivo = $dest;'),
            'con4_contratos.RPC.php#membro' => array('/\$membro->getArquivo\(\)/',
                '$membro = $falso; $caminho = $dest;'),
            'libs/db_stdlib.php#configarquivos' => array('/pg_lo_export\(\$conn,\s*\$arquivo,\s*\$caminho\)/',
                '$arquivo = $oid; $caminho = $dest;'),
            'model/integracao/transparencia/IntegracaoContrato.model.php' => array('/\$oDocumento->arquivo/',
                '$oDocumento = $falso; if (!defined("ECIDADE_PATH")) { define("ECIDADE_PATH", ""); }'),
            'model/AcordoComissaoMembro.model.php' => array('/\$this->getArquivo\(\)/',
                '$sPathArquivo = $dest;'),
        );
    }

    public function testOidInvalidoNosPontosDevolveFalseSemLancar()
    {
        $falhas = array();
        foreach ($this->pontos() as $chave => $def) {
            $arquivo = preg_replace('/#.*/', '', $chave);
            $linha = $this->linhaDoPonto($arquivo, $def[0]);
            foreach (array(null, 0, -1, 'abc') as $oid) {
                $dest = tempnam(sys_get_temp_dir(), 'lo042');
                unlink($dest);
                $erro = null;
                $this->emTransacao(function ($conn) use ($linha, $def, $oid, $dest, &$erro) {
                    $erro = $this->executa($linha, $def[1], $oid, $dest, $conn);
                });
                if ($erro !== null || file_exists($dest)) {
                    $falhas[] = $chave . ' com OID ' . var_export($oid, true) . ': ' . ($erro !== null ? $erro : 'criou arquivo');
                }
                if (file_exists($dest)) {
                    unlink($dest);
                }
            }
        }
        $this->assertSame(array(), $falhas, implode("\n", $falhas));
    }

    // OID valido: cada ponto corrigido continua exportando o mesmo conteudo que um pg_lo_export direto (a guarda so troca o ValueError).
    public function testOidValidoContinuaExportandoNosPontos()
    {
        $falhas = array();
        foreach ($this->pontos() as $chave => $def) {
            $arquivo = preg_replace('/#.*/', '', $chave);
            $linha = $this->linhaDoPonto($arquivo, $def[0]);
            $this->emTransacao(function ($conn) use ($chave, $linha, $def, &$falhas) {
                $oid = pg_fetch_result(pg_query($conn, 'select min(oid) from pg_largeobject_metadata'), 0, 0);
                if (!$oid) {
                    $this->markTestSkipped('banco sem large object para ler');
                }
                $ref = tempnam(sys_get_temp_dir(), 'lo042r');
                unlink($ref);
                pg_lo_export($conn, $oid, $ref);
                $dest = tempnam(sys_get_temp_dir(), 'lo042');
                unlink($dest);
                $erro = $this->executa($linha, $def[1], $oid, $dest, $conn);
                $vazio = 'tmp/' . $oid . '.dat';                 // IntegracaoContrato grava em tmp/<oid>.dat em vez de $dest
                $saida = file_exists($dest) ? $dest : (file_exists($vazio) ? $vazio : null);
                if ($erro !== null || $saida === null || md5_file($saida) !== md5_file($ref)) {
                    $falhas[] = $chave . ': ' . ($erro !== null ? $erro : ($saida === null ? 'nao exportou' : 'conteudo diferente'));
                }
                foreach (array($ref, $dest, $vazio) as $f) {
                    if (file_exists($f)) {
                        unlink($f);
                    }
                }
            });
        }
        $this->assertSame(array(), $falhas, implode("\n", $falhas));
    }

    // Pontos que continuam sem guarda por ja serem iguais ao 5.6 em todo valor que alcancam (ver docs/registro/pg-lo-export-oid-invalido.md):
    // o nulo chega como '' (cast para string ou chave de array), e '' devolve false nos dois runtimes.
    public function testNuloComoStringVaziaDevolveFalseNosDoisRuntimes()
    {
        $dest = tempnam(sys_get_temp_dir(), 'lo042');
        unlink($dest);
        $this->emTransacao(function ($conn) use ($dest) {
            $nulo = null;
            $this->assertFalse(@pg_lo_export($conn, "$nulo", $dest));            // convenio.model.php: "$oBanco->db90_logo"
        });
        $this->emTransacao(function ($conn) use ($dest) {
            $chaves = array(null => 'x');                                       // lic4_licitacon.RPC.php: foreach (getAnexos() as $iOID => ...)
            foreach ($chaves as $iOID => $v) {
                $this->assertFalse(@pg_lo_export($conn, $iOID, $dest));
            }
        });
        $this->assertFalse(file_exists($dest));
    }

    private function linhaDoPonto($arquivo, $padrao)
    {
        $texto = file_get_contents(__DIR__ . '/../../../' . $arquivo);
        $escolhida = null;
        foreach (preg_split('/\r?\n/', $texto) as $linha) {
            if (strpos($linha, 'pg_lo_export') !== false && preg_match($padrao, $linha)) {
                $escolhida = $linha;
                if (strpos($linha, 'try {') !== false) {
                    break;                                   // prefere a linha ja com a guarda
                }
            }
        }
        $this->assertNotNull($escolhida, "$arquivo: linha do ponto nao encontrada");
        return $escolhida;
    }

    // Devolve null se a linha nao lancou; a mensagem se lancou.
    private function executa($linha, $preparo, $oid, $dest, $conn)
    {
        if (strpos($linha, 'try {') === false) {
            if (!preg_match('/pg_lo_export\s*\(/', $linha, $m, PREG_OFFSET_CAPTURE)) {
                return 'sem chamada pg_lo_export na linha';
            }
            $ini = $m[0][1];
            $nivel = 0;
            $fim = $ini;
            for ($i = $ini; $i < strlen($linha); $i++) {
                if ($linha[$i] === '(') { $nivel++; }
                if ($linha[$i] === ')') { $nivel--; if ($nivel === 0) { $fim = $i; break; } }
            }
            $linha = '$r = ' . substr($linha, $ini, $fim - $ini + 1) . ';';
        }
        $falso = new PgLoExportOidFalso($oid, $conn);
        // eval() de proposito: executa a linha do proprio arquivo-fonte do repositorio (conteudo confiavel, so em teste), isolada.
        $corpo = function () use ($linha, $preparo, $oid, $dest, $conn, $falso) {
            eval($preparo . ' ' . $linha);
        };
        $corpo = Closure::bind($corpo, $falso, 'PgLoExportOidFalso');
        try {
            @$corpo();
        } catch (\Throwable $e) {
            return get_class($e) . ': ' . $e->getMessage();
        } catch (\Exception $e) {
            return get_class($e) . ': ' . $e->getMessage();
        }
        return null;
    }

    private function emTransacao($corpo)
    {
        if (!getenv('DB_HOST')) {
            $this->markTestSkipped('DB_HOST ausente: runtime sem acesso ao banco');
        }
        $GLOBALS['conn'] = pg_connect('host=' . getenv('DB_HOST') . ' port=' . (getenv('DB_PORT') ?: '5432')
            . ' dbname=' . getenv('DB_DATABASE') . ' user=' . getenv('DB_USERNAME') . ' password=' . getenv('DB_PASSWORD'));
        $conn = $GLOBALS['conn'];
        pg_query($conn, 'begin');
        try {
            $corpo($conn);
        } catch (\Exception $e) {
            pg_query($conn, 'rollback');
            throw $e;
        }
        pg_query($conn, 'rollback');
    }
}
