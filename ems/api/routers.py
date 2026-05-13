from rest_framework.routers import DefaultRouter

from ems.api.views.cls import ClassViewSet
from ems.api.views.course import CourseViewSet
from ems.api.views.department import DepartmentViewSet
from ems.api.views.faculty import FacultyViewSet
from ems.api.views.hall import HallViewSet
from ems.api.views.jobs import JobViewSet
from ems.api.views.student import StudentViewSet
from ems.api.views.user import UserViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"faculties", FacultyViewSet, basename="faculty")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"classes", ClassViewSet, basename="class")
router.register(r"halls", HallViewSet, basename="hall")
router.register(r"students", StudentViewSet, basename="student")
router.register(r"users", UserViewSet, basename="user")
router.register(r"jobs", JobViewSet, basename="job")
