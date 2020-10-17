<?php
use Elastic\Apm\ElasticApm;

$transaction = ElasticApm::getCurrentTransaction();
$span = $transaction->beginCurrentSpan(
    'foo',
<<<<<<< HEAD
    'app'
=======
    'app',
>>>>>>> bc74219 (add basic PHP agent integration tests (#863))
);
?>
foo
<?php
<<<<<<< HEAD
function dummyFuncToAddDepthToStacktrace(int $depthLeft): void
{
    global $span;

    // It's 2 because current dummyFuncToAddDepthToStacktrace frame
    // and frame for call to $span->end() below are included in span's stacktrace
    if ($depthLeft > 2) {
        dummyFuncToAddDepthToStacktrace($depthLeft - 1);
    } else {
        $span->end();
    }
}

dummyFuncToAddDepthToStacktrace(16);
=======
$span->end();
>>>>>>> bc74219 (add basic PHP agent integration tests (#863))
?>
