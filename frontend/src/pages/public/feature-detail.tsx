import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useFeature } from "@/api/public";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function FeatureDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const feature = useFeature(slug);

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
        <Button asChild variant="ghost" size="sm">
          <Link to="/features">
            <ArrowLeft className="mr-1 h-4 w-4" /> All features
          </Link>
        </Button>
        {feature.isLoading ? (
          <Skeleton className="mt-6 h-96" />
        ) : feature.error ? (
          <p className="mt-6 text-muted-foreground">
            That feature could not be found.
          </p>
        ) : feature.data ? (
          <div className="mt-6 max-w-3xl space-y-6">
            <div>
              <h1 className="text-3xl font-bold">{feature.data.title}</h1>
              <p className="mt-2 text-lg text-muted-foreground">
                {feature.data.subtitle}
              </p>
            </div>
            <p className="text-base">{feature.data.overview}</p>
            <Card>
              <CardHeader>
                <CardTitle>Capabilities</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc space-y-1 pl-6">
                  {feature.data.capabilities.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
            {feature.data.how_it_works.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>How it works</CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="list-decimal space-y-1 pl-6">
                    {feature.data.how_it_works.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader>
                <CardTitle>Benefits</CardTitle>
                <CardDescription>What you get out of the box.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="list-disc space-y-1 pl-6">
                  {feature.data.benefits.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </main>
    </div>
  );
}
