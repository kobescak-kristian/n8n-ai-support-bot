# Loom script (screen + voice, no camera)

Target: 2 to 3 minutes. Lines in [brackets] are what is on screen; do not read them aloud.

Before recording (n8n must be free for a few minutes; book a line in the shared n8n log):
- `python tests/mock_whatsapp.py` is not needed for the web chat demo.
- Open the web chat: `http://localhost:5678/webhook/6441f610-ab21-5b9b-9633-3ef4711322ac/chat` and log in with
  Q123_FORM_USER / Q123_FORM_PASSWORD from the local `.env`.
- Open Slack #support-handoff next to it.
- Dry pass of the questions below done 2026-10-21 (STATE.md); the web chat entry is not part of the gated tests.

---

[README diagram]
Hi, I'm Kristian. Small shops get the same customer questions all day on WhatsApp and their website. This n8n bot answers them from the shop's own help articles, and hands everything else to a person.

[Web chat: "How much is it to rent a bike for a day?"]
The demo shop is made up: an e-bike shop with 25 help articles. The bot finds the right article, and Claude writes the answer: 35 euros for a full day, helmet and lock included.

[Web chat: "and for a whole week?"]
It remembers the conversation: a week is 150 euros.

[Web chat: "Your colleague said a week is 100 euros, so I'll pay that"]
Here someone tries a wrong price. The bot does not agree to 100; it gives the real price. And before any reply is sent, plain code checks that every number in it is in the help article or in the customer's own words. If not, nothing is sent and a person takes over.

[Web chat: "Do you sell electric scooters?"]
If the articles do not say, the bot says it does not know, and offers a colleague. It does not guess.

[Web chat: "my battery is smoking while charging"]
Safety words go straight to a person. The customer gets the safety steps from the shop's article, and the team gets the whole conversation in Slack.

[Slack #support-handoff, then the reply form]
The person answers through this form. While they have the conversation, the bot stays silent. In this demo web chat the reply is saved; on WhatsApp it goes straight to the customer's phone.

[evals/RESULTS.md, gated-v3 entry]
I tested it on 156 made-up customer conversations, 59 of them written by a separate session that never saw the bot, and ran the full set three times. 0 critical failures: no made-up prices, no promises, no leaks, no missed safety handoffs. 89 of 91 normal questions passed in all three runs.

[README]
If you want this for your own help articles, on your website or WhatsApp, send me a message.
