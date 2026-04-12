# Conversation Module

Role:

- prepare approved drafts and run explicitly approved sends
- keep thread memory and next actions
- stay under policy and rate limits

Profile binding:

- `337`

Default safety mode:

- human approval required
- separate approval for `prepare_draft` and `send_message`
- no autonomous high-volume outreach

Memory:

- `knowledge/llm_wiki/conversations/`
- `knowledge/llm_wiki/campaigns/`
- `knowledge/llm_wiki/decisions/`
