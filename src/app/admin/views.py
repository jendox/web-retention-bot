from __future__ import annotations

from sqladmin import ModelView

from app.models.booking import Booking
from app.models.client import Client, MasterClient
from app.models.invitation import Invitation
from app.models.master import MasterProfile
from app.models.notifications.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationEvent,
    RetentionPolicy,
    ScheduledNotification,
    UserNotification,
    UserNotificationPreference,
)
from app.models.schedule import (
    ScheduleDateOverride,
    ScheduleDateOverrideInterval,
    WeeklyScheduleDay,
    WeeklyScheduleInterval,
)
from app.models.service import Service
from app.models.user import User

__all__ = [
    "BookingAdmin",
    "ClientAdmin",
    "InvitationAdmin",
    "MasterClientAdmin",
    "MasterProfileAdmin",
    "NotificationChannelAdmin",
    "NotificationDeliveryAdmin",
    "NotificationEventAdmin",
    "RetentionPolicyAdmin",
    "ScheduleDateOverrideAdmin",
    "ScheduleDateOverrideIntervalAdmin",
    "ScheduledNotificationAdmin",
    "ServiceAdmin",
    "UserAdmin",
    "UserNotificationAdmin",
    "UserNotificationPreferenceAdmin",
    "WeeklyScheduleDayAdmin",
    "WeeklyScheduleIntervalAdmin",
]


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    category = "Accounts"

    column_list = [
        User.id,
        User.email,
        User.email_verified_at,
        User.is_active,
        User.created_at,
        User.updated_at,
    ]
    column_searchable_list = [User.email]
    column_sortable_list = [User.email, User.created_at, User.updated_at]
    column_default_sort = [(User.created_at, True)]
    column_details_exclude_list = [User.password_hash, User.master_profile, User.client_profiles]
    form_excluded_columns = [User.password_hash, User.master_profile, User.client_profiles]

    can_create = False
    can_delete = False


class MasterProfileAdmin(ModelView, model=MasterProfile):
    name = "Master profile"
    name_plural = "Master profiles"
    icon = "fa-solid fa-user-tie"
    category = "Accounts"

    column_list = [
        MasterProfile.id,
        MasterProfile.user_id,
        MasterProfile.display_name,
        MasterProfile.public_slug,
        MasterProfile.timezone,
        MasterProfile.default_currency,
        MasterProfile.contact_email,
        MasterProfile.created_at,
    ]
    column_searchable_list = [MasterProfile.display_name, MasterProfile.public_slug, MasterProfile.contact_email]
    column_sortable_list = [MasterProfile.display_name, MasterProfile.created_at]
    column_default_sort = [(MasterProfile.created_at, True)]
    form_excluded_columns = [
        MasterProfile.user,
        MasterProfile.weekly_schedule_days,
        MasterProfile.schedule_date_overrides,
        MasterProfile.services,
        MasterProfile.master_clients,
        MasterProfile.invitations,
        MasterProfile.bookings,
    ]


class ClientAdmin(ModelView, model=Client):
    name = "Client"
    name_plural = "Clients"
    icon = "fa-solid fa-users"
    category = "Accounts"

    column_list = [
        Client.id,
        Client.display_name,
        Client.email,
        Client.phone,
        Client.timezone,
        Client.user_id,
        Client.created_at,
    ]
    column_searchable_list = [Client.display_name, Client.email, Client.phone]
    column_sortable_list = [Client.display_name, Client.created_at]
    column_default_sort = [(Client.created_at, True)]
    form_excluded_columns = [Client.user, Client.master_links, Client.bookings]


class MasterClientAdmin(ModelView, model=MasterClient):
    name = "Master–client link"
    name_plural = "Master–client links"
    icon = "fa-solid fa-link"
    category = "Accounts"

    column_list = [
        MasterClient.id,
        MasterClient.master_id,
        MasterClient.client_id,
        MasterClient.alias,
        MasterClient.client_alias,
        MasterClient.invitation_status,
        MasterClient.linked_account_email,
        MasterClient.invite_email_mismatch,
    ]
    column_searchable_list = [MasterClient.alias, MasterClient.client_alias, MasterClient.linked_account_email]
    column_sortable_list = [MasterClient.invitation_status]
    form_excluded_columns = [MasterClient.master, MasterClient.client]


class ServiceAdmin(ModelView, model=Service):
    name = "Service"
    name_plural = "Services"
    icon = "fa-solid fa-scissors"
    category = "Catalog & bookings"

    column_list = [
        Service.id,
        Service.master_id,
        Service.name,
        Service.duration_min,
        Service.price,
        Service.currency,
        Service.is_active,
        Service.sort_order,
    ]
    column_searchable_list = [Service.name]
    column_sortable_list = [Service.name, Service.sort_order, Service.is_active]
    form_excluded_columns = [Service.master, Service.bookings]


