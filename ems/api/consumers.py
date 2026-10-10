from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from ems.models import BackgroundJob


class JobProgressConsumer(AsyncJsonWebsocketConsumer):
    """Streams progress events for a single ``BackgroundJob``.

    URL: ``/ws/jobs/<job_id>/?token=<api token>``.
    Closes 4401 when the connection is unauthenticated and 4403 when the
    user does not own the job (or is not staff).
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.job_id = self.scope["url_route"]["kwargs"]["job_id"]
        snapshot = await self._fetch_snapshot()
        if snapshot is None:
            await self.close(code=4404)
            return
        if not user.is_staff and snapshot["created_by_id"] != user.id:
            await self.close(code=4403)
            return
        self.group_name = f"job_{self.job_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(snapshot["payload"])

    async def disconnect(self, code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def job_progress(self, event):
        await self.send_json(event["data"])

    @database_sync_to_async
    def _fetch_snapshot(self):
        try:
            job = BackgroundJob.objects.only(
                "id",
                "job_id",
                "job_type",
                "status",
                "progress",
                "total_steps",
                "error_message",
                "result_data",
                "created_by_id",
            ).get(job_id=self.job_id)
        except BackgroundJob.DoesNotExist:
            return None
        return {
            "created_by_id": job.created_by_id,
            "payload": {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress_percentage,
                "error_message": job.error_message,
                "result": job.result_data if job.status == "success" else None,
            },
        }


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Pushes the signed-in user's new notifications as they are sent.

    URL: ``/ws/notifications/?token=<api token>``. Sends
    ``{"type": "unread", "count": n}`` on connect, then
    ``{"type": "notification", "notification": {...}}`` per new one.
    Closes 4401 when the connection is unauthenticated.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        from ems.notifications import user_group

        self.group_name = user_group(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "unread", "count": await self._unread(user)})

    async def disconnect(self, code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notification_new(self, event):
        await self.send_json({"type": "notification", "notification": event["data"]})

    @database_sync_to_async
    def _unread(self, user):
        from ems.notifications import unread_count

        return unread_count(user)
