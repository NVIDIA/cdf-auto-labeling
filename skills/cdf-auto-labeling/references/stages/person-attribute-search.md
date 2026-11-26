# Person Attribute Search stage

The stage key is `person_attribute_search`; its image/build product is
`event-and-person-attribute-search-service`. The service is an assembly and
query-generation boundary. It never inspects media, captions images/video, runs
Visual QA, detects people, copies crops, or creates tracking manifests.

## Instructions

1. Before processing real individuals, confirm and document consent or another
   valid legal basis, the permitted purpose, the applicable retention period,
   and any required privacy or legal review.
2. Identify the source: one explicit `--attribute-json`, canonical single-person
   `visual_qa/items.json`, or video tracks plus namespaced per-track VQA windows.
3. Confirm every configured sidecar has an explicit upstream producer. For
   video, detection must produce `detection_and_tracking/tracks.json`; a separate
   Visual QA node must produce the configured item/window paths.
4. Configure the direct `person_attribute_search:` block. Use the shared LLM
   endpoint for per-person tiered queries or chunk-level caption/anomaly buckets.
   Do not add VLM fields or nested producer blocks.
5. For explicit attributes, pass `--attribute-json` as a node argument and keep
   exactly one service `DataEntry`. Bundle mode writes one matching entry per
   source image in the explicit JSON.
6. Suggest a workflow-runner dry-run and verify the PAS command contains its LLM
   settings and resolved source/config paths, but no VLM arguments.

## Configuration examples

Single or multi-view canonical VQA input:

```yaml
person_attribute_search:
  enabled: true
  dataset: upa
  visual_qa_item_sidecars: [visual_qa/items.json]
  visual_qa_window_sidecars: [visual_qa/windows.normalized.json]
  caption_sidecars: [captioning/image_caption.json]
  llm_query_generation: true
  use_template_for_medium: false
  bundle_query_generation: false
  bucket_query_generation: false
```

Video EPAS input and query buckets:

```yaml
person_attribute_search:
  enabled: true
  dataset: upa
  tracks_sidecars: [detection_and_tracking/tracks.json]
  visual_qa_item_sidecars: [visual_qa_per_track/items.json]
  visual_qa_window_sidecars: [visual_qa_per_track/windows.normalized.json]
  video_captions_sidecars: [captioning/video_captions.json]
  anomaly_items_sidecars: [visual_qa_anomaly/items.json]
  llm_query_generation: true
  bucket_query_generation: true
  emit_contextual: true
  emit_daft_contextual: true
```

Explicit attribute bundle input belongs in node args:

```yaml
workflow:
  nodes:
    person_attribute_search:
      stage: person_attribute_search
      args:
        - --attribute-json
        - data/input_media/attributes.json
        - --query-prompt-file
        - ../pas_synonymous_query_prompt.json
person_attribute_search:
  dataset: upa
  bundle_query_generation: true
  bundle_query_count: 3
  llm_query_generation: false
  bucket_query_generation: false
```

## Direct Python CLI

With the service installed in the active Python environment, PAS can run without
Docker, workflow-runner, or a configuration file:

```bash
python -m event_and_person_attribute_search_service.main \
  --input-file /path/to/input.jsonl \
  --attribute-json /path/to/attributes.json \
  --query-prompt-file cookbooks/visual_attribute_search/pas_synonymous_query_prompt.json \
  --query-count 3 \
  --llm-endpoint-url https://inference-api.nvidia.com/v1 \
  --llm-model <served-model-name> \
  --temperature 0 --max-tokens 2048
```

Run this example from the repository root. Attribute and prompt files are input
data, not service configuration. Keep exactly one input entry for explicit
attributes. Named flags are the primary interface; optional `--config-file`
and advanced `--set` follow the same precedence and snapshot rules as
[Reasoning](reasoning.md#direct-python-cli). PAS consumes existing attributes;
this command does not run upstream detection, captioning, or VQA.

## Outputs

- Explicit bundle: `bundle_attributes.json`, `bundle_queries.json`, optional
  `bundle_hitl.json`.
- Single identity: `attributes.json`, `queries.json`, optional `hitl.json`.
- Video: `pas.json`, `chunk_queries.json`, optional `pas_anomaly.json` and
  `contextual/person_attributes.json`.

All PAS sidecars live under `sidecars/person_attribute_search/`.

> **Sensitive-data warning:** These artifacts, including `person_attributes.json`
> and `bundle_queries.json`, may contain personal data, biometric-adjacent
> attributes, or other PII derived from images, crops, or video. Before using PAS
> on real individuals, identify and document consent or another valid legal basis
> and confirm compliance with all applicable laws, which may include the GDPR,
> CCPA/CPRA, and Illinois BIPA. Restrict input and output directories to authorized
> personnel and service accounts using least-privilege permissions; do not place
> artifacts in public or broadly shared locations. Encrypt artifacts at rest,
> apply a documented purpose-limited retention schedule, and securely delete the
> source media, crops, sidecars, query bundles, backups, and derived copies when
> that period expires. Obtain qualified privacy or legal review when requirements
> are uncertain.

## Guardrails

- Do not configure `image_pas`, crop discovery, synthetic tracks, captioning, or
  Visual QA inside this service. This architectural restriction does not reduce
  the privacy obligations for person data produced upstream or consumed by PAS.
- Do not pass a VLM endpoint to PAS.
- Do not claim PAS owns or reuses another service's artifacts.
- Keep execution in the workflow-runner operator skill and require approval for
  real Docker runs.
