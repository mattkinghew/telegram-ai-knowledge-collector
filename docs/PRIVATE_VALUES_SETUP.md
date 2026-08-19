# Private Values Setup

Use `config/private-values.example.json` only as a public shape example. Never edit it with real values. Copy the four values into device-local Shortcut variables or another approved private store.

## Classification

| Value | Must stay only on device | May be stored privately outside Git | Safe example value |
|---|---:|---:|---|
| Real Obsidian Vault identifier | Yes | Only in an approved encrypted backup | `EXAMPLE_VAULT_ID` |
| Active private project names | Preferred | Yes, in an approved private note/config | `Project Alpha` |
| Make webhook URL | Yes | Only in an approved secret manager | `SET_ON_DEVICE_ONLY` |
| API credentials / connection tokens | Yes; use provider/Make connection storage | Only in an approved secret manager | Never create a realistic example |
| AI enabled switch | No | Yes | `false` |
| Employer/client data | Keep in approved work systems only | Only where employer/client policy permits | Use fictional content in this repository |

## Setup

1. Leave the committed example unchanged.
2. On the device, set `VaultID` to the exact Vault identifier used by Obsidian URI handling.
3. Add 3–8 short active project display names; do not copy archived projects.
4. Keep `ai_enabled=false` until optional Make/Gemini setup and privacy approval are complete.
5. If enabling AI, paste the real webhook URL directly on the device. Do not send it through chat, screenshots, Git, or sample payloads.
6. Run `python3 tools/validate_private_config_example.py config/private-values.example.json` only against the public example.

## Never commit

- real Vault ID or absolute Vault path;
- private project names;
- webhook URL;
- API key, token, password, secret, or connection export;
- employer/client data, customer identifiers, or confidential evidence.

The validator intentionally does not search for or load a real config. A passing example validation proves only that the committed placeholder file is safe.
