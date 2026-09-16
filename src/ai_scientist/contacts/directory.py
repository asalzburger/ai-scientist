from ..storage import SQLiteStore
from .models import Contact


class Directory:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def save(self, contact: Contact) -> Contact:
        self.store.save_document("contact", contact.id, contact.model_dump(mode="json"))
        return contact

    def list(self) -> list[Contact]:
        return [Contact.model_validate(item) for item in self.store.documents("contact")]

    def resolve(self, name_or_email: str) -> Contact:
        matches = [
            item
            for item in self.list()
            if name_or_email.casefold() in {item.name.casefold(), item.email.casefold(), item.id}
        ]
        if len(matches) != 1:
            raise ValueError("Contact must resolve uniquely; use an exact name, email, or ID")
        return matches[0]
