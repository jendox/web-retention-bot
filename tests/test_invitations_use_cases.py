import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import status

from app.models.client import InvitationStatus
from app.use_cases.invitations.accept import AcceptInvitationError, AcceptInvitationUseCase
from app.use_cases.invitations.create import CreateInvitationError, CreateInvitationUseCase


class FakeInvitationRepo:
    def __init__(self, invite=None, active_pending=None):
        self.invite = invite
        self.active_pending = active_pending
        self.created_kwargs = None
        self.revoked = []

    async def get_by_token(self, token: str):
        return self.invite if token == "invite-token" else None

    async def create_invite(self, **kwargs):
        self.created_kwargs = kwargs
        return SimpleNamespace(**kwargs)

    async def find_active_pending_target_invite(self, master_id, client_id):
        return self.active_pending

    async def revoke_pending_target_invites(self, master_id, client_id):
        self.revoked.append((master_id, client_id))


class FakeClientRepo:
    def __init__(self, *, link_with_client=None, existing_client_ids=None, unlinked_email_matches=None):
        self.link_with_client = link_with_client
        self.existing_client_ids = existing_client_ids or []
        self.unlinked_email_matches = unlinked_email_matches or []
        self.created_client = None
        self.created_link = None

    async def get_link_with_client(self, *, master_id, client_id):
        return self.link_with_client

    async def client_ids_for_master_user(self, master_id, user_id):
        return self.existing_client_ids

    async def unlinked_clients_by_master_email(self, *, master_id, email, limit=2):
        return self.unlinked_email_matches[:limit]

    async def create(self, *, display_name, phone=None, email=None):
        self.created_client = SimpleNamespace(
            id=uuid.uuid4(),
            display_name=display_name,
            phone=phone,
            email=email,
            user_id=None,
        )
        return self.created_client

    async def create_link(self, *, master_id, client_id, invitation_status=InvitationStatus.LINKED):
        self.created_link = SimpleNamespace(
            master_id=master_id,
            client_id=client_id,
            invitation_status=invitation_status,
            linked_account_email=None,
            invite_email_mismatch=False,
        )
        return self.created_link


class FakeDispatcher:
    def __init__(self):
        self.email_mismatch_calls = []

    async def dispatch_invite_email_mismatch_for_master(self, **kwargs):
        self.email_mismatch_calls.append(kwargs)


def _valid_invite(*, master_id=None, target_client_id=None):
    master_user_id = uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(),
        master_id=master_id or uuid.uuid4(),
        token="invite-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        accepted_at=None,
        revoked_at=None,
        linked_client_id=None,
        target_client_id=target_client_id,
        master=SimpleNamespace(id=master_id or uuid.uuid4(), user_id=master_user_id),
    )


async def test_accept_open_invitation_creates_new_client_and_link():
    invite = _valid_invite()
    user = SimpleNamespace(id=uuid.uuid4(), email="client@example.com")
    client_repo = FakeClientRepo()
    invite_repo = FakeInvitationRepo(invite=invite)
    dispatcher = FakeDispatcher()
    use_case = AcceptInvitationUseCase(client_repo, invite_repo, dispatcher)

    client_id, mismatch = await use_case(
        token="invite-token",
        display_name="  Client Name  ",
        phone="  +375291112233  ",
        user=user,
    )

    assert mismatch is False
    assert client_id == client_repo.created_client.id
    assert client_repo.created_client.display_name == "Client Name"
    assert client_repo.created_client.phone == "+375291112233"
    assert client_repo.created_client.email == "client@example.com"
    assert client_repo.created_client.user_id == user.id
    assert client_repo.created_link.client_id == client_id
    assert client_repo.created_link.linked_account_email == "client@example.com"
    assert client_repo.created_link.invitation_status == InvitationStatus.LINKED
    assert invite.linked_client_id == client_id
    assert invite.accepted_at is not None


async def test_accept_open_invitation_links_existing_unlinked_client_with_same_email():
    master_id = uuid.uuid4()
    existing_client_id = uuid.uuid4()
    invite = _valid_invite(master_id=master_id)
    user = SimpleNamespace(id=uuid.uuid4(), email="client@example.com")
    link = SimpleNamespace(
        master_id=master_id,
        client_id=existing_client_id,
        invitation_status=InvitationStatus.PENDING,
        linked_account_email=None,
        invite_email_mismatch=True,
    )
    client = SimpleNamespace(
        id=existing_client_id,
        display_name="Stored Name",
        phone="+375290000000",
        email="CLIENT@example.com",
        user_id=None,
    )
    client_repo = FakeClientRepo(unlinked_email_matches=[(link, client)])
    use_case = AcceptInvitationUseCase(client_repo, FakeInvitationRepo(invite=invite), FakeDispatcher())

    client_id, mismatch = await use_case(
        token="invite-token",
        display_name="Accepted Name",
        phone="+375291112233",
        user=user,
    )

    assert mismatch is False
    assert client_id == existing_client_id
    assert client_repo.created_client is None
    assert client_repo.created_link is None
    assert client.display_name == "Accepted Name"
    assert client.phone == "+375291112233"
    assert client.email == "client@example.com"
    assert client.user_id == user.id
    assert link.linked_account_email == "client@example.com"
    assert link.invite_email_mismatch is False
    assert link.invitation_status == InvitationStatus.LINKED
    assert invite.linked_client_id == existing_client_id
    assert invite.accepted_at is not None


