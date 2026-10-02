# Benchmark report — development

Dataset version: `1.0.0`

| Metric | Result |
|---|---:|
| prediction_coverage | 1.000000 |
| field_accuracy | 0.577381 |
| required_field_accuracy | 0.747475 |
| identifier_accuracy | 0.743590 |
| row_accuracy | 0.000000 |
| classification_accuracy | 0.882353 |
| grouping_accuracy | 0.588235 |
| decision_accuracy | 0.000000 |
| cer_mean | N/A |
| wer_mean | N/A |
| latency_ms_p50 | N/A |
| latency_ms_p95 | N/A |
| peak_memory_mb_max | N/A |

Evaluated 9 of 9 documents.

## Regression gate: FAILED

- `required_field_accuracy` = 0.7474747474747475; minimum = 1.0
- `identifier_accuracy` = 0.7435897435897436; minimum = 1.0
- `row_accuracy` = 0.0; minimum = 1.0
- `classification_accuracy` = 0.8823529411764706; minimum = 1.0
- `grouping_accuracy` = 0.5882352941176471; minimum = 1.0
- `decision_accuracy` = 0.0; minimum = 1.0