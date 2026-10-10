import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { isPlatformOwner, PLATFORM_ROLE_LABELS, usePlatformAuth } from "@/lib/platform-auth";

/** Console landing. Schools take over this page when slice 7 lands. */
export default function ConsoleHomePage() {
  const { admin } = usePlatformAuth();
  const links = [
    ...(isPlatformOwner(admin)
      ? [{ to: "/console/admins" as const, title: "Admins", text: "Invite the Ordo team, change roles, reset two factor sign in." }]
      : []),
    { to: "/console/audit" as const, title: "Audit log", text: "Every console sign in and change, with who, when and from where." },
  ];

  return (
    <div className="space-y-10">
      <header className="border-b border-[color:var(--border)] pb-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          Console · {admin ? PLATFORM_ROLE_LABELS[admin.role] : ""}
        </p>
        <h1 className="mt-3 font-serif text-[2.5rem] leading-[1.05] tracking-[-0.015em] sm:text-[3rem]">
          Hello, {admin?.name.split(" ")[0]}.
        </h1>
        <p className="mt-3 max-w-2xl text-[14.5px] leading-[1.65] text-muted-foreground">
          This is where the Ordo team runs the platform.
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="group rounded-[12px] border border-[color:var(--border)] bg-card p-6 transition-colors hover:border-[color:var(--brand)]"
          >
            <span className="flex items-center justify-between font-serif text-[1.5rem]">
              {link.title}
              <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden />
            </span>
            <span className="mt-2 block text-[14px] leading-[1.6] text-muted-foreground">{link.text}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
