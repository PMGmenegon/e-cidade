<?php

namespace ECidade\V3\Error\Handler;

use \ECidade\V3\Error\Handler\Error;
use PHPUnit_Framework_TestCase;

class ErrorTest extends PHPUnit_Framework_TestCase
{

    public function testHandle()
    {

        $type = E_ERROR;
        $message = 'Test message';
        $file = 'testfile';
        $line = 9;

        $entity = Error::handle($type, $message, $file, $line, array());
        $this->assertEquals($type, $entity->getType());
        $this->assertEquals($message, $entity->getMessage());
        $this->assertEquals($file, $entity->getFile());
        $this->assertEquals($line, $entity->getLine());
    }

    public function testHandleWithoutReporting()
    {

        $type = E_ERROR;
        $message = 'Test message';
        $file = 'testfile';
        $line = 9;

        // T-026: era error_reporting(null). No PHP 8 o null quer dizer "nao mude" (o nivel fica como esta);
        // no 5.6 zerava. O 0 zera nos dois, que e o que o teste quer preparar. Assercao igual.
        error_reporting(0);

        $this->assertFalse(Error::handle($type, $message, $file, $line, array()));
    }

    /**
     * T-026: erro suprimido com @ continua suprimido no PHP 8. Dentro do @ o 5.6 da error_reporting() = 0 e o
     * PHP 8 da error_reporting() = so os bits de erro fatal (4437); os dois tem de devolver false.
     */
    public function testHandleSuppressedByAt()
    {
        $nivel = error_reporting(E_ALL);

        $suprimido = @Error::handle(E_USER_WARNING, 'Test message', 'testfile', 9, array());
        $naoSuprimido = Error::handle(E_USER_WARNING, 'Test message', 'testfile', 9, array());

        error_reporting($nivel);

        $this->assertFalse($suprimido);
        $this->assertInstanceOf('\\ECidade\\V3\\Error\\Entity', $naoSuprimido);
    }
}
