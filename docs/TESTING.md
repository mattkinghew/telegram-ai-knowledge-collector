# Testing

```bash
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m business_knowledge_capture.cli --help
```

Temporary non-sensitive smoke test:

```bash
mkdir -p /tmp/bkc-vault/00_Inbox
mkdir -p /tmp/bkc-vault/10_Work/11_Projects
mkdir -p /tmp/bkc-vault/90_System

PYTHONPATH=src python -m business_knowledge_capture.cli init --vault /tmp/bkc-vault
PYTHONPATH=src python -m business_knowledge_capture.cli capture \
  --vault /tmp/bkc-vault \
  --text "AI PM onboarding example" \
  --title "Smoke test"
PYTHONPATH=src python -m business_knowledge_capture.cli validate --vault /tmp/bkc-vault
```
