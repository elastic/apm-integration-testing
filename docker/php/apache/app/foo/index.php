<?php
use Elastic\Apm\ElasticApm;

$transaction = ElasticApm::getCurrentTransaction();
$span = $transaction->beginCurrentSpan(
    'foo',
    'app',
);
?>
foo
<?php
$span->end();
?>
