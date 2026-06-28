SELECT
    d.updated_at,
    d.id AS delivery_id,
    d.channel,
    n.event_type,
    left(n.title, 80) AS title,
    left(coalesce(d.error_message, ''), 240) AS error_message
FROM notification_deliveries AS d
JOIN user_notifications AS n ON n.id = d.user_notification_id
WHERE d.status = 'failed'
ORDER BY d.updated_at DESC
LIMIT :limit;
