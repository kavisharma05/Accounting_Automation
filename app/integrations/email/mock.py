from app.integrations.protocols import EmailProvider


class MockEmailProvider(EmailProvider):
    sent: list[dict] = []

    async def send_email(
        self, to: str, subject: str, body: str, *, attachment: bytes | None = None
    ) -> str:
        MockEmailProvider.sent.append({
            "to": to,
            "subject": subject,
            "body": body,
            "attachment_size": len(attachment) if attachment else 0,
        })
        return "mock-email-id"
