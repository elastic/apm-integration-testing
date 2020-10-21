<?php
use Elastic\Apm\ElasticApm;

$transaction = ElasticApm::getCurrentTransaction();
$span = $transaction->beginCurrentSpan(
    'foo',
    'app'
);
?>
foo
<?php
function dummyFuncToAddDepthToStacktrace(int $depthLeft): void
{
    global $span;

    // It's 2 because current dummyFuncToAddDepthToStacktrace frame
    // and $span->end() frame are counted
    if ($depthLeft > 2) {
        dummyFuncToAddDepthToStacktrace($depthLeft - 1);
    }

    $span->end();
}

dummyFuncToAddDepthToStacktrace(16);
?>
