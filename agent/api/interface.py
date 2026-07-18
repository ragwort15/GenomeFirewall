"""Multi-provider LLM handler.

Adapted from DeepRare/api/interface.py. Imports for anthropic / google are made
lazy so this module works in the `genomefirewall` env (which only ships openai).
Default provider for Genome Firewall is OpenAI gpt-4o.
"""


class Openai_api:
    def __init__(self, api_key, model="gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def get_completion(self, system_prompt, prompt, seed=42, temperature=0.0):
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                seed=seed,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            return str(completion.choices[0].message.content)
        except Exception as e:
            print(e)
            return None

    def mini_completion(self, system_prompt, prompt, seed=42):
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                seed=seed,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            return str(completion.choices[0].message.content)
        except Exception as e:
            print(e)
            return None

    def get_embedding(self, text, model="text-embedding-3-small"):
        return self.client.embeddings.create(input=[text], model=model).data[0].embedding


class claude_api:
    def __init__(self, api_key, model):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def get_completion(self, system_prompt, prompt, seed=42):
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return str(message.content[0].text)
        except Exception as e:
            print(e)
            return None


def get_handler(provider="openai", api_key=None, model="gpt-4o"):
    """Factory. `api_key` falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY env."""
    import os
    if provider == "openai":
        return Openai_api(api_key or os.environ.get("OPENAI_API_KEY"), model)
    if provider == "claude":
        return claude_api(api_key or os.environ.get("ANTHROPIC_API_KEY"), model)
    raise ValueError(f"unknown provider: {provider}")
