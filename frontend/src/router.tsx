import { createBrowserRouter, Navigate } from "react-router-dom";
import LoginPage from "@/pages/login";
import DashboardPage from "@/pages/dashboard";
import DepartmentsListPage from "@/pages/departments/list";
import FacultiesListPage from "@/pages/faculties/list";
import ConstraintsPage from "@/pages/constraints/page";
import CoursesListPage from "@/pages/courses/list";
import ClassesListPage from "@/pages/classes/list";
import ClassDetailPage from "@/pages/classes/detail";
import HallsListPage from "@/pages/halls/list";
import StudentsListPage from "@/pages/students/list";
import UsersListPage from "@/pages/users/list";
import SettingsPage from "@/pages/settings/page";
import UploadsPage from "@/pages/uploads/page";
import TimetablePage from "@/pages/timetable/page";
import DistributionPage from "@/pages/distribution/page";
import AllocationPage from "@/pages/allocation/page";
import HallAllocationPage from "@/pages/allocation/hall";
import DirectoryPage from "@/pages/directory/page";
import JobsListPage from "@/pages/jobs/list";
import AuditLogListPage from "@/pages/audit/list";
import ExportsPage from "@/pages/exports/page";
import LandingPage from "@/pages/public/landing";
import FeaturesPage from "@/pages/public/features";
import FeatureDetailPage from "@/pages/public/feature-detail";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import {
  RequireAuth,
  RequireCommittee,
  RequireDataOfficer,
  RequireFacultyOfficer,
  RequireSuperAdmin,
} from "@/components/route-guards";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/features", element: <FeaturesPage /> },
  { path: "/features/:slug", element: <FeatureDetailPage /> },
  { path: "/login", element: <LoginPage /> },
  {
    element: (
      <RequireAuth>
        <DashboardLayout />
      </RequireAuth>
    ),
    children: [
      { path: "/dashboard", element: <DashboardPage /> },
      {
        path: "/departments",
        element: (
          <RequireDataOfficer>
            <DepartmentsListPage />
          </RequireDataOfficer>
        ),
      },
      {
        path: "/faculties",
        element: (
          <RequireFacultyOfficer>
            <FacultiesListPage />
          </RequireFacultyOfficer>
        ),
      },
      {
        path: "/constraints",
        element: (
          <RequireSuperAdmin>
            <ConstraintsPage />
          </RequireSuperAdmin>
        ),
      },
      { path: "/courses", element: <CoursesListPage /> },
      { path: "/classes", element: <ClassesListPage /> },
      { path: "/classes/:id", element: <ClassDetailPage /> },
      {
        path: "/halls",
        element: (
          <RequireDataOfficer>
            <HallsListPage />
          </RequireDataOfficer>
        ),
      },
      { path: "/students", element: <StudentsListPage /> },
      {
        path: "/users",
        element: (
          <RequireSuperAdmin>
            <UsersListPage />
          </RequireSuperAdmin>
        ),
      },
      {
        path: "/uploads",
        element: (
          <RequireDataOfficer>
            <UploadsPage />
          </RequireDataOfficer>
        ),
      },
      { path: "/timetable", element: <TimetablePage /> },
      {
        path: "/distribution",
        element: (
          <RequireCommittee>
            <DistributionPage />
          </RequireCommittee>
        ),
      },
      {
        path: "/allocation",
        element: (
          <RequireCommittee>
            <AllocationPage />
          </RequireCommittee>
        ),
      },
      {
        path: "/allocation/hall",
        element: (
          <RequireCommittee>
            <HallAllocationPage />
          </RequireCommittee>
        ),
      },
      {
        path: "/jobs",
        element: (
          <RequireSuperAdmin>
            <JobsListPage />
          </RequireSuperAdmin>
        ),
      },
      {
        path: "/audit",
        element: (
          <RequireSuperAdmin>
            <AuditLogListPage />
          </RequireSuperAdmin>
        ),
      },
      { path: "/exports", element: <ExportsPage /> },
      {
        path: "/directory",
        element: (
          <RequireCommittee>
            <DirectoryPage />
          </RequireCommittee>
        ),
      },
      {
        path: "/settings",
        element: (
          <RequireSuperAdmin>
            <SettingsPage />
          </RequireSuperAdmin>
        ),
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
