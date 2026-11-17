<?php

namespace ECidade\V3\Error\Handler;

use \ECidade\V3\Extension\Registry;
use \ECidade\V3\Error\Trace;
use \ECidade\V3\Error\EntityFactory;

class Error implements HandlerInterface {

  private $entity;

  public static function register() {
    return set_error_handler(array(__CLASS__, '_handle'), Registry::get('app.config')->get('php.error_reporting'));
  }

  /**
   * Function to explicit return false and populate php_errormsg
   * T-026: $context opcional -- o PHP 8 chama o callback do set_error_handler com 4 argumentos (o $errcontext saiu).
   */
  public static function _handle($type, $message, $file, $line, $context = null) {
    static::handle($type, $message, $file, $line, $context);
    return false;
  }

  public static function handle($type, $message, $file, $line, $context) {

    // T-026: erro suprimido com @. No 5.6 o error_reporting() dentro do @ e 0; no PHP 8 ele mantem os bits de erro
    // fatal (E_ERROR|E_CORE_ERROR|E_COMPILE_ERROR|E_USER_ERROR|E_RECOVERABLE_ERROR|E_PARSE = 4437). Suprimido = nenhum
    // bit alem desses. Caso-limite: nivel posto pela aplicacao so com bits fatais (fora do @) tambem conta como suprimido.
    $suppress = (error_reporting() & ~(E_ERROR | E_CORE_ERROR | E_COMPILE_ERROR | E_USER_ERROR | E_RECOVERABLE_ERROR | E_PARSE)) === 0;

    if ($suppress) {
      return false;
    }

    $trace = new Trace();
    $trace->filter(function($trace) {
      if (!isset($trace['class'])) return true;
      return $trace['class'] !== __CLASS__;
    });

    $entity = EntityFactory::create($type, $suppress, $message, $file, $line, time(), $trace);

    Registry::get('app.eventManager')->trigger('app.error', null, array($entity));

    return $entity;
  }

}
