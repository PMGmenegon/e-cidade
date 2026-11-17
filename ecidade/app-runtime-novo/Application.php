<?php

namespace App;

/**
 * Class Application
 * @package App
 */
class Application extends \Illuminate\Foundation\Application
{
    /**
     * Providers de configuration/app.php que o conjunto do Laravel 13 nao traz (o pacote de imagem do 13 e outro).
     * Sao retirados da lista de forma explicita; qualquer outro provider ausente continua falhando no boot.
     * @var string[]
     */
    const PROVIDERS_FORA = [
        'Intervention\Image\ImageServiceProvider',
    ];

    /**
     * @param string|null $basePath
     */
    public function __construct($basePath = null)
    {
        parent::__construct($basePath);

        $this->beforeBootstrapping(\Illuminate\Foundation\Bootstrap\RegisterProviders::class, function ($app) {
            $config = $app->make('config');
            $config->set('app.providers', array_values(array_diff($config->get('app.providers'), self::PROVIDERS_FORA)));
        });
    }

    /**
     * @param string $path
     * @return string
     */
    public function configPath($path = '')
    {
        return $this->basePath . DIRECTORY_SEPARATOR . 'configuration' . ($path ? DIRECTORY_SEPARATOR . $path : $path);
    }
}
