# Frontier-shift report (serving path)

**blocked_on:** `{'both': 38, 'none': 5, 'question': 4, 'statement': 3}`

## Leverage — next capability ranked by flip-readiness

| capability | flip_ready | advances | flip-ready cases |
|---|---|---|---|
| `question_extractor` | 4 | 42 | 0007, 0008, 0009, 0035 |
| `no_recognizer_match` | 1 | 10 | 0010 |
| `inject:discrete_count_statement` | 0 | 31 | — |
| `inject:multiplicative_aggregation` | 0 | 6 | — |
| `inject:currency_amount` | 0 | 5 | — |
| `inject:descriptive_setup_no_quantity` | 0 | 5 | — |
| `inject:rate_with_currency` | 0 | 3 | — |
| `inject:temporal_aggregation` | 0 | 3 | — |

## Per case

| case | blocked_on | statement_gaps | question_parses |
|---|---|---|---|
| 0001 | both | rate_with_currency, temporal_aggregation | False |
| 0002 | both | descriptive_setup_no_quantity, discrete_count_statement, no_recognizer_match | False |
| 0003 | both | discrete_count_statement | False |
| 0004 | both | discrete_count_statement, no_recognizer_match | False |
| 0005 | both | no_recognizer_match | False |
| 0006 | both | discrete_count_statement, multiplicative_aggregation | False |
| 0007 | question | — | False |
| 0008 | question | — | False |
| 0009 | question | — | False |
| 0010 | statement | no_recognizer_match | True |
| 0011 | both | rate_with_currency | False |
| 0012 | both | descriptive_setup_no_quantity, discrete_count_statement | False |
| 0013 | both | multiplicative_aggregation | False |
| 0014 | none | temporal_aggregation | False |
| 0015 | both | discrete_count_statement | False |
| 0016 | both | discrete_count_statement | False |
| 0017 | both | discrete_count_statement, temporal_aggregation | False |
| 0018 | none | discrete_count_statement | False |
| 0019 | both | currency_amount, no_recognizer_match | False |
| 0020 | both | discrete_count_statement | False |
| 0021 | both | discrete_count_statement | False |
| 0022 | both | discrete_count_statement, rate_with_currency | False |
| 0023 | both | descriptive_setup_no_quantity, discrete_count_statement | False |
| 0024 | none | — | True |
| 0025 | both | multiplicative_aggregation | False |
| 0026 | both | no_recognizer_match | False |
| 0027 | both | descriptive_setup_no_quantity, discrete_count_statement | False |
| 0028 | both | currency_amount, temporal_aggregation, no_recognizer_match | False |
| 0029 | both | discrete_count_statement | False |
| 0030 | both | discrete_count_statement, no_recognizer_match | False |
| 0031 | both | currency_amount, discrete_count_statement | False |
| 0032 | both | discrete_count_statement, multiplicative_aggregation | False |
| 0033 | both | discrete_count_statement | False |
| 0034 | both | discrete_count_statement | False |
| 0035 | question | — | False |
| 0036 | both | descriptive_setup_no_quantity, discrete_count_statement | False |
| 0037 | both | discrete_count_statement | False |
| 0038 | both | discrete_count_statement | False |
| 0039 | both | discrete_count_statement | False |
| 0040 | both | discrete_count_statement | False |
| 0041 | both | discrete_count_statement | False |
| 0042 | none | — | False |
| 0043 | both | currency_amount, discrete_count_statement | False |
| 0044 | statement | currency_amount, discrete_count_statement | True |
| 0045 | both | discrete_count_statement, multiplicative_aggregation | False |
| 0046 | none | — | True |
| 0047 | both | discrete_count_statement, multiplicative_aggregation | False |
| 0048 | both | no_recognizer_match | False |
| 0049 | both | discrete_count_statement | False |
| 0050 | statement | discrete_count_statement, no_recognizer_match | True |
