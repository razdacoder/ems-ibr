import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { extractErrorEnvelope } from "@/lib/api";

export interface FileUploadCardProps {
  title: string;
  description: string;
  accept?: string;
  disabled?: boolean;
  isPending: boolean;
  result?: { created: number; updated: number } | null;
  error?: unknown;
  onUpload: (file: File) => Promise<void>;
}

export function FileUploadCard({
  title,
  description,
  accept = ".csv,text/csv",
  disabled,
  isPending,
  result,
  error,
  onUpload,
}: FileUploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = async () => {
    if (!file) return;
    await onUpload(file);
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Input
          ref={inputRef}
          type="file"
          accept={accept}
          disabled={disabled || isPending}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        {result && (
          <Alert>
            <AlertTitle>Upload complete</AlertTitle>
            <AlertDescription>
              Created {result.created} record{result.created === 1 ? "" : "s"},
              updated {result.updated}.
            </AlertDescription>
          </Alert>
        )}
        {error ? (
          <Alert variant="destructive">
            <AlertDescription>
              {extractErrorEnvelope(error).detail}
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
      <CardFooter className="justify-end">
        <Button
          onClick={handleSubmit}
          disabled={!file || disabled || isPending}
        >
          <Upload className="mr-2 h-4 w-4" />
          {isPending ? "Uploading…" : "Upload"}
        </Button>
      </CardFooter>
    </Card>
  );
}
