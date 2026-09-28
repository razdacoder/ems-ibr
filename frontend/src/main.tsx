import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { router } from "./router";
import { queryClient } from "./lib/query";
import { AuthProvider } from "./lib/auth";
import { ConfirmProvider } from "./lib/confirm";
import { ThemeProvider } from "./lib/theme";
import { BrandApplier } from "./lib/brand";
import { Toaster } from "./components/toaster";
import { TooltipProvider } from "./components/ui/tooltip";
import "@fontsource-variable/outfit";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrandApplier />
        <AuthProvider>
          <ConfirmProvider>
            <TooltipProvider delay={150}>
              <RouterProvider router={router} />
            </TooltipProvider>
            <Toaster />
          </ConfirmProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
