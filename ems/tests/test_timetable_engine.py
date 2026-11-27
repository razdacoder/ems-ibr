"""The timetable task runs the engine the Ordo team set for the school
(School.timetable_engine): greedy or CP-SAT."""
import sys
from unittest import mock

from django.db import connection

from ems import tasks
from ems.api.serializers.constraints import GenerationConstraintsSerializer
from ems.models import GenerationConstraints, TimeTable

from .test_student_lists import run
from .test_timetable_fit import MON, TUE, FitTestCase


class EngineTests(FitTestCase):
    def setUp(self):
        super().setUp()
        school = connection.tenant
        saved = (school.timetable_engine, school.cpsat_spread_seconds)

        def restore():
            school.timetable_engine, school.cpsat_spread_seconds = saved
        self.addCleanup(restore)

    def use(self, engine):
        connection.tenant.timetable_engine = engine
        connection.tenant.cpsat_spread_seconds = 5

    def generate(self):
        job = run(tasks.generate_timetable_task, str(MON), str(TUE))
        self.assertEqual(job.status, "success", job.result_data)
        return job.result_data

    def test_greedy_is_the_default(self):
        self.assertEqual(connection.tenant.timetable_engine, "greedy")
        result = self.generate()
        self.assertEqual(result["engine"], "greedy")
        self.assertIsNone(GenerationConstraints.objects.get().cpsat_alpha)

    def test_cpsat_plans_every_course_and_stores_alpha(self):
        self.use("cpsat")
        result = self.generate()
        self.assertEqual(result["engine"], "cpsat")
        self.assertEqual(result["am_skipped"] + result["pm_skipped"], 0)
        self.assertEqual(TimeTable.objects.values("course").distinct().count(), 5)
        self.assertIsNotNone(GenerationConstraints.objects.get().cpsat_alpha)

    def test_cpsat_uses_the_schools_settings_and_stored_alpha(self):
        self.use("cpsat")
        GenerationConstraints.objects.update(cpsat_alpha=3.5)
        from ems import timetable_cpsat
        with mock.patch.object(timetable_cpsat, "generate_cpsat",
                               wraps=timetable_cpsat.generate_cpsat) as spy:
            self.generate()
        self.assertEqual(spy.call_args.kwargs["initial_alpha"], 3.5)
        self.assertEqual(spy.call_args.kwargs["spread_time_limit"], 5)

    def test_falls_back_to_greedy_without_ortools(self):
        self.use("cpsat")
        with mock.patch.dict(sys.modules, {"ems.timetable_cpsat": None}):
            result = self.generate()
        self.assertEqual(result["engine"], "greedy")
        self.assertIn("greedy", result["warnings"][-1]["title"].lower())


class SchoolCannotPickTheEngineTests(FitTestCase):
    def test_constraints_carry_no_engine_and_alpha_is_read_only(self):
        s = GenerationConstraintsSerializer(
            GenerationConstraints.objects.get(),
            data={"timetable_engine": "cpsat", "cpsat_alpha": 99}, partial=True,
        )
        self.assertTrue(s.is_valid())
        s.save()
        self.assertNotIn("timetable_engine", s.data)
        self.assertIsNone(GenerationConstraints.objects.get().cpsat_alpha)
