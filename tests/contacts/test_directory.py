import pytest

from ai_scientist.contacts.directory import Directory
from ai_scientist.contacts.models import Contact


def test_contacts_persist_and_ambiguous_names_fail(comm_store):
    directory = Directory(comm_store)
    first = directory.save(Contact(name="Alex", email="alex@example.org"))
    assert Directory(comm_store).resolve("alex@example.org") == first
    directory.save(Contact(name="Alex", email="other@example.org"))
    with pytest.raises(ValueError, match="uniquely"):
        directory.resolve("Alex")
