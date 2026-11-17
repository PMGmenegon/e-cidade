<?php

namespace App\Domain\Core\Base\Providers;

use Illuminate\Contracts\Support\DeferrableProvider;
use Illuminate\Support\ServiceProvider;

abstract class BaseDeferredProvider extends ServiceProvider implements DeferrableProvider
{
    /**
     * Retorna os Services registrados no provider.
     * @return array
     */
    public function provides()
    {
        return array();
    }
}
