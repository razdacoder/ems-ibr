import { createFileRoute } from "@tanstack/react-router";
import LandingPage from "@/pages/public/landing";

// Marketing site (bare domain). Site routes live under /site internally;
// the router's host rewrite (router.tsx) maps ordo.app/ here.
export const Route = createFileRoute("/site/")({
  component: LandingPage,
});
