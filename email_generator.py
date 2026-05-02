import os
import anthropic


def generate_email(
    name: str,
    company: str,
    role: str,
    context: str,
    product_name: str,
    product_desc: str,
    sender_name: str = "Mamadou Lamine TALL",
    tone: str = "professional",
    lang: str = "fr",
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    lang_instr = "Write the email in French." if lang == "fr" else "Write the email in English."

    prompt = f"""You are an expert B2B sales copywriter specialising in AI tools for life sciences and healthcare.
{lang_instr}

Prospect:
- Name: {name}
- Company: {company}
- Role: {role}
- Context / pain point: {context}

Product to pitch:
- Name: {product_name}
- Description: {product_desc}

Sender: {sender_name}
Tone: {tone}

Rules:
- Max 130 words in the body
- First line = "Subject: <subject line>"
- Personalised opening that references their context
- One clear value proposition (no buzzwords)
- One soft CTA: propose a 15-min call or free demo
- No spam language, no fake urgency, no all-caps
- Sign off with sender name and GitHub link https://github.com/mamadoulaminetall

Return ONLY the email (subject + body), nothing else."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
