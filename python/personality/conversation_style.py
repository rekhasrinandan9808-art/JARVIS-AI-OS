"""
personality/conversation_style.py
Turns stiff/formal text into casual, friend-like phrasing before it goes
to voice.speak(). Pure text transform -- no ML model, no network call --
so it's fast, free, and fully testable offline (unlike voice/vision/etc).

This does NOT touch what JARVIS *decides* to say -- that's your
orchestrator/LLM logic. It only adjusts *how* the words are phrased,
right before they're spoken aloud.
"""

from __future__ import annotations
import random
import re

# Swap stiff phrasing for how a friend would actually say it.
CASUAL_REPLACEMENTS = [
    (r"\bI have completed\b", "I've finished"),
    (r"\bI am unable to\b", "I can't"),
    (r"\bI am currently\b", "I'm"),
    (r"\bdo you require\b", "do you need"),
    (r"\bAffirmative\b", "Yep"),
    (r"\bNegative\b", "Nope"),
    (r"\bIt appears that\b", "Looks like"),
    (r"\butilize\b", "use"),
    (r"\bapproximately\b", "about"),
    (r"\btherefore\b", "so"),
    (r"\bhowever\b", "but"),
    (r"\bI would recommend\b", "I'd say"),
    (r"\bPlease note that\b", ""),
    (r"\bI apologize,? but\b", "sorry, but"),
    (r"\bIn conclusion,?\b", "so basically,"),
]

GREETING_OPENERS = ["Hey,", "Hey!", "Hi,", "So,", "Okay,", "Alright,"]
ACK_OPENERS = ["Got it.", "Sure thing.", "On it.", "Okay.", "Yep."]

CASUAL_ERROR_TEMPLATES = [
    "Hmm, that didn't work -- {reason}",
    "Ran into a snag: {reason}",
    "That failed on me -- {reason}",
]


def humanize(text: str, mode: str = "friendly") -> str:
    """
    mode: "friendly" (default, casual contractions + softer phrasing),
          "formal" (no changes -- passthrough, for when you want the raw text),
          "brief" (friendly + trims to the first sentence, for quick voice replies)
    """
    if mode == "formal":
        return text

    out = text
    for pattern, replacement in CASUAL_REPLACEMENTS:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)

    out = _contractions(out)

    if mode == "brief":
        first_sentence = re.split(r"(?<=[.!?])\s", out.strip())
        out = first_sentence[0] if first_sentence else out

    return out.strip()


def _contractions(text: str) -> str:
    pairs = [
        (r"\bI am\b", "I'm"), (r"\byou are\b", "you're"), (r"\bthey are\b", "they're"),
        (r"\bwe are\b", "we're"), (r"\bit is\b", "it's"), (r"\bthat is\b", "that's"),
        (r"\bdo not\b", "don't"), (r"\bdoes not\b", "doesn't"), (r"\bdid not\b", "didn't"),
        (r"\bcannot\b", "can't"), (r"\bwill not\b", "won't"), (r"\bwould not\b", "wouldn't"),
        (r"\bshould not\b", "shouldn't"), (r"\bhave not\b", "haven't"), (r"\bhas not\b", "hasn't"),
        (r"\bI will\b", "I'll"), (r"\byou will\b", "you'll"), (r"\bwe will\b", "we'll"),
        (r"\bI would\b", "I'd"), (r"\bI have\b", "I've"),
    ]
    out = text
    for pattern, repl in pairs:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out


def add_greeting(text: str) -> str:
    """Prefix a casual opener, e.g. for the first thing JARVIS says in a session."""
    return f"{random.choice(GREETING_OPENERS)} {text}"


def add_acknowledgement(text: str) -> str:
    """Prefix a short acknowledgement, e.g. before reporting a completed task."""
    return f"{random.choice(ACK_OPENERS)} {text}"


def humanize_error(reason: str) -> str:
    """Turn a raw exception string into something that doesn't sound like a stack trace."""
    template = random.choice(CASUAL_ERROR_TEMPLATES)
    clean_reason = reason[0].lower() + reason[1:] if reason else "not sure why."
    return template.format(reason=clean_reason)
