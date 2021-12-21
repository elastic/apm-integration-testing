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
    // and frame for call to $span->end() below are included in span's stacktrace
    if ($depthLeft > 2) {
        dummyFuncToAddDepthToStacktrace($depthLeft - 1);
    } else {
        $span->end();
    }
}

dummyFuncToAddDepthToStacktrace(16);
?>
