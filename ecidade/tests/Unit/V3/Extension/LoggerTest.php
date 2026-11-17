<?php

namespace ECidade\V3\Extension;

use \ECidade\V3\Extension\Logger;

class LoggerTest extends \PHPUnit\Framework\TestCase // T-026: era PHPUnit_Framework_TestCase (nao existe no PHPUnit 9)
{

    protected $logger;

    /**
     * T-026: era setUp(). O PHPUnit 9 exige setUp(): void, que nao compila no 5.6; @before existe no 5.7 e no 9.
     * @before
     */
    public function preparaLogger()
    {
        $this->logger = new Logger('php://output', Logger::DEBUG);
    }

    /**
     * T-026: era tearDown() (mesmo motivo do preparaLogger).
     * @after
     */
    public function descartaLogger()
    {
        $this->logger = null;
    }

  //expectOutputString

  /**
   * @dataProvider provideMessages
   */
    public function testMessageLevels($message)
    {

        $template = '['. date('Y-m-d H:i:s') .'] %s: ' . $message . "\n";

        $expect = str_repeat($template, 5);

        $this->logger->info($message);
        $this->logger->notice($message);
        $this->logger->warning($message);
        $this->logger->error($message);
        $this->logger->debug($message);

        $this->expectOutputString(sprintf($expect, 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'DEBUG'));
    }

    public function provideMessages()
    {
        return array(
        array('Mensagem 1'),
        array('Teste de mensagem'),
        array(123456789)
        );
    }

    public function testLogWithWrongLevel()
    {

        $logger = new Logger('php://output', Logger::INFO);

        $this->assertFalse($logger->verbose('test', Logger::DEBUG));
    }

  /**
   * T-026: era @expectedException/@expectedExceptionMessage (removidos no PHPUnit 9); expectException() e
   * expectExceptionMessage() existem no 5.7 e no 9. Mesma excecao, mesma mensagem.
   */
    public function testErrorOnNonExistingFile()
    {
        $this->expectException('\\Exception');
        $this->expectExceptionMessage('Não foi possível abrir o arquivo para escrita');
        $logger = new Logger('/path/to/invalid/file.txt', Logger::INFO);
    }
}
