# Connector maintenance

## Explicit EA state replay

`connector.replay_reporter_ea_state` is an exceptional read-only recovery
tool for a reporter that has not appended `ea_state` after a sealed chart
attachment. It does not change MT5, its profile, EA, JSONL, terminal process,
or AutoTrading. It requires every magic explicitly, queues only a sealed
snapshot in the local connector buffer, and appends an audit record.

Stop the connector service, run a dry run, then run with `--apply`; finally
start the normal service so its existing authenticated sender drains the queue.
Never use it for JJTI or BEPB.

```powershell
& .\.venv\Scripts\python.exe -m connector.replay_reporter_ea_state `
  --outbox-dir 'C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files' `
  --outbox-filename 'stratos_incubadora_*.jsonl' `
  --account-login '3000108092' `
  --buffer-db 'C:\ProgramData\StratOSQXPro\operational\incubadora\buffer.sqlite' `
  --audit-log 'C:\ProgramData\StratOSQXPro\operational\incubadora\maintenance\reporter-replays.jsonl' `
  --magic 243 --magic 295 --reason 'post_attachment_state_replay' --apply
```
