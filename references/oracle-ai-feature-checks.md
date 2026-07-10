# Oracle AI Feature Readiness Checks

## Evidence categories

1. Package and synonym visibility.
2. Procedure visibility.
3. Existing AI profiles and attributes.
4. Existing managed vector indexes and attributes.
5. Existing native VECTOR columns and indexes.
6. Credential object visibility.
7. Runtime provider and retrieval tests.

## Status rules

- **not detected**: the current user cannot see required package or procedure evidence.
- **available; setup required**: feature entry points are visible but required profile, credential, or index evidence is absent.
- **blocked by prerequisite**: the feature is visible but a dependent profile or RAG configuration is absent.
- **ready-looking**: stored configuration evidence exists; runtime verification is still required.

Never translate `ready-looking` into production readiness.