class BookingAdmin(ModelView, model=Booking):
    name = "Booking"
    name_plural = "Bookings"
    icon = "fa-solid fa-calendar-check"
    category = "Catalog & bookings"

    column_list = [
        Booking.id,
        Booking.master_id,
        Booking.client_id,
        Booking.service_id,
        Booking.start_at,
        Booking.end_at,
        Booking.status,
        Booking.duration_min,
        Booking.price_snapshot,
        Booking.currency_snapshot,
    ]
    column_searchable_list = [Booking.cancel_comment, Booking.reschedule_comment]
    column_sortable_list = [Booking.start_at, Booking.end_at, Booking.status, Booking.created_at]
    column_default_sort = [(Booking.start_at, True)]
    form_excluded_columns = [Booking.master, Booking.client, Booking.service]

    can_delete = False


class InvitationAdmin(ModelView, model=Invitation):
    name = "Invitation"
    name_plural = "Invitations"
    icon = "fa-solid fa-envelope-open-text"
    category = "Invitations"

    column_list = [
        Invitation.id,
        Invitation.master_id,
        Invitation.target_email,
        Invitation.token,
        Invitation.expires_at,
        Invitation.accepted_at,
        Invitation.revoked_at,
        Invitation.target_client_id,
        Invitation.linked_client_id,
    ]
    column_searchable_list = [Invitation.target_email, Invitation.token]
    column_sortable_list = [Invitation.expires_at, Invitation.accepted_at]
    column_default_sort = [(Invitation.expires_at, True)]
    form_excluded_columns = [Invitation.master, Invitation.target_client]

    can_create = False


class WeeklyScheduleDayAdmin(ModelView, model=WeeklyScheduleDay):
    name = "Weekly schedule day"
    name_plural = "Weekly schedule days"
    icon = "fa-solid fa-calendar-week"
    category = "Schedule"

    column_list = [
        WeeklyScheduleDay.id,
        WeeklyScheduleDay.master_id,
        WeeklyScheduleDay.weekday,
        WeeklyScheduleDay.is_closed,
        WeeklyScheduleDay.note,
    ]
    column_sortable_list = [WeeklyScheduleDay.master_id, WeeklyScheduleDay.weekday]
    form_excluded_columns = [WeeklyScheduleDay.master, WeeklyScheduleDay.intervals]


class WeeklyScheduleIntervalAdmin(ModelView, model=WeeklyScheduleInterval):
    name = "Weekly interval"
    name_plural = "Weekly intervals"
    icon = "fa-solid fa-clock"
    category = "Schedule"

    column_list = [
        WeeklyScheduleInterval.id,
        WeeklyScheduleInterval.day_id,
        WeeklyScheduleInterval.start_time,
        WeeklyScheduleInterval.end_time,
        WeeklyScheduleInterval.sort_order,
    ]
    column_sortable_list = [WeeklyScheduleInterval.sort_order, WeeklyScheduleInterval.start_time]
    form_excluded_columns = [WeeklyScheduleInterval.day]


class ScheduleDateOverrideAdmin(ModelView, model=ScheduleDateOverride):
    name = "Date override"
    name_plural = "Date overrides"
    icon = "fa-solid fa-calendar-day"
    category = "Schedule"

    column_list = [
        ScheduleDateOverride.id,
        ScheduleDateOverride.master_id,
        ScheduleDateOverride.schedule_date,
        ScheduleDateOverride.is_closed,
        ScheduleDateOverride.note,
    ]
    column_sortable_list = [ScheduleDateOverride.schedule_date]
    column_default_sort = [(ScheduleDateOverride.schedule_date, True)]
    form_excluded_columns = [ScheduleDateOverride.master, ScheduleDateOverride.intervals]


class ScheduleDateOverrideIntervalAdmin(ModelView, model=ScheduleDateOverrideInterval):
    name = "Override interval"
    name_plural = "Override intervals"
    icon = "fa-solid fa-clock-rotate-left"
    category = "Schedule"

    column_list = [
        ScheduleDateOverrideInterval.id,
        ScheduleDateOverrideInterval.override_id,
        ScheduleDateOverrideInterval.start_time,
        ScheduleDateOverrideInterval.end_time,
        ScheduleDateOverrideInterval.sort_order,
    ]
    form_excluded_columns = [ScheduleDateOverrideInterval.override]


