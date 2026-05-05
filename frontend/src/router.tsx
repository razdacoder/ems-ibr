import { createBrowserRouter, Navigate } from "react-router-dom";
import LoginPage from "@/pages/login";
import DashboardPage from "@/pages/dashboard";
import DepartmentsListPage from "@/pages/departments/list";
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
import JobsListPage from "@/pages/jobs/list";
import ExportsPage from "@/pages/exports/page";
import LandingPage from "@/pages/public/landing";
import FeaturesPage from "@/pages/public/features";
import FeatureDetailPage from "@/pages/public/feature-detail";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { RequireAdmin, RequireAuth } from "@/components/route-guards";

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
      { path: "/departments", element: <DepartmentsListPage /> },
      { path: "/courses", element: <CoursesListPage /> },
      { path: "/classes", element: <ClassesListPage /> },
      { path: "/classes/:id", element: <ClassDetailPage /> },
      { path: "/halls", element: <HallsListPage /> },
      { path: "/students", element: <StudentsListPage /> },
      {
        path: "/users",
        element: (
          <RequireAdmin>
            <UsersListPage />
          </RequireAdmin>
        ),
      },
      {
        path: "/uploads",
        element: (
          <RequireAdmin>
            <UploadsPage />
          </RequireAdmin>
        ),
      },
      { path: "/timetable", element: <TimetablePage /> },
      { path: "/distribution", element: <DistributionPage /> },
      { path: "/allocation", element: <AllocationPage /> },
      { path: "/allocation/hall", element: <HallAllocationPage /> },
      { path: "/jobs", element: <JobsListPage /> },
      { path: "/exports", element: <ExportsPage /> },
      {
        path: "/settings",
        element: (
          <RequireAdmin>
            <SettingsPage />
          </RequireAdmin>
        ),
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
