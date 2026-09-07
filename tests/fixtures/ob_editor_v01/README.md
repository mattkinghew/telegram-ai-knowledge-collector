# OB Editor V0.1 acceptance fixtures

這些是 test-only 觸發方式，不是 production debug endpoint，也不會呼叫
Gemini 或其他付費模型。

在 repository root 執行：

```bash
PYTHONPATH=src:. .venv/bin/python -m unittest \
  tests.test_ob_editor_v01_capture_contract -v
```

對應關係：

- normal success：`MockProvider`
- delayed processing：`CaptureService(defer_processing=True)` 的 pending，
  再呼叫 `process_existing`
- AI failure：`FailureProvider("AI_UNAVAILABLE")`
- malformed AI result：`OpaqueProvider` 回傳不符合 ProviderResult 的 object
- processing timeout：`FailureProvider("AI_TIMEOUT")`

每個 fixture 使用 temporary SQLite；failure 測試會再次從 store/GET 讀取
raw content。若要做真機 delayed processing，只能使用已配置的 Gemini
環境，並承擔外部服務、費用與網路變動；本 repository 不提供可由外部呼叫
的 debug route。
