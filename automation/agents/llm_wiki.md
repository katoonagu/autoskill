# LLM Wiki Architecture

## Purpose

`LLM Wiki` is the shared long-term memory layer for all agents.

It is meant to store:

- synthesized knowledge
- agent decisions
- cross-agent context
- reusable outreach and validation playbooks

It is not meant to replace:

- operational state JSON
- raw screenshots
- raw logs
- future retrieval / embeddings / vector search

## Why We Use It Before RAG

Right now we want:

- human-readable knowledge
- zero dependency on embeddings
- easy versioning inside the repo
- direct editability by humans and agents

This gives us shared memory without introducing vector DB infrastructure yet.

## Folder Model

- `knowledge/llm_wiki/brands/`
- `knowledge/llm_wiki/bloggers/`
- `knowledge/llm_wiki/contacts/`
- `knowledge/llm_wiki/campaigns/`
- `knowledge/llm_wiki/conversations/`
- `knowledge/llm_wiki/evidence/`
- `knowledge/llm_wiki/decisions/`
- `knowledge/llm_wiki/playbooks/`
- `knowledge/llm_wiki/templates/`

## Canonical Page Types

### Brand Page

Should include:

- brand identity
- niche and positioning
- reputation summary
- risk flags
- mention frequency
- geo and pricing
- fit by blogger segment
- available contacts

### Blogger Page

Should include:

- audience summary
- content style
- brand fit
- past collabs
- red flags
- recommended outreach style

### Contact Page

Should include:

- person / team
- channel
- source
- confidence
- prior conversation references

### Campaign Page

Should include:

- brand-blogger pairing
- current stage
- score
- rationale
- chosen channel
- outcomes

### Conversation Page

Should include:

- thread summary
- who wrote what
- commitments
- next step
- approval status

### Decision Page

Should include:

- decision type
- evidence used
- confidence
- owner agent
- follow-up tasks

## Update Rules

- `Discovery Agent` writes raw evidence and creates initial brand/blogger stubs
- `Brand Intelligence Agent` enriches brand pages and produces brand scores
- `Outreach Planning Agent` writes decisions and campaign plans
- `Conversation Agent` updates conversation and campaign pages
- `Feedback / Validation Agent` appends contradictory evidence, complaints and validation notes

## Safety Rules

- never overwrite raw evidence with summary text
- keep source links in every wiki page
- use confidence labels on inferred statements
- keep contact and conversation history traceable
- do not auto-escalate to active outreach without explicit decision record

## Future Upgrade Path

When scale grows, we can keep the LLM Wiki as the human-readable memory layer and add:

- BM25 / full-text search
- embeddings
- vector retrieval
- reranking

That future layer should sit under the wiki, not replace it.
