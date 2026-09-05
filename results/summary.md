# Local builder benchmark — summary

_2026-09-05 22:17 · num_predict=8000 · temp=0_

| model | placement | cold-load | task | tier | pass | warm s | tok |
|---|---|--:|---|--:|--:|--:|--:|
| ornith:9b | gpu | 5315ms | t1_dedupe | 1 | 100% | 1.0 | 56 |
| ornith:9b | gpu | 5315ms | t1_parse_kv | 1 | 100% | 1.1 | 65 |
| ornith:9b | gpu | 5315ms | t2_classify | 2 | 100% | 1.1 | 65 |
| ornith:9b | gpu | 5315ms | t2_heat | 2 | 100% | 0.8 | 43 |
| ornith:9b | gpu | 5315ms | t2_tail | 2 | 100% | 0.9 | 52 |
| ornith:9b | gpu | 5315ms | t3_provenance | 3 | 100% | 1.5 | 98 |
| ornith:9b | gpu | 5315ms | t3_fold_edges | 3 | 100% | 1.8 | 116 |
| ornith:9b | gpu | 5315ms | t3_merge | 3 | 100% | 0.9 | 54 |
| ornith:9b | gpu | 5315ms | a2_audit_config | 2 | 0% | 0.2 | 12 |
| ornith:9b | gpu | 5315ms | a2_audit_code | 2 | 100% | 0.2 | 12 |
| gemma4:12b | gpu | 6334ms | t1_dedupe | 1 | 100% | 1.4 | 57 |
| gemma4:12b | gpu | 6334ms | t1_parse_kv | 1 | 100% | 1.9 | 83 |
| gemma4:12b | gpu | 6334ms | t2_classify | 2 | 100% | 1.5 | 64 |
| gemma4:12b | gpu | 6334ms | t2_heat | 2 | 100% | 1.2 | 48 |
| gemma4:12b | gpu | 6334ms | t2_tail | 2 | 100% | 1.1 | 43 |
| gemma4:12b | gpu | 6334ms | t3_provenance | 3 | 100% | 2.7 | 120 |
| gemma4:12b | gpu | 6334ms | t3_fold_edges | 3 | 100% | 2.8 | 128 |
| gemma4:12b | gpu | 6334ms | t3_merge | 3 | 100% | 1.4 | 60 |
| gemma4:12b | gpu | 6334ms | a2_audit_config | 2 | 100% | 0.4 | 12 |
| gemma4:12b | gpu | 6334ms | a2_audit_code | 2 | 100% | 0.4 | 12 |
| gpt-oss:20b | gpu | 11529ms | t1_dedupe | 1 | 100% | 2.4 | 233 |
| gpt-oss:20b | gpu | 11529ms | t1_parse_kv | 1 | 100% | 4.7 | 479 |
| gpt-oss:20b | gpu | 11529ms | t2_classify | 2 | 100% | 3.7 | 375 |
| gpt-oss:20b | gpu | 11529ms | t2_heat | 2 | 100% | 2.4 | 229 |
| gpt-oss:20b | gpu | 11529ms | t2_tail | 2 | 100% | 7.7 | 788 |
| gpt-oss:20b | gpu | 11529ms | t3_provenance | 3 | 100% | 3.9 | 399 |
| gpt-oss:20b | gpu | 11529ms | t3_fold_edges | 3 | 100% | 4.3 | 428 |
| gpt-oss:20b | gpu | 11529ms | t3_merge | 3 | 100% | 3.6 | 373 |
| gpt-oss:20b | gpu | 11529ms | a2_audit_config | 2 | 100% | 2.8 | 273 |
| gpt-oss:20b | gpu | 11529ms | a2_audit_code | 2 | 100% | 1.7 | 155 |
| gemma4:e4b | gpu | 8602ms | t1_dedupe | 1 | 100% | 0.8 | 57 |
| gemma4:e4b | gpu | 8602ms | t1_parse_kv | 1 | 100% | 1.2 | 84 |
| gemma4:e4b | gpu | 8602ms | t2_classify | 2 | 100% | 1.1 | 68 |
| gemma4:e4b | gpu | 8602ms | t2_heat | 2 | 100% | 0.9 | 51 |
| gemma4:e4b | gpu | 8602ms | t2_tail | 2 | 100% | 0.9 | 57 |
| gemma4:e4b | gpu | 8602ms | t3_provenance | 3 | 100% | 1.4 | 105 |
| gemma4:e4b | gpu | 8602ms | t3_fold_edges | 3 | 0% | 1.9 | 141 |
| gemma4:e4b | gpu | 8602ms | t3_merge | 3 | 100% | 0.8 | 64 |
| gemma4:e4b | gpu | 8602ms | a2_audit_config | 2 | 100% | 0.2 | 12 |
| gemma4:e4b | gpu | 8602ms | a2_audit_code | 2 | 100% | 0.3 | 12 |
| qwen3.6:27b | mixed:86% | 18920ms | t1_dedupe | 1 | 100% | 5.0 | 51 |
| qwen3.6:27b | mixed:86% | 18920ms | t1_parse_kv | 1 | 100% | 7.5 | 67 |
| qwen3.6:27b | mixed:86% | 18920ms | t2_classify | 2 | 100% | 6.5 | 65 |
| qwen3.6:27b | mixed:86% | 18920ms | t2_heat | 2 | 100% | 4.2 | 43 |
| qwen3.6:27b | mixed:86% | 18920ms | t2_tail | 2 | 100% | 3.5 | 37 |
| qwen3.6:27b | mixed:86% | 18920ms | t3_provenance | 3 | 100% | 9.4 | 93 |
| qwen3.6:27b | mixed:86% | 18920ms | t3_fold_edges | 3 | 100% | 12.2 | 122 |
| qwen3.6:27b | mixed:86% | 18920ms | t3_merge | 3 | 100% | 5.4 | 54 |
| qwen3.6:27b | mixed:86% | 18920ms | a2_audit_config | 2 | 100% | 1.1 | 12 |
| qwen3.6:27b | mixed:86% | 18920ms | a2_audit_code | 2 | 100% | 1.1 | 12 |
| gemma4:26b | mixed:79% | 17883ms | t1_dedupe | 1 | 100% | 1.2 | 57 |
| gemma4:26b | mixed:79% | 17883ms | t1_parse_kv | 1 | 100% | 2.0 | 83 |
| gemma4:26b | mixed:79% | 17883ms | t2_classify | 2 | 100% | 1.6 | 68 |
| gemma4:26b | mixed:79% | 17883ms | t2_heat | 2 | 100% | 1.1 | 48 |
| gemma4:26b | mixed:79% | 17883ms | t2_tail | 2 | 100% | 0.9 | 41 |
| gemma4:26b | mixed:79% | 17883ms | t3_provenance | 3 | 100% | 2.2 | 105 |
| gemma4:26b | mixed:79% | 17883ms | t3_fold_edges | 3 | 100% | 2.5 | 109 |
| gemma4:26b | mixed:79% | 17883ms | t3_merge | 3 | 100% | 1.4 | 64 |
| gemma4:26b | mixed:79% | 17883ms | a2_audit_config | 2 | 100% | 0.3 | 12 |
| gemma4:26b | mixed:79% | 17883ms | a2_audit_code | 2 | 100% | 0.2 | 12 |
| ornith:35b | mixed:72% | 17739ms | t1_dedupe | 1 | 100% | 1.1 | 51 |
| ornith:35b | mixed:72% | 17739ms | t1_parse_kv | 1 | 100% | 1.8 | 76 |
| ornith:35b | mixed:72% | 17739ms | t2_classify | 2 | 100% | 1.5 | 70 |
| ornith:35b | mixed:72% | 17739ms | t2_heat | 2 | 100% | 0.9 | 43 |
| ornith:35b | mixed:72% | 17739ms | t2_tail | 2 | 100% | 0.8 | 38 |
| ornith:35b | mixed:72% | 17739ms | t3_provenance | 3 | 100% | 2.1 | 98 |
| ornith:35b | mixed:72% | 17739ms | t3_fold_edges | 3 | 100% | 2.8 | 116 |
| ornith:35b | mixed:72% | 17739ms | t3_merge | 3 | 100% | 1.4 | 54 |
| ornith:35b | mixed:72% | 17739ms | a2_audit_config | 2 | 0% | 0.3 | 12 |
| ornith:35b | mixed:72% | 17739ms | a2_audit_code | 2 | 100% | 0.3 | 12 |

## Per model

| model | placement | cold-load | overall pass | median warm s |
|---|---|--:|--:|--:|
| ornith:9b | gpu | 5315ms | 90% | 0.9 |
| gemma4:12b | gpu | 6334ms | 100% | 1.4 |
| gpt-oss:20b | gpu | 11529ms | 100% | 3.7 |
| gemma4:e4b | gpu | 8602ms | 90% | 0.9 |
| qwen3.6:27b | mixed:86% | 18920ms | 100% | 5.2 |
| gemma4:26b | mixed:79% | 17883ms | 100% | 1.3 |
| ornith:35b | mixed:72% | 17739ms | 90% | 1.2 |
