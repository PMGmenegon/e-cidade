<?php
/**
 * T-004: mesma config do projeto (rector-curado.php, regras e denylist intactas); muda SO a
 * execucao paralela -- o timeout padrao de 120 s por processo filho estourou na varredura de
 * 20 mil arquivos ("Child process timed out after 120 seconds") e o Rector abortou com 0 arquivos.
 * Paralelo: 6 processos (a maquina de 16 nucleos e dividida com outros processos).
 * Uso: copiar para ecidade/tmp/rector/ junto com rector-curado.php e passar em --config.
 */
return (require __DIR__ . '/rector-curado.php')->withParallel(1800, 6, 8);
