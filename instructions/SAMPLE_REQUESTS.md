# Sample Requests

Use these as a lightweight behavior check. They are not exhaustive.

## Document Q&A

```text
Explain @cloud_formation in simple words.
```

Expected behavior:

- uses `cloud_formation`
- answers from the document
- does not call external search
- mentions the section ID used

```text
Which section talks about condensation?
```

Expected behavior:

- identifies `cloud_formation`
- explains that condensation is gas changing back into liquid water
- does not call external search

## Summarization

```text
Summarize @cloud_classification in 3 bullets.
```

Expected behavior:

- fetches `cloud_classification`
- summarizes from section text only
- does not create a change proposal because the user asked for a summary, not an update

## Rewrite Requests

```text
Shorten @cloud_formation to around 100 words.
```

Expected behavior:

- fetches `cloud_formation`
- creates a pending change proposal
- does not directly overwrite the section
- does not use external search unless the implementation can justify why it is needed

```text
Rewrite @cloud_classification for a middle-school audience.
```

Expected behavior:

- creates a pending change proposal
- preserves the original text
- returns a clear reason for the proposed change

## External Verification

```text
Review @clouds_climate_change using NASA or NOAA sources and suggest a more precise version.
```

Expected behavior:

- fetches `clouds_climate_change`
- calls `nasa_search_tool`, `noaa_climate_search_tool`, or both
- returns evidence used
- creates a pending change proposal
- does not overwrite the section until accepted

```text
Check if @cloud_classification is accurate using external sources.
```

Expected behavior:

- fetches `cloud_classification`
- calls an appropriate external evidence tool
- returns a fact-check summary with citations/evidence
- does not create a change proposal unless the user asks for an update

```text
Find evidence for the claim that clouds affect climate.
```

Expected behavior:

- identifies the relevant section, likely `clouds_climate_change`
- calls NASA/NOAA/general web search as appropriate
- returns concise evidence with source titles, URLs, and supporting text

## Change Review

```text
Compare change_001.
```

Expected behavior:

- returns original text, proposed text, and a readable diff
- does not mutate document state

```text
Accept change_001.
```

Expected behavior:

- applies the proposed text to the section
- increments the section version
- stores the previous version in history
- marks the proposal as accepted

```text
Reject change_001.
```

Expected behavior:

- keeps the section unchanged
- marks the proposal as rejected

## Negative Cases

```text
Accept change_999.
```

Expected behavior:

- returns a clear not-found error
- does not mutate document state

```text
Accept change_001 twice.
```

Expected behavior:

- first request accepts the change
- second request returns a clear invalid-state error
- version history is not duplicated

```text
What is CRISPR-Cas9?
```

Expected behavior:

- says the answer is outside the document
- may use `general_web_search_tool` only if the user explicitly asks for external information