async def test_accept_targeted_invitation_links_existing_client_and_flags_email_mismatch():
    master_id = uuid.uuid4()
    target_client_id = uuid.uuid4()
    invite = _valid_invite(master_id=master_id, target_client_id=target_client_id)
    user = SimpleNamespace(id=uuid.uuid4(), email="account@example.com")
    link = SimpleNamespace(linked_account_email=None, invite_email_mismatch=False)
    client = SimpleNamespace(
        id=target_client_id,
        display_name="Stored Name",
        phone=None,
        email="profile@example.com",
        user_id=None,
    )
    client_repo = FakeClientRepo(link_with_client=(link, client))
    dispatcher = FakeDispatcher()
    use_case = AcceptInvitationUseCase(client_repo, FakeInvitationRepo(invite=invite), dispatcher)

    client_id, mismatch = await use_case(
        token="invite-token",
        display_name="Accepted Name",
        phone="",
        user=user,
    )

    assert client_id == target_client_id
    assert mismatch is True
    assert client.display_name == "Accepted Name"
    assert client.phone is None
    assert client.email == "profile@example.com"
    assert client.user_id == user.id
    assert link.linked_account_email == "account@example.com"
    assert link.invite_email_mismatch is True
    assert dispatcher.email_mismatch_calls == [
        {
            "master_user_id": invite.master.user_id,
            "master_profile_id": invite.master.id,
            "client_id": target_client_id,
            "profile_email": "profile@example.com",
            "account_email": "account@example.com",
            "client_display_name": "Accepted Name",
        }
    ]
    assert invite.linked_client_id == target_client_id
    assert invite.accepted_at is not None


async def test_accept_invitation_rejects_already_accepted_invite():
    invite = _valid_invite()
    invite.accepted_at = datetime.now(UTC)
    use_case = AcceptInvitationUseCase(FakeClientRepo(), FakeInvitationRepo(invite=invite), FakeDispatcher())

    with pytest.raises(AcceptInvitationError) as exc_info:
        await use_case(
            token="invite-token",
            display_name="Client",
            phone=None,
            user=SimpleNamespace(id=uuid.uuid4(), email="client@example.com"),
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.error_message == "Invitation already accepted"


async def test_create_targeted_invitation_rejects_active_pending_invite_without_replace():
    target_client_id = uuid.uuid4()
    client = SimpleNamespace(id=target_client_id, user_id=None)
    client_repo = FakeClientRepo(link_with_client=(SimpleNamespace(), client))
    invite_repo = FakeInvitationRepo(active_pending=SimpleNamespace(id=uuid.uuid4()))
    use_case = CreateInvitationUseCase(client_repo, invite_repo)

    with pytest.raises(CreateInvitationError) as exc_info:
        await use_case(
            master_id=uuid.uuid4(),
            expires_hours=72,
            target_email=None,
            target_client_id=target_client_id,
            replace=False,
        )

    assert str(exc_info.value) == "An active invitation already exists for this client."


async def test_create_targeted_invitation_replaces_active_pending_invite():
    master_id = uuid.uuid4()
    target_client_id = uuid.uuid4()
    client = SimpleNamespace(id=target_client_id, user_id=None)
    client_repo = FakeClientRepo(link_with_client=(SimpleNamespace(), client))
    invite_repo = FakeInvitationRepo(active_pending=SimpleNamespace(id=uuid.uuid4()))
    use_case = CreateInvitationUseCase(client_repo, invite_repo)

    out = await use_case(
        master_id=master_id,
        expires_hours=24,
        target_email="TARGET@EXAMPLE.COM",
        target_client_id=target_client_id,
        replace=True,
    )

    assert invite_repo.revoked == [(master_id, target_client_id)]
    assert invite_repo.created_kwargs["master_id"] == master_id
    assert invite_repo.created_kwargs["target_email"] == "target@example.com"
    assert out.target_client_id == target_client_id
    assert out.target_email == "target@example.com"
