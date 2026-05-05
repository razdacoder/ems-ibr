import { Link } from "react-router-dom";
import { useFeatures } from "@/api/public";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function FeaturesPage() {
  const features = useFeatures();
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="font-semibold">
            EMS-IBR
          </Link>
          <Button asChild>
            <Link to="/login">Sign in</Link>
          </Button>
        </div>
      </header>
      <main className="container py-12">
        <h1 className="text-3xl font-bold">Features</h1>
        <p className="mt-2 text-muted-foreground">
          Every module the platform ships with.
        </p>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.isLoading
            ? Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-44" />
              ))
            : features.data?.map((f) => (
                <Card key={f.slug}>
                  <CardHeader>
                    <CardTitle>{f.title}</CardTitle>
                    <CardDescription>{f.subtitle}</CardDescription>
                  </CardHeader>
                  <CardFooter>
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/features/${f.slug}`}>Learn more</Link>
                    </Button>
                  </CardFooter>
                </Card>
              ))}
        </div>
      </main>
    </div>
  );
}
