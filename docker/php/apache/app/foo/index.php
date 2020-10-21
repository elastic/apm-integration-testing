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
<<<<<<< HEAD
    // and frame for call to $span->end() below are included in span's stacktrace
    if ($depthLeft > 2) {
        dummyFuncToAddDepthToStacktrace($depthLeft - 1);
    } else {
        $span->end();
    }
=======
    // and $span->end() frame are counted
    if ($depthLeft > 2) {
        dummyFuncToAddDepthToStacktrace($depthLeft - 1);
    }

    $span->end();
>>>>>>> 44983ff (Added stack depth to conform to 'assert 15 < len(stacktrace) < 70')
}

dummyFuncToAddDepthToStacktrace(15);
?>
