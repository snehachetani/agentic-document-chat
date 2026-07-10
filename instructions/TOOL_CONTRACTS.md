# Tool Contracts

The assignment should include external evidence tools and internal document operations.

External tools may be implemented with Tavily, mocked with realistic deterministic responses, or replaced with another equivalent search provider. If using Tavily, load the API key from `TAVILY_API_KEY` and restrict searches to the required domains.

The candidate should not spend most of the assignment building search infrastructure. Focus on when and how the agent uses tools.

## External Evidence Tools

### `general_web_search_tool`

Use only when the user asks for general external information and the document itself is not enough.

Input:

```json
{
  "query": "string",
  "allowed_domains": ["string"],
  "max_results": 5
}
```

Output:

```json
{
  "results": [
    {
      "title": "string",
      "url": "string",
      "source_domain": "string",
      "snippet": "string",
      "retrieved_text": "string"
    }
  ]
}
```

Expected behavior:

- Do not call this tool for every request.
- First check whether the answer can be handled from the document.
- Respect `allowed_domains`.

### `nasa_search_tool`

Use when the user asks to verify, improve, or rewrite cloud/climate content using NASA-style evidence.

Input:

```json
{
  "query": "string",
  "section_id": "string",
  "max_results": 5
}
```

Output:

```json
{
  "results": [
    {
      "source_title": "string",
      "source_url": "string",
      "retrieved_text": "string",
      "relevance_reason": "string"
    }
  ]
}
```

Example use cases:

```text
Check whether @cloud_formation is scientifically accurate using NASA sources.
Update @clouds_climate_change to align better with NASA-style scientific explanation.
Find evidence for the claim that clouds affect climate.
```

Suggested domain restriction: `nasa.gov`.

### `noaa_climate_search_tool`

Use when the user asks about weather, climate, atmosphere, cloud classification, climate measurement, or long-term climate patterns.

Input:

```json
{
  "query": "string",
  "section_id": "string",
  "max_results": 5
}
```

Output:

```json
{
  "results": [
    {
      "source_title": "string",
      "source_url": "string",
      "retrieved_text": "string",
      "relevance_reason": "string"
    }
  ]
}
```

Example use cases:

```text
Verify the definition of climate in @clouds_climate_change.
Check if @cloud_classification is accurate.
Improve the climate change paragraph using authoritative climate/weather sources.
```

Suggested domain restriction: `noaa.gov`.

### Optional: `pubmed_search_tool`

This is optional for the clouds document because PubMed is not the most natural source for this topic. It is included to show how the same architecture could later support biomedical or regulatory evidence tools.

Input:

```json
{
  "query": "string",
  "max_results": 5
}
```

Output:

```json
{
  "results": [
    {
      "title": "string",
      "authors": ["string"],
      "journal": "string",
      "year": "string",
      "abstract": "string",
      "url": "string",
      "relevance_reason": "string"
    }
  ]
}
```

Suggested domain restrictions: `pubmed.ncbi.nlm.nih.gov`, `ncbi.nlm.nih.gov`.

## Internal Document Operations

The following operations define the expected document workflow. They may be implemented as tools, service methods, repository methods, API handlers, or some combination. They are intentionally not solved by the starter code.

### `get_document_structure`

Returns section IDs, titles, and current versions.

Output example:

```json
{
  "document_id": "clouds_doc_v1",
  "sections": [
    {
      "section_id": "cloud_formation",
      "title": "CLOUD FORMATION",
      "version": 1
    },
    {
      "section_id": "cloud_classification",
      "title": "CLOUD CLASSIFICATION",
      "version": 1
    },
    {
      "section_id": "clouds_climate_change",
      "title": "CLOUDS AND CLIMATE CHANGE",
      "version": 1
    },
    {
      "section_id": "condensation_nuclei",
      "title": "CONDENSATION NUCLEI",
      "version": 1
    },
    {
      "section_id": "clouds_and_radiation",
      "title": "CLOUDS AND RADIATION",
      "version": 1
    },
    {
      "section_id": "observing_clouds",
      "title": "OBSERVING CLOUDS",
      "version": 1
    },
    {
      "section_id": "clouds_and_weather",
      "title": "CLOUDS AND WEATHER",
      "version": 1
    }
  ]
}
```

### `get_section`

Input:

```json
{
  "section_id": "string"
}
```

Output:

```json
{
  "section_id": "string",
  "title": "string",
  "content": "string",
  "version": 1
}
```

### `create_change_proposal`

Input:

```json
{
  "section_id": "string",
  "original_text": "string",
  "proposed_text": "string",
  "reason_for_change": "string",
  "evidence_used": []
}
```

Output:

```json
{
  "change_id": "string",
  "status": "pending"
}
```

### `compare_change`

Input:

```json
{
  "change_id": "string"
}
```

Output:

```json
{
  "change_id": "string",
  "section_id": "string",
  "diff": "string",
  "original_text": "string",
  "proposed_text": "string"
}
```

### `accept_change`

Input:

```json
{
  "change_id": "string"
}
```

Output:

```json
{
  "change_id": "string",
  "section_id": "string",
  "status": "accepted",
  "new_version": 2
}
```

### `reject_change`

Input:

```json
{
  "change_id": "string"
}
```

Output:

```json
{
  "change_id": "string",
  "section_id": "string",
  "status": "rejected"
}
```
