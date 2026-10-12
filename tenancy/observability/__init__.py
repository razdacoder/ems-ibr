"""Per school error observability (spec 0004).

Captures server errors, failed jobs and tasks, logged errors, browser errors
and WebSocket problems, tags each with the school it happened in
(``connection.tenant``), and groups repeats. Capture never raises into its
caller: every public function here logs on ``ordo.observability`` and
returns.
"""
