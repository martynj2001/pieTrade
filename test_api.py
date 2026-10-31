import traceback
import anthropic, config

print("anthropic version:", anthropic.__version__)
client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY.strip(),
                             max_retries=0, timeout=30,
                             default_headers={"Accept-Encoding": "identity"})
try:
    m = client.messages.create(model="claude-haiku-5-5", max_tokens=50,
                               messages=[{"role": "user", "content": "Reply with the word ok"}])
    print("SDK WORKED:", m.content[0].text)
except Exception as e:
    traceback.print_exc()
    print("REAL CAUSE:", repr(getattr(e, "__cause__", None)))