class NotificationEventAdmin(ModelView, model=NotificationEvent):
    name = "Notification event"
    name_plural = "Notification events"
    icon = "fa-solid fa-bolt"
    category = "Notifications"

    column_list = [
        NotificationEvent.id,
        NotificationEvent.type,
        NotificationEvent.occurred_at,
        NotificationEvent.actor_user_id,
        NotificationEvent.target_user_id,
        NotificationEvent.master_profile_id,
        NotificationEvent.client_id,
        NotificationEvent.booking_id,
    ]
    column_sortable_list = [NotificationEvent.occurred_at, NotificationEvent.type]
    column_default_sort = [(NotificationEvent.occurred_at, True)]
    form_excluded_columns = [NotificationEvent.user_notifications]

    can_create = False
    can_edit = False
    can_delete = False


class UserNotificationAdmin(ModelView, model=UserNotification):
    name = "In-app notification"
    name_plural = "In-app notifications"
    icon = "fa-solid fa-bell"
    category = "Notifications"

    column_list = [
        UserNotification.id,
        UserNotification.event_type,
        UserNotification.title,
        UserNotification.recipient_user_id,
        UserNotification.recipient_client_id,
        UserNotification.read_at,
        UserNotification.created_at,
    ]
    column_searchable_list = [UserNotification.title, UserNotification.dedup_key]
    column_sortable_list = [UserNotification.created_at, UserNotification.read_at]
    column_default_sort = [(UserNotification.created_at, True)]
    form_excluded_columns = [UserNotification.event, UserNotification.deliveries]

    can_create = False


class NotificationDeliveryAdmin(ModelView, model=NotificationDelivery):
    name = "Delivery"
    name_plural = "Deliveries"
    icon = "fa-solid fa-paper-plane"
    category = "Notifications"

    column_list = [
        NotificationDelivery.id,
        NotificationDelivery.channel,
        NotificationDelivery.status,
        NotificationDelivery.scheduled_at,
        NotificationDelivery.sent_at,
        NotificationDelivery.error_message,
        NotificationDelivery.user_notification_id,
        NotificationDelivery.created_at,
    ]
    column_searchable_list = [NotificationDelivery.error_message, NotificationDelivery.external_id]
    column_sortable_list = [
        NotificationDelivery.created_at,
        NotificationDelivery.status,
        NotificationDelivery.scheduled_at,
    ]
    column_default_sort = [(NotificationDelivery.created_at, True)]
    form_excluded_columns = [NotificationDelivery.user_notification]

    can_create = False


class UserNotificationPreferenceAdmin(ModelView, model=UserNotificationPreference):
    name = "Notification preference"
    name_plural = "Notification preferences"
    icon = "fa-solid fa-sliders"
    category = "Notifications"

    column_list = [
        UserNotificationPreference.id,
        UserNotificationPreference.user_id,
        UserNotificationPreference.channel,
        UserNotificationPreference.event_type,
        UserNotificationPreference.category,
        UserNotificationPreference.enabled,
    ]
    column_sortable_list = [UserNotificationPreference.user_id, UserNotificationPreference.channel]


class ScheduledNotificationAdmin(ModelView, model=ScheduledNotification):
    name = "Scheduled notification"
    name_plural = "Scheduled notifications"
    icon = "fa-solid fa-hourglass-half"
    category = "Notifications"

    column_list = [
        ScheduledNotification.id,
        ScheduledNotification.booking_id,
        ScheduledNotification.purpose,
        ScheduledNotification.fire_at,
        ScheduledNotification.status,
        ScheduledNotification.recipient_user_id,
        ScheduledNotification.recipient_client_id,
    ]
    column_sortable_list = [ScheduledNotification.fire_at, ScheduledNotification.status]
    column_default_sort = [(ScheduledNotification.fire_at, True)]

    can_create = False


class NotificationChannelAdmin(ModelView, model=NotificationChannel):
    name = "Messenger channel"
    name_plural = "Messenger channels"
    icon = "fa-solid fa-comments"
    category = "Notifications"

    column_list = [
        NotificationChannel.id,
        NotificationChannel.user_id,
        NotificationChannel.kind,
        NotificationChannel.address,
        NotificationChannel.is_verified,
    ]
    column_searchable_list = [NotificationChannel.address]
    form_excluded_columns = [NotificationChannel.user]


class RetentionPolicyAdmin(ModelView, model=RetentionPolicy):
    name = "Retention policy"
    name_plural = "Retention policies"
    icon = "fa-solid fa-recycle"
    category = "Notifications"

    column_list = [
        RetentionPolicy.id,
        RetentionPolicy.name,
        RetentionPolicy.idle_days,
        RetentionPolicy.target_audience,
        RetentionPolicy.event_type,
        RetentionPolicy.is_active,
    ]
    column_searchable_list = [RetentionPolicy.name, RetentionPolicy.target_audience]
