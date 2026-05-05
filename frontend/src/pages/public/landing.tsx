import { Link } from "react-router-dom";
import {
  CalendarCheck,
  Database,
  FileText,
  Grid3x3,
  LayoutGrid,
  ListChecks,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const HIGHLIGHTS = [
  {
    icon: CalendarCheck,
    title: "Conflict-free timetables",
    description: "Generate exam schedules in minutes, not days.",
  },
  {
    icon: LayoutGrid,
    title: "Smart hall distribution",
    description: "Capacity-aware allocation with split-class support.",
  },
  {
    icon: Grid3x3,
    title: "Anti-cheating seating",
    description: "8-direction adjacency and pattern-based placement.",
  },
  {
    icon: FileText,
    title: "Polished reports",
    description: "DOCX, Excel, and CSV ready for the printer.",
  },
  {
    icon: Database,
    title: "Bulk data tooling",
    description: "CSV ingestion with strict validation and clear errors.",
  },
  {
    icon: ListChecks,
    title: "Real-time job monitor",
    description: "Live progress for every long-running task.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between">
          <div className="font-semibold">EMS-IBR</div>
          <nav className="flex items-center gap-3 text-sm">
            <Link to="/features" className="text-muted-foreground hover:text-foreground">
              Features
            </Link>
            <Button asChild>
              <Link to="/login">Sign in</Link>
            </Button>
          </nav>
        </div>
      </header>

      <main>
        <section className="container py-20 text-center">
          <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight md:text-6xl">
            Run examinations without the spreadsheets.
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            EMS-IBR generates conflict-free timetables, distributes classes to
            halls, and assigns individual seats with anti-cheating constraints —
            in a single integrated workflow.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Button asChild size="lg">
              <Link to="/login">Get started</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/features">Explore features</Link>
            </Button>
          </div>
        </section>

        <section className="container pb-20">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {HIGHLIGHTS.map(({ icon: Icon, title, description }) => (
              <Card key={title}>
                <CardHeader>
                  <Icon className="mb-2 h-6 w-6 text-primary" />
                  <CardTitle className="text-lg">{title}</CardTitle>
                  <CardDescription>{description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t py-8">
        <div className="container text-center text-sm text-muted-foreground">
          © {new Date().getFullYear()} EMS-IBR.
        </div>
      </footer>
    </div>
  );
}
